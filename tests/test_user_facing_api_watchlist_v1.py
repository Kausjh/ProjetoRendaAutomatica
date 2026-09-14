from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
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
CONTRACT = ROOT / "contracts" / "user_facing_api_watchlist_v1.json"


def _request(
    url: str,
    *,
    method: str = "GET",
    payload: object | None = None,
    session: str | None = None,
    infra: str | None = None,
) -> tuple[int, dict[str, object]]:
    headers: dict[str, str] = {}

    if session is not None:
        headers["X-User-Session"] = session
    if infra is not None:
        headers["Authorization"] = f"Bearer {infra}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(
        url,
        method=method,
        headers=headers,
        data=data,
    )

    try:
        with urlopen(req, timeout=5) as response:
            return (
                response.status,
                json.loads(response.read().decode("utf-8")),
            )
    except HTTPError as error:
        return (
            error.code,
            json.loads(error.read().decode("utf-8")),
        )


@pytest.fixture
def api(tmp_path: Path):
    banco = tmp_path / "user_identity.sqlite3"
    identity_repository = UserIdentityRepository(banco)
    identity = UserIdentityService(identity_repository)
    personalization = UserPersonalizationService(
        UserPersonalizationRepository(banco),
        identity_repository,
    )

    conta = identity.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    sessao = identity.emitir_sessao(conta)

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="",
        user_identity_service=identity,
        user_personalization_service=personalization,
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco

    try:
        yield (
            f"http://127.0.0.1:{porta}",
            identity,
            personalization,
            conta,
            sessao.token,
        )
    finally:
        servidor.encerrar()


def test_contract_watchlist():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["schema"] == ("projeto-renda-automatica.user-facing-api-watchlist")
    paths = {(item["method"], item["path"]) for item in data["routes"]}
    assert ("GET", "/api/v1/me/watchlist") in paths
    assert (
        "PUT",
        "/api/v1/me/watchlist/{canonical_key}",
    ) in paths
    assert (
        "DELETE",
        "/api/v1/me/watchlist/{canonical_key}",
    ) in paths


def test_get_inicialmente_vazia(api):
    base, _, _, _, token = api
    status, body = _request(
        f"{base}/api/v1/me/watchlist",
        session=token,
    )
    assert status == 200
    assert body["dados"]["itens"] == []


def test_put_cria_e_lista_sem_ids_internos(api):
    base, _, _, _, token = api
    status, body = _request(
        f"{base}/api/v1/me/watchlist/amd_ryzen_7_5700x",
        method="PUT",
        payload={
            "preco_alvo": "999.90",
            "notificar_queda_preco": False,
        },
        session=token,
    )

    assert status == 200
    item = body["dados"]["item"]
    assert item["canonical_key"] == "amd_ryzen_7_5700x"
    assert item["preco_alvo"] == "999.90"
    assert item["notificar_queda_preco"] is False
    assert "conta_id" not in item
    assert "id" not in item

    status, body = _request(
        f"{base}/api/v1/me/watchlist",
        session=token,
    )
    assert status == 200
    assert len(body["dados"]["itens"]) == 1


def test_put_vazio_aplica_defaults(api):
    base, _, _, _, token = api
    status, body = _request(
        f"{base}/api/v1/me/watchlist/produto_x",
        method="PUT",
        payload={},
        session=token,
    )
    assert status == 200
    item = body["dados"]["item"]
    assert item["preco_alvo"] is None
    assert item["notificar_queda_preco"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"conta_id": "usr_outro"},
        {"canonical_key": "outra"},
        {"id": "wat_fake"},
        {"preco_alvo": True},
        {"preco_alvo": []},
        {"notificar_queda_preco": "true"},
    ],
)
def test_put_rejeita_payload_invalido(api, payload):
    base, _, _, _, token = api
    status, body = _request(
        f"{base}/api/v1/me/watchlist/produto_x",
        method="PUT",
        payload=payload,
        session=token,
    )
    assert status == 400
    assert body["erro"]["codigo"] == "payload_invalido"


