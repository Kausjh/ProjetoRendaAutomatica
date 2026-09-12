import json

import httpx
import pytest

from models.inteligencia_ai import (
    SolicitacaoInteligenciaAI,
)
from services.inteligencia_assistiva_ai import (
    interpretar_com_inteligencia_assistiva,
)
from services.provedor_http_inteligencia_ai import (
    LIMITE_REQUISICAO_BYTES_PADRAO,
    LIMITE_RESPOSTA_BYTES_PADRAO,
    SCHEMA_VERSION,
    TIMEOUT_SEGUNDOS_PADRAO,
    ContratoProvedorHttpInteligenciaAIInvalido,
    ErroProvedorHttpInteligenciaAI,
    LimitePayloadProvedorHttpInteligenciaAIExcedido,
    ProvedorHttpInteligenciaAI,
    TimeoutProvedorHttpInteligenciaAI,
)


def _solicitacao(
    contexto=None,
):
    if contexto is None:
        contexto = {
            "titulo": "RTX 5070",
        }

    return SolicitacaoInteligenciaAI(
        tarefa="classificar_produto",
        contexto=contexto,
    )


def _json_response(
    *,
    conteudo=None,
    confianca=0.95,
    schema_version=SCHEMA_VERSION,
    status_code=200,
    headers=None,
):
    if conteudo is None:
        conteudo = {
            "categoria_sugerida": "gpu",
        }

    if headers is None:
        headers = {
            "content-type": "application/json",
        }

    return httpx.Response(
        status_code,
        headers=headers,
        json={
            "schema_version": schema_version,
            "conteudo": conteudo,
            "confianca": confianca,
        },
    )


def _provedor(
    handler,
    **kwargs,
):
    transport = httpx.MockTransport(handler)

    return ProvedorHttpInteligenciaAI(
        endpoint="https://ai-gateway.example/v1/interpretar",
        provedor="gateway-teste",
        modelo="modelo-teste",
        transport=transport,
        **kwargs,
    )


def test_constantes_de_seguranca():
    assert TIMEOUT_SEGUNDOS_PADRAO == 10.0

    assert LIMITE_REQUISICAO_BYTES_PADRAO == 128 * 1024

    assert LIMITE_RESPOSTA_BYTES_PADRAO == 64 * 1024


def test_chamada_valida_retorna_modelo_normalizado():
    recebido = {}

    def handler(
        request,
    ):
        recebido["method"] = request.method
        recebido["url"] = str(request.url)
        recebido["body"] = json.loads(request.content.decode("utf-8"))

        return _json_response()

    provedor = _provedor(handler)

    resposta = provedor.interpretar(_solicitacao())

    assert recebido["method"] == "POST"

    assert recebido["url"] == "https://ai-gateway.example/v1/interpretar"

    assert recebido["body"] == {
        "schema_version": 1,
        "tarefa": "classificar_produto",
        "contexto": {
            "titulo": "RTX 5070",
        },
        "modelo": "modelo-teste",
    }

    assert resposta.conteudo == {
        "categoria_sugerida": "gpu",
    }

    assert resposta.confianca == 0.95
    assert resposta.provedor == "gateway-teste"
    assert resposta.modelo == "modelo-teste"


def test_adapter_nao_envia_autoridade_operacional():
    recebido = {}

    def handler(
        request,
    ):
        recebido.update(json.loads(request.content.decode("utf-8")))

        return _json_response()

    provedor = _provedor(handler)

    provedor.interpretar(_solicitacao())

    proibidos = {
        "autoriza_publicacao",
        "autoriza_alteracao_budget",
        "substitui_regras_deterministicas",
        "publicar",
        "budget",
    }

    assert proibidos.intersection(recebido) == set()


