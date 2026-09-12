from __future__ import annotations

import httpx
import pytest

from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
    SolicitacaoInteligenciaAI,
)
from models.observabilidade_ai import (
    UsoInteligenciaAI,
)
from services.controle_operacional_ai import (
    ControleOperacionalInteligenciaAI,
)
from services.inteligencia_assistiva_ai import (
    interpretar_com_inteligencia_assistiva,
)
from services.provedor_http_inteligencia_ai import (
    SCHEMA_VERSION,
    ContratoProvedorHttpInteligenciaAIInvalido,
    ProvedorHttpInteligenciaAI,
)


def _solicitacao():
    return SolicitacaoInteligenciaAI(
        tarefa="teste_usage_v19e3",
        contexto={
            "titulo": "RTX 5070",
        },
    )


def _provedor(
    handler,
):
    return ProvedorHttpInteligenciaAI(
        endpoint=("https://ai.example.test/" "interpretar"),
        provedor="fake-http",
        modelo="fake-v1",
        transport=httpx.MockTransport(handler),
    )


def _response(
    *,
    uso_incluido=False,
    uso=None,
    confianca=0.95,
    extras=None,
):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "conteudo": {
            "categoria_sugerida": "gpu",
        },
        "confianca": confianca,
    }

    if uso_incluido:
        payload["uso"] = uso

    if extras:
        payload.update(extras)

    return httpx.Response(
        200,
        headers={
            "content-type": "application/json",
        },
        json=payload,
    )


def test_modelo_preserva_backward_compatibility_sem_usage():
    resposta = RespostaProvedorInteligenciaAI(
        conteudo={
            "ok": True,
        },
        confianca=0.9,
        provedor="fake",
    )

    assert resposta.uso is None


def test_modelo_aceita_usage_tipado():
    uso = UsoInteligenciaAI(
        tokens_entrada=100,
        tokens_saida=20,
        tokens_total=120,
        custo_estimado_usd=0.002,
    )

    resposta = RespostaProvedorInteligenciaAI(
        conteudo={
            "ok": True,
        },
        confianca=0.9,
        provedor="fake",
        uso=uso,
    )

    assert resposta.uso is uso


def test_modelo_rejeita_usage_nao_tipado():
    with pytest.raises(TypeError):
        RespostaProvedorInteligenciaAI(
            conteudo={},
            confianca=0.9,
            provedor="fake",
            uso={
                "tokens_total": 10,
            },
        )


def test_provider_preserva_resposta_antiga_sem_usage():
    def handler(
        request,
    ):
        return _response()

    resposta = _provedor(handler).interpretar(_solicitacao())

    assert resposta.uso is None
    assert resposta.confianca == 0.95


def test_provider_converte_usage_completo():
    def handler(
        request,
    ):
        return _response(
            uso_incluido=True,
            uso={
                "tokens_entrada": 100,
                "tokens_saida": 25,
                "tokens_total": 125,
                "custo_estimado_usd": 0.0025,
            },
        )

    resposta = _provedor(handler).interpretar(_solicitacao())

    assert resposta.uso is not None
    assert resposta.uso.tokens_entrada == 100
    assert resposta.uso.tokens_saida == 25
    assert resposta.uso.tokens_total == 125

    assert resposta.uso.custo_estimado_usd == pytest.approx(0.0025)


def test_provider_aceita_usage_parcial():
    def handler(
        request,
    ):
        return _response(
            uso_incluido=True,
            uso={
                "tokens_total": 81,
            },
        )

    resposta = _provedor(handler).interpretar(_solicitacao())

    assert resposta.uso is not None
    assert resposta.uso.tokens_total == 81

    assert resposta.uso.tokens_entrada is None

    assert resposta.uso.tokens_saida is None

    assert resposta.uso.custo_estimado_usd is None


def test_provider_aceita_usage_null():
    def handler(
        request,
    ):
        return _response(
            uso_incluido=True,
            uso=None,
        )

    resposta = _provedor(handler).interpretar(_solicitacao())

    assert resposta.uso is None


