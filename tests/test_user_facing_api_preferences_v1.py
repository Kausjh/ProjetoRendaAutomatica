from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from repositories.user_identity_repository import UserIdentityRepository
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.api_aplicacao.servidor import ServidorApiAplicacao
from services.user_identity_service import UserIdentityService
from services.user_personalization_service import UserPersonalizationService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "user_facing_api_preferences_v1.json"
RUNTIME = ROOT / "runtime.py"


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: object | None = None,
    user_session: str | None = None,
    infra_token: str | None = None,
) -> tuple[int, dict[str, object]]:
    headers: dict[str, str] = {}

    if user_session is not None:
        headers["X-User-Session"] = user_session

    if infra_token is not None:
        headers["Authorization"] = f"Bearer {infra_token}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url,
        headers=headers,
        method=method,
        data=data,
    )

    try:
        with urlopen(request, timeout=5) as resposta:
            return (
                resposta.status,
                json.loads(resposta.read().decode("utf-8")),
            )
    except HTTPError as erro:
        return (
            erro.code,
            json.loads(erro.read().decode("utf-8")),
        )


@pytest.fixture
def api(tmp_path: Path):
    banco = tmp_path / "user_identity.sqlite3"
    identity_repository = UserIdentityRepository(banco)
    identity_service = UserIdentityService(identity_repository)

    personalization_repository = UserPersonalizationRepository(banco)
    personalization_service = UserPersonalizationService(
        personalization_repository,
        identity_repository,
    )

    conta = identity_service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    sessao = identity_service.emitir_sessao(conta)

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="",
        user_identity_service=identity_service,
        user_personalization_service=personalization_service,
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco

    try:
        yield (
            f"http://127.0.0.1:{porta}",
            identity_service,
            personalization_service,
            conta,
            sessao.token,
        )
    finally:
        servidor.encerrar()


def test_contract_define_preferences_http():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["schema"] == ("projeto-renda-automatica.user-facing-api-preferences")
    assert data["preferences_http_version"] == 1

    routes = {(item["method"], item["path"]): item for item in data["routes"]}

    assert ("GET", "/api/v1/me/preferences") in routes
    assert ("PATCH", "/api/v1/me/preferences") in routes
    assert all(item["requires_user_session"] is True for item in routes.values())


def test_get_preferences_cria_defaults(api):
    base, _, _, _, token = api
    status, body = _request_json(
        f"{base}/api/v1/me/preferences",
        user_session=token,
    )
    assert status == 200
    prefs = body["dados"]["preferencias"]
    assert prefs["notificacoes_preco_habilitadas"] is True
    assert prefs["marketplaces_preferidos"] == []
    assert prefs["atualizado_em"]


def test_patch_parcial_preserva_campo_omitido(api):
    base, _, personalization, conta, token = api

    personalization.atualizar_preferencias(
        conta_id=conta.id,
        notificacoes_preco_habilitadas=True,
        marketplaces_preferidos=["mercado_livre", "shopee"],
    )

    status, body = _request_json(
        f"{base}/api/v1/me/preferences",
        method="PATCH",
        payload={"notificacoes_preco_habilitadas": False},
        user_session=token,
    )

    assert status == 200
    prefs = body["dados"]["preferencias"]
    assert prefs["notificacoes_preco_habilitadas"] is False
    assert prefs["marketplaces_preferidos"] == [
        "mercado_livre",
        "shopee",
    ]


def test_patch_normaliza_e_deduplica_marketplaces(api):
    base, _, _, _, token = api

    status, body = _request_json(
        f"{base}/api/v1/me/preferences",
        method="PATCH",
        payload={
            "marketplaces_preferidos": [
                " Shopee ",
                "mercado_livre",
                "shopee",
            ],
        },
        user_session=token,
    )

    assert status == 200
    assert body["dados"]["preferencias"]["marketplaces_preferidos"] == ["mercado_livre", "shopee"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"conta_id": "usr_outro"},
        {"notificacoes_preco_habilitadas": "false"},
        {"marketplaces_preferidos": "mercado_livre"},
        {"marketplaces_preferidos": [123]},
    ],
)
def test_patch_rejeita_payload_invalido(api, payload):
    base, _, _, _, token = api

    status, body = _request_json(
        f"{base}/api/v1/me/preferences",
        method="PATCH",
        payload=payload,
        user_session=token,
    )

    assert status == 400
    assert body["erro"]["codigo"] == "payload_invalido"


def test_patch_marketplace_invalido_retorna_400(api):
    base, _, _, _, token = api

    status, body = _request_json(
        f"{base}/api/v1/me/preferences",
        method="PATCH",
        payload={"marketplaces_preferidos": ["mercado livre"]},
        user_session=token,
    )

    assert status == 400
    assert body["erro"]["codigo"] == "preferencias_invalidas"


def test_preferences_sem_sessao_retorna_401(api):
    base, _, _, _, _ = api

    status, body = _request_json(
        f"{base}/api/v1/me/preferences",
    )

    assert status == 401
    assert body["erro"]["codigo"] == ("sessao_usuario_obrigatoria")


def test_preferences_isoladas_por_sessao(api):
    base, identity, personalization, conta_a, token_a = api

    conta_b = identity.criar_conta(
        email="outra@example.com",
        senha="outra-senha-forte-123",
    )
    sessao_b = identity.emitir_sessao(conta_b)

    status_a, _ = _request_json(
        f"{base}/api/v1/me/preferences",
        method="PATCH",
        payload={"notificacoes_preco_habilitadas": False},
        user_session=token_a,
    )
    assert status_a == 200

    status_b, body_b = _request_json(
        f"{base}/api/v1/me/preferences",
        user_session=sessao_b.token,
    )
    assert status_b == 200
    assert body_b["dados"]["preferencias"]["notificacoes_preco_habilitadas"] is True
    assert personalization.obter_preferencias(conta_a.id).notificacoes_preco_habilitadas is False


def test_preferences_preservam_bearer_de_infraestrutura(
    tmp_path: Path,
):
    banco = tmp_path / "identity.sqlite3"
    identity_repository = UserIdentityRepository(banco)
    identity_service = UserIdentityService(identity_repository)
    personalization_service = UserPersonalizationService(
        UserPersonalizationRepository(banco),
        identity_repository,
    )

    conta = identity_service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    sessao = identity_service.emitir_sessao(conta)

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="segredo-infra",
        user_identity_service=identity_service,
        user_personalization_service=personalization_service,
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco
    base = f"http://127.0.0.1:{porta}"

    try:
        sem_infra, body = _request_json(
            f"{base}/api/v1/me/preferences",
            user_session=sessao.token,
        )
        assert sem_infra == 401
        assert body["erro"]["codigo"] == ("infraestrutura_nao_autorizada")

        com_infra, _ = _request_json(
            f"{base}/api/v1/me/preferences",
            user_session=sessao.token,
            infra_token="segredo-infra",
        )
        assert com_infra == 200
    finally:
        servidor.encerrar()


def test_runtime_injeta_personalizacao_no_mesmo_banco():
    source = RUNTIME.read_text(encoding="utf-8")
    assert "UserPersonalizationRepository" in source
    assert "UserPersonalizationService" in source
    assert "user_identity.sqlite3" in source
    assert ("user_personalization_service=" "user_personalization_service") in source


def test_watchlist_foi_aberta_pelo_bloco_posterior():
    source = (ROOT / "services" / "api_aplicacao" / "servidor.py").read_text(encoding="utf-8")

    assert "/api/v1/me/watchlist" in source