def test_cabecalho_de_autenticacao_generico_e_encaminhado():
    recebido = {}

    def handler(
        request,
    ):
        recebido["x-api-key"] = request.headers.get("x-api-key")

        return _json_response()

    provedor = _provedor(
        handler,
        cabecalhos={
            "X-Api-Key": "segredo-de-teste",
        },
    )

    provedor.interpretar(_solicitacao())

    assert recebido["x-api-key"] == "segredo-de-teste"


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.com/v1",
        "ftp://example.com/v1",
        "https://usuario:senha@example.com/v1",
        "https://example.com/v1#fragmento",
        "sem-url",
    ],
)
def test_endpoint_inseguro_ou_invalido_e_rejeitado(
    endpoint,
):
    with pytest.raises(ValueError):
        ProvedorHttpInteligenciaAI(
            endpoint=endpoint,
            provedor="teste",
        )


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://localhost:8000/v1",
        "http://127.0.0.1:8000/v1",
        "http://[::1]:8000/v1",
        "https://example.com/v1",
    ],
)
def test_endpoints_seguros_aceitos(
    endpoint,
):
    ProvedorHttpInteligenciaAI(
        endpoint=endpoint,
        provedor="teste",
    )


def test_redirect_nao_e_seguido():
    chamadas = []

    def handler(
        request,
    ):
        chamadas.append(str(request.url))

        return httpx.Response(
            302,
            headers={
                "location": "https://outro.example/",
                "content-type": "application/json",
            },
            json={},
        )

    provedor = _provedor(handler)

    with pytest.raises(ErroProvedorHttpInteligenciaAI):
        provedor.interpretar(_solicitacao())

    assert len(chamadas) == 1


def test_status_http_de_erro_falha():
    def handler(
        request,
    ):
        return httpx.Response(
            503,
            headers={
                "content-type": "application/json",
            },
            json={
                "erro": "indisponivel",
            },
        )

    provedor = _provedor(handler)

    with pytest.raises(ErroProvedorHttpInteligenciaAI):
        provedor.interpretar(_solicitacao())


def test_timeout_e_convertido_para_erro_controlado():
    def handler(
        request,
    ):
        raise httpx.ReadTimeout(
            "timeout",
            request=request,
        )

    provedor = _provedor(handler)

    with pytest.raises(TimeoutProvedorHttpInteligenciaAI):
        provedor.interpretar(_solicitacao())


def test_content_type_precisa_ser_json():
    def handler(
        request,
    ):
        return httpx.Response(
            200,
            headers={
                "content-type": "text/plain",
            },
            content=b"{}",
        )

    provedor = _provedor(handler)

    with pytest.raises(ContratoProvedorHttpInteligenciaAIInvalido):
        provedor.interpretar(_solicitacao())


def test_json_malformado_e_rejeitado():
    def handler(
        request,
    ):
        return httpx.Response(
            200,
            headers={
                "content-type": "application/json",
            },
            content=b"{invalido",
        )

    provedor = _provedor(handler)

    with pytest.raises(ContratoProvedorHttpInteligenciaAIInvalido):
        provedor.interpretar(_solicitacao())


def test_raiz_precisa_ser_objeto():
    def handler(
        request,
    ):
        return httpx.Response(
            200,
            headers={
                "content-type": "application/json",
            },
            json=[
                {
                    "conteudo": {},
                }
            ],
        )

    provedor = _provedor(handler)

    with pytest.raises(ContratoProvedorHttpInteligenciaAIInvalido):
        provedor.interpretar(_solicitacao())


@pytest.mark.parametrize(
    "payload",
    [
        {
            "schema_version": 1,
            "conteudo": {},
        },
        {
            "schema_version": 1,
            "conteudo": {},
            "confianca": 0.9,
            "extra": True,
        },
        {
            "schema_version": 2,
            "conteudo": {},
            "confianca": 0.9,
        },
        {
            "schema_version": 1,
            "conteudo": [],
            "confianca": 0.9,
        },
        {
            "schema_version": 1,
            "conteudo": {},
            "confianca": True,
        },
        {
            "schema_version": 1,
            "conteudo": {},
            "confianca": 2.0,
        },
    ],
)
def test_contrato_json_estrito(
    payload,
):
    def handler(
        request,
    ):
        return httpx.Response(
            200,
            headers={
                "content-type": "application/json",
            },
            json=payload,
        )

    provedor = _provedor(handler)

    with pytest.raises(ContratoProvedorHttpInteligenciaAIInvalido):
        provedor.interpretar(_solicitacao())