@pytest.mark.parametrize(
    "uso",
    [
        "invalido",
        123,
        [],
        {
            "campo_desconhecido": 1,
        },
        {
            "tokens_total": -1,
        },
        {
            "tokens_total": True,
        },
        {
            "custo_estimado_usd": -0.1,
        },
    ],
)
def test_provider_rejeita_usage_invalido(
    uso,
):
    def handler(
        request,
    ):
        return _response(
            uso_incluido=True,
            uso=uso,
        )

    with pytest.raises(ContratoProvedorHttpInteligenciaAIInvalido):
        (_provedor(handler).interpretar(_solicitacao()))


def test_provider_continua_rejeitando_top_level_desconhecido():
    def handler(
        request,
    ):
        return _response(
            extras={
                "campo_extra": 123,
            },
        )

    with pytest.raises(ContratoProvedorHttpInteligenciaAIInvalido):
        (_provedor(handler).interpretar(_solicitacao()))


def test_usage_chega_a_telemetria_em_sucesso():
    def handler(
        request,
    ):
        return _response(
            uso_incluido=True,
            uso={
                "tokens_entrada": 90,
                "tokens_saida": 10,
                "tokens_total": 100,
                "custo_estimado_usd": 0.001,
            },
        )

    controle = ControleOperacionalInteligenciaAI()

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=_provedor(handler),
        validador=lambda sugestao: (sugestao.get("categoria_sugerida") == "gpu"),
        controle_operacional=controle,
    )

    assert resultado.status == "sugestao_ai_validada"

    obs = controle.snapshot().observabilidade

    assert obs.chamadas_com_tokens_conhecidos == 1

    assert obs.tokens_entrada_total == 90
    assert obs.tokens_saida_total == 10
    assert obs.tokens_total == 100

    assert obs.chamadas_com_custo_conhecido == 1

    assert obs.custo_estimado_usd_total == pytest.approx(0.001)


def test_usage_chega_a_telemetria_mesmo_com_baixa_confianca():
    def handler(
        request,
    ):
        return _response(
            confianca=0.20,
            uso_incluido=True,
            uso={
                "tokens_total": 50,
                "custo_estimado_usd": 0.0005,
            },
        )

    controle = ControleOperacionalInteligenciaAI()

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=_provedor(handler),
        validador=lambda sugestao: True,
        confianca_minima=0.70,
        controle_operacional=controle,
    )

    assert resultado.status == "confianca_insuficiente"

    obs = controle.snapshot().observabilidade

    assert obs.chamadas_com_tokens_conhecidos == 1

    assert obs.tokens_total == 50

    assert obs.chamadas_com_custo_conhecido == 1


def test_sem_usage_nao_inventa_tokens_ou_custo():
    def handler(
        request,
    ):
        return _response()

    controle = ControleOperacionalInteligenciaAI()

    interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=_provedor(handler),
        validador=lambda sugestao: True,
        controle_operacional=controle,
    )

    obs = controle.snapshot().observabilidade

    assert obs.chamadas_com_tokens_conhecidos == 0

    assert obs.chamadas_com_custo_conhecido == 0

    assert obs.tokens_total == 0

    assert obs.custo_estimado_usd_total == 0.0


def test_usage_invalido_faz_fail_open_e_conta_falha_provider():
    def handler(
        request,
    ):
        return _response(
            uso_incluido=True,
            uso={
                "tokens_total": -50,
            },
        )

    controle = ControleOperacionalInteligenciaAI(
        limite_falhas_consecutivas=1,
    )

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=_provedor(handler),
        validador=lambda sugestao: True,
        controle_operacional=controle,
    )

    assert resultado.status == "erro_provedor"
    assert resultado.fallback_usado is True

    snapshot = controle.snapshot()

    assert snapshot.circuit_breaker.estado == "aberto"

    assert snapshot.circuit_breaker.falhas_consecutivas == 1
