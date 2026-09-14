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
CONTRACT = ROOT / "contracts" / "user_facing_api_register_login_v1.json"
RUNTIME = ROOT / "runtime.py"


def _post_json(
    url: str,
    payload: object,
    *,
    infra_token: str | None = None,
) -> tuple[int, dict[str, object]]:
    corpo = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }

    if infra_token is not None:
        headers["Authorization"] = f"Bearer {infra_token}"

    request = Request(
        url,
        data=corpo,
        headers=headers,
        method="POST",
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
        )
    finally:
        servidor.encerrar()


def test_contract_define_register_login():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["schema"] == ("projeto-renda-automatica.user-facing-api-register-login")
    assert data["register_login_version"] == 1

    routes = {(item["method"], item["path"]): item for item in data["routes"]}

    assert ("POST", "/api/v1/auth/register") in routes
    assert ("POST", "/api/v1/auth/login") in routes
    assert routes[("POST", "/api/v1/auth/register")]["returns_session"] is False
    assert routes[("POST", "/api/v1/auth/login")]["returns_session"] is True


def test_register_cria_conta_sem_retornar_segredos(api):
    base, identity = api

    status, body = _post_json(
        f"{base}/api/v1/auth/register",
        {
            "email": " Usuario@Example.com ",
            "senha": "uma-senha-forte-123",
        },
    )

    assert status == 201
    dados = body["dados"]
    assert isinstance(dados, dict)

    conta = dados["conta"]
    assert isinstance(conta, dict)
    assert conta["email"] == "Usuario@Example.com"
    assert conta["id"].startswith("usr_")
    assert "senha" not in json.dumps(body).lower()
    assert "sessao" not in dados

    autenticada = identity.autenticar(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    assert autenticada is not None


def test_register_email_duplicado_retorna_409(api):
    base, _ = api
    payload = {
        "email": "usuario@example.com",
        "senha": "uma-senha-forte-123",
    }

    primeiro, _ = _post_json(
        f"{base}/api/v1/auth/register",
        payload,
    )
    segundo, body = _post_json(
        f"{base}/api/v1/auth/register",
        payload,
    )

    assert primeiro == 201
    assert segundo == 409
    assert body["erro"]["codigo"] == "email_em_uso"


def test_register_payload_invalido_retorna_400(api):
    base, _ = api

    status, body = _post_json(
        f"{base}/api/v1/auth/register",
        {"email": "usuario@example.com"},
    )

    assert status == 400
    assert body["erro"]["codigo"] == "payload_invalido"


def test_login_emite_sessao_real(api):
    base, identity = api

    identity.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )

    status, body = _post_json(
        f"{base}/api/v1/auth/login",
        {
            "email": "usuario@example.com",
            "senha": "uma-senha-forte-123",
        },
    )

    assert status == 200
    dados = body["dados"]
    assert isinstance(dados, dict)

    sessao = dados["sessao"]
    assert isinstance(sessao, dict)
    token = sessao["token"]

    assert isinstance(token, str)
    assert token.startswith("pra_usr_v1_")
    assert sessao["expira_em"]

    conta = identity.resolver_sessao(token)
    assert conta is not None
    assert conta.email == "usuario@example.com"


def test_login_invalido_retorna_erro_generico(api):
    base, identity = api

    identity.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )

    status, body = _post_json(
        f"{base}/api/v1/auth/login",
        {
            "email": "usuario@example.com",
            "senha": "senha-errada-999",
        },
    )

    assert status == 401
    assert body["erro"]["codigo"] == "credenciais_invalidas"
    assert body["erro"]["mensagem"] == "Credenciais invalidas."


def test_login_email_inexistente_tem_mesmo_erro(api):
    base, _ = api

    status, body = _post_json(
        f"{base}/api/v1/auth/login",
        {
            "email": "inexistente@example.com",
            "senha": "uma-senha-forte-123",
        },
    )

    assert status == 401
    assert body["erro"]["codigo"] == "credenciais_invalidas"
    assert body["erro"]["mensagem"] == "Credenciais invalidas."


def test_register_login_respeitam_bearer_de_infraestrutura(
    tmp_path: Path,
):
    identity = UserIdentityService(UserIdentityRepository(tmp_path / "identity.sqlite3"))

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
        sem_token, body = _post_json(
            f"{base}/api/v1/auth/register",
            {
                "email": "usuario@example.com",
                "senha": "uma-senha-forte-123",
            },
        )

        assert sem_token == 401
        assert body["erro"]["codigo"] == ("infraestrutura_nao_autorizada")

        com_token, _ = _post_json(
            f"{base}/api/v1/auth/register",
            {
                "email": "usuario@example.com",
                "senha": "uma-senha-forte-123",
            },
            infra_token="segredo-infra",
        )

        assert com_token == 201
    finally:
        servidor.encerrar()


def test_identidade_ausente_retorna_503():
    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="",
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco
    base = f"http://127.0.0.1:{porta}"

    try:
        status, body = _post_json(
            f"{base}/api/v1/auth/register",
            {
                "email": "usuario@example.com",
                "senha": "uma-senha-forte-123",
            },
        )

        assert status == 503
        assert body["erro"]["codigo"] == ("identidade_usuario_indisponivel")
    finally:
        servidor.encerrar()


def test_runtime_injeta_servico_real_de_identidade():
    source = RUNTIME.read_text(encoding="utf-8")

    assert "UserIdentityRepository" in source
    assert "UserIdentityService" in source
    assert "user_identity.sqlite3" in source
    assert "user_identity_service=user_identity_service" in source


def test_logout_e_me_ainda_nao_foram_abertos():
    source = (ROOT / "services" / "api_aplicacao" / "servidor.py").read_text(encoding="utf-8")

    assert "/api/v1/auth/logout" not in source
    assert 'rota == "/api/v1/me"' not in source
    assert "/api/v1/me/preferences" not in source
    assert "/api/v1/me/watchlist" not in source