def test_limite_de_resposta_e_aplicado():
    conteudo = {
        "texto": ("x" * 5000),
    }

    def handler(
        request,
    ):
        return _json_response(conteudo=conteudo)

    provedor = _provedor(
        handler,
        limite_resposta_bytes=200,
    )

    with pytest.raises(LimitePayloadProvedorHttpInteligenciaAIExcedido):
        provedor.interpretar(_solicitacao())


def test_limite_de_requisicao_e_aplicado():
    provedor = _provedor(
        lambda request: _json_response(),
        limite_requisicao_bytes=100,
    )

    solicitacao = _solicitacao(
        contexto={
            "texto": ("x" * 1000),
        }
    )

    with pytest.raises(LimitePayloadProvedorHttpInteligenciaAIExcedido):
        provedor.interpretar(solicitacao)


def test_contexto_nao_serializavel_e_rejeitado():
    solicitacao = _solicitacao(
        contexto={
            "objeto": object(),
        }
    )

    provedor = _provedor(lambda request: _json_response())

    with pytest.raises(ContratoProvedorHttpInteligenciaAIInvalido):
        provedor.interpretar(solicitacao)


def test_integracao_com_orquestrador_v19a():
    def handler(
        request,
    ):
        return _json_response(
            conteudo={
                "categoria_sugerida": "gpu",
            },
            confianca=0.95,
        )

    provedor = _provedor(handler)

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=provedor,
        validador=lambda sugestao: (sugestao.get("categoria_sugerida") == "gpu"),
    )

    assert resultado.status == "sugestao_ai_validada"
    assert resultado.fallback_usado is False
    assert resultado.autoriza_publicacao is False
    assert resultado.autoriza_alteracao_budget is False
    assert resultado.substitui_regras_deterministicas is False


def test_erro_http_integra_com_fail_open_da_v19a():
    def handler(
        request,
    ):
        return httpx.Response(
            500,
            headers={
                "content-type": "application/json",
            },
            json={},
        )

    provedor = _provedor(handler)

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=provedor,
        validador=lambda sugestao: True,
    )

    assert resultado.status == "erro_provedor"
    assert resultado.fallback_usado is True

    assert resultado.tipo_erro == "ErroProvedorHttpInteligenciaAI"

    assert resultado.sugestao == {
        "categoria_sugerida": "outros",
    }


@pytest.mark.parametrize(
    "cabecalhos",
    [
        {
            "Accept": "text/plain",
        },
        {
            "Content-Type": "text/plain",
        },
    ],
)
def test_headers_de_contrato_nao_podem_ser_sobrescritos(
    cabecalhos,
):
    with pytest.raises(ValueError):
        ProvedorHttpInteligenciaAI(
            endpoint="https://example.com/v1",
            provedor="teste",
            cabecalhos=cabecalhos,
        )


@pytest.mark.parametrize(
    "campo,valor",
    [
        (
            "timeout_segundos",
            0,
        ),
        (
            "timeout_segundos",
            -1,
        ),
        (
            "limite_requisicao_bytes",
            0,
        ),
        (
            "limite_resposta_bytes",
            -1,
        ),
    ],
)
def test_limites_invalidos_sao_rejeitados(
    campo,
    valor,
):
    kwargs = {
        campo: valor,
    }

    with pytest.raises(ValueError):
        ProvedorHttpInteligenciaAI(
            endpoint="https://example.com/v1",
            provedor="teste",
            **kwargs,
        )