@pytest.mark.parametrize(
    "preco",
    [0, -1, "0.00", "-10.50", "NaN"],
)
def test_put_rejeita_preco_invalido(api, preco):
    base, _, _, _, token = api
    status, body = _request(
        f"{base}/api/v1/me/watchlist/produto_x",
        method="PUT",
        payload={"preco_alvo": preco},
        session=token,
    )
    assert status == 400
    assert body["erro"]["codigo"] == "watchlist_invalida"


def test_delete_remove_item_da_conta(api):
    base, _, _, _, token = api
    criado, _ = _request(
        f"{base}/api/v1/me/watchlist/produto_x",
        method="PUT",
        payload={},
        session=token,
    )
    assert criado == 200

    status, body = _request(
        f"{base}/api/v1/me/watchlist/produto_x",
        method="DELETE",
        session=token,
    )
    assert status == 200
    assert body["dados"]["removido"] is True


def test_delete_cross_user_falha_fechado(api):
    base, identity, personalization, _, token_a = api

    conta_b = identity.criar_conta(
        email="outra@example.com",
        senha="outra-senha-forte-123",
    )
    personalization.adicionar_ou_atualizar_watchlist(
        conta_id=conta_b.id,
        canonical_key="produto_compartilhado",
    )

    status, body = _request(
        f"{base}/api/v1/me/watchlist/produto_compartilhado",
        method="DELETE",
        session=token_a,
    )
    assert status == 404
    assert body["erro"]["codigo"] == ("watchlist_item_nao_encontrado")
    assert len(personalization.listar_watchlist(conta_b.id)) == 1


def test_delete_inexistente_404(api):
    base, _, _, _, token = api
    status, body = _request(
        f"{base}/api/v1/me/watchlist/inexistente",
        method="DELETE",
        session=token,
    )
    assert status == 404
    assert body["erro"]["codigo"] == ("watchlist_item_nao_encontrado")


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("GET", "", None),
        ("PUT", "/produto_x", {}),
        ("DELETE", "/produto_x", None),
    ],
)
def test_watchlist_exige_sessao(
    api,
    method,
    suffix,
    payload,
):
    base, _, _, _, _ = api
    status, body = _request(
        f"{base}/api/v1/me/watchlist{suffix}",
        method=method,
        payload=payload,
    )
    assert status == 401
    assert body["erro"]["codigo"] == ("sessao_usuario_obrigatoria")


def test_canonical_key_encoded_no_path(api):
    base, _, _, _, token = api
    chave = "produto/com/barra"
    encoded = quote(chave, safe="")

    status, body = _request(
        f"{base}/api/v1/me/watchlist/{encoded}",
        method="PUT",
        payload={},
        session=token,
    )
    assert status == 200
    assert body["dados"]["item"]["canonical_key"] == chave


def test_bearer_de_infraestrutura_preservado(tmp_path: Path):
    banco = tmp_path / "identity.sqlite3"
    identity_repository = UserIdentityRepository(banco)
    identity = UserIdentityService(identity_repository)
    personalization = UserPersonalizationService(
        UserPersonalizationRepository(banco),
        identity_repository,
    )

    conta = identity.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    sessao = identity.emitir_sessao(conta)

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="segredo-infra",
        user_identity_service=identity,
        user_personalization_service=personalization,
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco
    base = f"http://127.0.0.1:{porta}"

    try:
        status, body = _request(
            f"{base}/api/v1/me/watchlist",
            session=sessao.token,
        )
        assert status == 401
        assert body["erro"]["codigo"] == ("infraestrutura_nao_autorizada")

        status, body = _request(
            f"{base}/api/v1/me/watchlist",
            session=sessao.token,
            infra="segredo-infra",
        )
        assert status == 200
        assert body["dados"]["itens"] == []
    finally:
        servidor.encerrar()
