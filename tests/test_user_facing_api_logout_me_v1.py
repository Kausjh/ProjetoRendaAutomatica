from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from repositories.user_identity_repository import UserIdentityRepository
from services.api_aplicacao.servidor import ServidorApiAplicacao
from services.user_identity_service import UserIdentityService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "user_facing_api_logout_me_v1.json"


def _request_json(
    url: str,
    *,
    method: str = "GET",
    user_session: str | None = None,
    infra_token: str | None = None,
) -> tuple[int, dict[str, object]]:
    headers: dict[str, str] = {}

    if user_session is not None:
        headers["X-User-Session"] = user_session

    if infra_token is not None:
        headers["Authorization"] = f"Bearer {infra_token}"

    request = Request(
        url,
        headers=headers,
        method=method,
        data=b"" if method == "POST" else None,
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
    repository = UserIdentityRepository(tmp_path / "user_identity.sqlite3")
    identity = UserIdentityService(repository)

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
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco

    try:
        yield (
            f"http://127.0.0.1:{porta}",
            identity,
            conta,
            sessao.token,
        )
    finally:
        servidor.encerrar()


def test_contract_define_logout_me():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["schema"] == ("projeto-renda-automatica.user-facing-api-logout-me")
    assert data["logout_me_version"] == 1

    routes = {(item["method"], item["path"]): item for item in data["routes"]}

    assert ("POST", "/api/v1/auth/logout") in routes
    assert ("GET", "/api/v1/me") in routes
    assert all(item["requires_user_session"] is True for item in routes.values())


def test_me_retorna_conta_da_sessao(api):
    base, _, conta, token = api

    status, body = _request_json(
        f"{base}/api/v1/me",
        user_session=token,
    )

    assert status == 200
    dados = body["dados"]
    assert isinstance(dados, dict)

    publica = dados["conta"]
    assert isinstance(publica, dict)
    assert publica["id"] == conta.id
    assert publica["email"] == conta.email
    assert publica["ativa"] is True
    assert "token" not in json.dumps(body).lower()


def test_me_ignora_conta_id_do_cliente(api):
    base, identity, conta, token = api

    outra = identity.criar_conta(
        email="outra@example.com",
        senha="outra-senha-forte-123",
    )

    status, body = _request_json(
        f"{base}/api/v1/me?conta_id={outra.id}",
        user_session=token,
    )

    assert status == 200
    dados = body["dados"]
    assert isinstance(dados, dict)
    publica = dados["conta"]
    assert isinstance(publica, dict)

    assert publica["id"] == conta.id
    assert publica["id"] != outra.id


def test_me_sem_sessao_retorna_401(api):
    base, _, _, _ = api

    status, body = _request_json(
        f"{base}/api/v1/me",
    )

    assert status == 401
    assert body["erro"]["codigo"] == ("sessao_usuario_obrigatoria")


def test_logout_revoga_somente_sessao_atual(api):
    base, identity, conta, token_atual = api
    outra_sessao = identity.emitir_sessao(conta)

    status, body = _request_json(
        f"{base}/api/v1/auth/logout",
        method="POST",
        user_session=token_atual,
    )

    assert status == 200
    assert body["dados"]["sessao_revogada"] is True
    assert identity.resolver_sessao(token_atual) is None
    assert identity.resolver_sessao(outra_sessao.token) is not None


def test_token_revogado_falha_no_me(api):
    base, _, _, token = api

    logout_status, _ = _request_json(
        f"{base}/api/v1/auth/logout",
        method="POST",
        user_session=token,
    )
    assert logout_status == 200

    status, body = _request_json(
        f"{base}/api/v1/me",
        user_session=token,
    )

    assert status == 401
    assert body["erro"]["codigo"] == "sessao_usuario_invalida"


def test_logout_sem_sessao_retorna_401(api):
    base, _, _, _ = api

    status, body = _request_json(
        f"{base}/api/v1/auth/logout",
        method="POST",
    )

    assert status == 401
    assert body["erro"]["codigo"] == ("sessao_usuario_obrigatoria")


def test_me_preserva_bearer_de_infraestrutura(
    tmp_path: Path,
):
    identity = UserIdentityService(UserIdentityRepository(tmp_path / "identity.sqlite3"))
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
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco
    base = f"http://127.0.0.1:{porta}"

    try:
        sem_infra, body = _request_json(
            f"{base}/api/v1/me",
            user_session=sessao.token,
        )

        assert sem_infra == 401
        assert body["erro"]["codigo"] == ("infraestrutura_nao_autorizada")

        com_infra, body = _request_json(
            f"{base}/api/v1/me",
            user_session=sessao.token,
            infra_token="segredo-infra",
        )

        assert com_infra == 200
        assert body["dados"]["conta"]["id"] == conta.id
    finally:
        servidor.encerrar()


def test_preferences_abertas_e_watchlist_ainda_fechada():
    source = (ROOT / "services" / "api_aplicacao" / "servidor.py").read_text(encoding="utf-8")

    assert "/api/v1/me/preferences" in source
    assert "/api/v1/me/watchlist" not in source
