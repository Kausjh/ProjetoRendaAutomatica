from __future__ import annotations

import json
from email.message import Message
from io import BytesIO
from pathlib import Path

import pytest

from models.user_identity import ContaUsuario
from services.api_aplicacao.servidor import ServidorApiAplicacao
from services.api_aplicacao.user_facing_http import (
    DEFAULT_MAX_JSON_BODY_BYTES,
    ErroHttpUserFacing,
    UserFacingHttpFoundation,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "user_facing_api_http_foundation_v1.json"
SERVER = ROOT / "services" / "api_aplicacao" / "servidor.py"


class IdentityFake:
    def __init__(self, conta: ContaUsuario | None) -> None:
        self.conta = conta
        self.tokens: list[str] = []

    def resolver_sessao(self, token: str) -> ContaUsuario | None:
        self.tokens.append(token)
        return self.conta


def _headers(**values: str) -> Message:
    headers = Message()

    for key, value in values.items():
        headers[key.replace("_", "-")] = value

    return headers


def _json_request(payload: object) -> tuple[Message, BytesIO]:
    corpo = json.dumps(payload).encode("utf-8")
    return (
        _headers(
            Content_Type="application/json; charset=utf-8",
            Content_Length=str(len(corpo)),
        ),
        BytesIO(corpo),
    )


def test_contract_define_http_foundation_sem_rotas_de_negocio():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["schema"] == ("projeto-renda-automatica.user-facing-api-http-foundation")
    assert data["http_foundation_version"] == 1
    assert data["stage"] == "http-foundation"
    assert data["new_business_routes"] is False


def test_json_objeto_valido():
    foundation = UserFacingHttpFoundation()
    headers, stream = _json_request(
        {
            "email": "usuario@example.com",
            "senha": "segredo",
        }
    )

    payload = foundation.ler_json_objeto(
        headers=headers,
        stream=stream,
    )

    assert payload["email"] == "usuario@example.com"
    assert payload["senha"] == "segredo"


def test_content_type_invalido_retorna_415():
    foundation = UserFacingHttpFoundation()
    corpo = b"{}"
    headers = _headers(
        Content_Type="text/plain",
        Content_Length=str(len(corpo)),
    )

    with pytest.raises(ErroHttpUserFacing) as erro:
        foundation.ler_json_objeto(
            headers=headers,
            stream=BytesIO(corpo),
        )

    assert erro.value.status == 415
    assert erro.value.codigo == "content_type_invalido"


def test_content_length_ausente_retorna_400():
    foundation = UserFacingHttpFoundation()
    headers = _headers(Content_Type="application/json")

    with pytest.raises(ErroHttpUserFacing) as erro:
        foundation.ler_json_objeto(
            headers=headers,
            stream=BytesIO(b"{}"),
        )

    assert erro.value.status == 400
    assert erro.value.codigo == "content_length_ausente"


def test_content_length_invalido_retorna_400():
    foundation = UserFacingHttpFoundation()
    headers = _headers(
        Content_Type="application/json",
        Content_Length="nao-numero",
    )

    with pytest.raises(ErroHttpUserFacing) as erro:
        foundation.ler_json_objeto(
            headers=headers,
            stream=BytesIO(b"{}"),
        )

    assert erro.value.status == 400
    assert erro.value.codigo == "content_length_invalido"


def test_payload_grande_retorna_413_sem_ler_stream():
    foundation = UserFacingHttpFoundation()
    headers = _headers(
        Content_Type="application/json",
        Content_Length=str(DEFAULT_MAX_JSON_BODY_BYTES + 1),
    )

    with pytest.raises(ErroHttpUserFacing) as erro:
        foundation.ler_json_objeto(
            headers=headers,
            stream=BytesIO(b""),
        )

    assert erro.value.status == 413
    assert erro.value.codigo == "payload_muito_grande"


def test_json_invalido_retorna_400():
    foundation = UserFacingHttpFoundation()
    corpo = b"{"
    headers = _headers(
        Content_Type="application/json",
        Content_Length=str(len(corpo)),
    )

    with pytest.raises(ErroHttpUserFacing) as erro:
        foundation.ler_json_objeto(
            headers=headers,
            stream=BytesIO(corpo),
        )

    assert erro.value.status == 400
    assert erro.value.codigo == "json_invalido"


def test_json_precisa_ser_objeto():
    foundation = UserFacingHttpFoundation()
    headers, stream = _json_request(["nao", "objeto"])

    with pytest.raises(ErroHttpUserFacing) as erro:
        foundation.ler_json_objeto(
            headers=headers,
            stream=stream,
        )

    assert erro.value.status == 400
    assert erro.value.codigo == "json_objeto_obrigatorio"


def test_envelope_de_sucesso_e_erro():
    sucesso = UserFacingHttpFoundation.sucesso({"id": "usr_1"})
    erro = ErroHttpUserFacing(
        401,
        "sessao_usuario_invalida",
        "Sessao de usuario invalida.",
    )

    assert sucesso == {
        "api_version": "v1",
        "dados": {"id": "usr_1"},
    }
    assert erro.payload() == {
        "api_version": "v1",
        "erro": {
            "codigo": "sessao_usuario_invalida",
            "mensagem": "Sessao de usuario invalida.",
        },
    }


def test_extrai_x_user_session():
    token = "pra_usr_v1_token-seguro"
    headers = _headers(X_User_Session=token)

    assert (
        UserFacingHttpFoundation.extrair_token_sessao(
            headers,
            obrigatorio=True,
        )
        == token
    )


def test_sessao_ausente_falha_fechada():
    with pytest.raises(ErroHttpUserFacing) as erro:
        UserFacingHttpFoundation.extrair_token_sessao(
            _headers(),
            obrigatorio=True,
        )

    assert erro.value.status == 401
    assert erro.value.codigo == "sessao_usuario_obrigatoria"


def test_prefixo_de_sessao_invalido_falha_fechada():
    headers = _headers(X_User_Session="outro_token")

    with pytest.raises(ErroHttpUserFacing) as erro:
        UserFacingHttpFoundation.extrair_token_sessao(
            headers,
            obrigatorio=True,
        )

    assert erro.value.status == 401
    assert erro.value.codigo == "sessao_usuario_invalida"


def test_resolve_usuario_pelo_servico_de_identidade():
    conta = ContaUsuario(
        id="usr_teste",
        email="usuario@example.com",
        criado_em="2026-09-13T20:00:00+00:00",
        ativa=True,
    )
    identity = IdentityFake(conta)
    foundation = UserFacingHttpFoundation(
        user_identity_service=identity,  # type: ignore[arg-type]
    )
    token = "pra_usr_v1_token-valido"

    resolvida = foundation.resolver_usuario(_headers(X_User_Session=token))

    assert resolvida.id == "usr_teste"
    assert identity.tokens == [token]


def test_sessao_nao_resolvida_retorna_401():
    identity = IdentityFake(None)
    foundation = UserFacingHttpFoundation(
        user_identity_service=identity,  # type: ignore[arg-type]
    )

    with pytest.raises(ErroHttpUserFacing) as erro:
        foundation.resolver_usuario(_headers(X_User_Session="pra_usr_v1_invalido"))

    assert erro.value.status == 401
    assert erro.value.codigo == "sessao_usuario_invalida"


def test_identity_service_ausente_retorna_503():
    foundation = UserFacingHttpFoundation()

    with pytest.raises(ErroHttpUserFacing) as erro:
        foundation.resolver_usuario(_headers(X_User_Session="pra_usr_v1_valido"))

    assert erro.value.status == 503
    assert erro.value.codigo == "identidade_usuario_indisponivel"


def test_servidor_expoe_foundation_sem_mudar_construtor_basico():
    controlador = object()
    servidor = ServidorApiAplicacao(
        controlador,  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="",
    )

    assert isinstance(
        servidor.user_facing_http,
        UserFacingHttpFoundation,
    )


def test_servidor_ainda_nao_contem_rotas_user_facing():
    source = SERVER.read_text(encoding="utf-8")

    routes = (
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/me",
        "/api/v1/me/preferences",
        "/api/v1/me/watchlist",
    )

    assert all(route not in source for route in routes)
