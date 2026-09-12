from __future__ import annotations

import json

import httpx
import pytest

from models.inteligencia_ai import (
    SolicitacaoInteligenciaAI,
)
from services.provedor_openai_responses_ai import (
    ContratoOpenAIResponsesAIInvalido,
    ErroProvedorOpenAIResponsesAI,
    ProvedorOpenAIResponsesAI,
    TimeoutOpenAIResponsesAI,
)


def _solicitacao() -> SolicitacaoInteligenciaAI:
    return SolicitacaoInteligenciaAI(
        tarefa="avaliar_provider_ai",
        contexto={
            "entrada": "ping",
        },
    )


def _response_ok(
    *,
    conteudo=None,
    confianca=0.99,
    usage=True,
):
    if conteudo is None:
        conteudo = {
            "resultado": "ok",
        }

    payload = {
        "id": "resp_teste",
        "object": "response",
        "status": "completed",
        "model": "gpt-5.6-luna",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "conteudo": conteudo,
                                "confianca": confianca,
                            }
                        ),
                    }
                ],
            }
        ],
    }

    if usage:
        payload["usage"] = {
            "input_tokens": 20,
            "output_tokens": 8,
            "total_tokens": 28,
        }

    return payload


def test_adapter_envia_responses_api_sem_store() -> None:
    capturado = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        capturado["authorization"] = request.headers["Authorization"]
        capturado["payload"] = json.loads(request.content.decode("utf-8"))

        return httpx.Response(
            200,
            headers={
                "Content-Type": "application/json",
            },
            json=_response_ok(),
        )

    provedor = ProvedorOpenAIResponsesAI(
        api_key="segredo-teste",
        transport=httpx.MockTransport(handler),
    )

    resposta = provedor.interpretar(_solicitacao())

    assert capturado["authorization"] == "Bearer segredo-teste"

    payload = capturado["payload"]

    assert payload["model"] == "gpt-5.6-luna"
    assert payload["store"] is False
    assert payload["max_output_tokens"] == 200

    entrada = json.loads(payload["input"])

    assert entrada["tarefa"] == "avaliar_provider_ai"
    assert entrada["contexto"] == {
        "entrada": "ping",
    }

    assert resposta.conteudo == {
        "resultado": "ok",
    }
    assert resposta.confianca == 0.99
    assert resposta.provedor == "openai"
    assert resposta.modelo == "gpt-5.6-luna"


def test_adapter_converte_usage_sem_inventar_custo() -> None:
    provedor = ProvedorOpenAIResponsesAI(
        api_key="segredo-teste",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={
                    "Content-Type": "application/json",
                },
                json=_response_ok(),
            )
        ),
    )

    resposta = provedor.interpretar(_solicitacao())

    assert resposta.uso is not None
    assert resposta.uso.tokens_entrada == 20
    assert resposta.uso.tokens_saida == 8
    assert resposta.uso.tokens_total == 28
    assert resposta.uso.custo_estimado_usd is None


def test_adapter_aceita_usage_ausente() -> None:
    provedor = ProvedorOpenAIResponsesAI(
        api_key="segredo-teste",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={
                    "Content-Type": "application/json",
                },
                json=_response_ok(usage=False),
            )
        ),
    )

    resposta = provedor.interpretar(_solicitacao())

    assert resposta.uso is None


def test_adapter_rejeita_json_do_modelo_com_campos_extras() -> None:
    payload = _response_ok()

    payload["output"][0]["content"][0]["text"] = json.dumps(
        {
            "conteudo": {
                "resultado": "ok",
            },
            "confianca": 0.99,
            "autoriza_publicacao": True,
        }
    )

    provedor = ProvedorOpenAIResponsesAI(
        api_key="segredo-teste",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        ),
    )

    with pytest.raises(ContratoOpenAIResponsesAIInvalido):
        provedor.interpretar(_solicitacao())


def test_adapter_rejeita_confianca_fora_da_faixa() -> None:
    provedor = ProvedorOpenAIResponsesAI(
        api_key="segredo-teste",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={
                    "Content-Type": "application/json",
                },
                json=_response_ok(confianca=1.5),
            )
        ),
    )

    with pytest.raises(ContratoOpenAIResponsesAIInvalido):
        provedor.interpretar(_solicitacao())


def test_adapter_rejeita_refusal() -> None:
    payload = _response_ok()
    payload["output"][0]["content"] = [
        {
            "type": "refusal",
            "refusal": "nao posso",
        }
    ]

    provedor = ProvedorOpenAIResponsesAI(
        api_key="segredo-teste",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        ),
    )

    with pytest.raises(ContratoOpenAIResponsesAIInvalido):
        provedor.interpretar(_solicitacao())


def test_adapter_rejeita_http_redirect_sem_seguir() -> None:
    provedor = ProvedorOpenAIResponsesAI(
        api_key="segredo-teste",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                302,
                headers={
                    "Location": ("https://example.com/"),
                    "Content-Type": "application/json",
                },
                json={
                    "redirect": True,
                },
            )
        ),
    )

    with pytest.raises(ErroProvedorOpenAIResponsesAI):
        provedor.interpretar(_solicitacao())


def test_adapter_converte_timeout() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ReadTimeout(
            "timeout",
            request=request,
        )

    provedor = ProvedorOpenAIResponsesAI(
        api_key="segredo-teste",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(TimeoutOpenAIResponsesAI):
        provedor.interpretar(_solicitacao())


def test_adapter_rejeita_endpoint_http_remoto() -> None:
    with pytest.raises(
        ValueError,
        match="HTTPS",
    ):
        ProvedorOpenAIResponsesAI(
            api_key="segredo-teste",
            endpoint=("http://api.openai.com/v1/responses"),
        )


def test_adapter_nao_expoe_api_key_no_repr() -> None:
    provedor = ProvedorOpenAIResponsesAI(
        api_key="segredo-super-secreto",
    )

    assert "segredo-super-secreto" not in repr(provedor)


def test_adapter_rejeita_host_https_estranho() -> None:
    with pytest.raises(
        ValueError,
        match="api.openai.com",
    ):
        ProvedorOpenAIResponsesAI(
            api_key="segredo-teste",
            endpoint=("https://example.com/v1/responses"),
        )


def test_adapter_rejeita_path_openai_inesperado() -> None:
    with pytest.raises(
        ValueError,
        match="/v1/responses",
    ):
        ProvedorOpenAIResponsesAI(
            api_key="segredo-teste",
            endpoint=("https://api.openai.com/v1/chat/completions"),
        )
