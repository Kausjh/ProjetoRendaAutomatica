from __future__ import annotations

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


class Provider:
    def __init__(
        self,
        *,
        uso=None,
    ):
        self.uso = uso
        self.chamadas = 0

    def interpretar(
        self,
        solicitacao,
    ):
        self.chamadas += 1
        return RespostaProvedorInteligenciaAI(
            conteudo={"ok": True},
            confianca=0.95,
            provedor="fake",
            modelo="fake-v1",
            uso=self.uso,
        )


def _solicitacao():
    return SolicitacaoInteligenciaAI(
        tarefa="teste_limites_operacionais",
        contexto={},
    )


def _executar(*, controle, provider):
    return interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={"ok": False},
        habilitado=True,
        provedor=provider,
        validador=lambda sugestao: True,
        controle_operacional=controle,
    )


def test_sem_limites_preserva_legado():
    controle = ControleOperacionalInteligenciaAI()
    snapshot = controle.snapshot()

    assert snapshot.limite_chamadas_externas is None
    assert snapshot.limite_tokens_total is None
    assert snapshot.limite_custo_estimado_usd is None
    assert snapshot.bloqueio_limite_ativo is False
    assert snapshot.motivo_bloqueio_limite is None


def test_limite_chamadas_e_exato():
    controle = ControleOperacionalInteligenciaAI(
        limite_chamadas_externas=1,
    )
    provider = Provider()

    primeiro = _executar(
        controle=controle,
        provider=provider,
    )
    segundo = _executar(
        controle=controle,
        provider=provider,
    )

    assert primeiro.status == "sugestao_ai_validada"
    assert segundo.status == "limite_operacional_bloqueado"
    assert segundo.fallback_usado is True
    assert provider.chamadas == 1

    snapshot = controle.snapshot()
    assert snapshot.chamadas_reservadas == 0
    assert snapshot.bloqueio_limite_ativo is True
    assert snapshot.motivo_bloqueio_limite == "limite_chamadas_externas_atingido"


def test_limite_tokens_bloqueia_apos_total_atingido():
    controle = ControleOperacionalInteligenciaAI(
        limite_tokens_total=100,
    )
    provider = Provider(
        uso=UsoInteligenciaAI(
            tokens_total=100,
        )
    )

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "sugestao_ai_validada"
    )

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "limite_operacional_bloqueado"
    )

    snapshot = controle.snapshot()
    assert provider.chamadas == 1
    assert snapshot.observabilidade.tokens_total == 100
    assert snapshot.observabilidade.chamadas_com_tokens_total_conhecido == 1
    assert snapshot.motivo_bloqueio_limite == "limite_tokens_total_atingido"


def test_tokens_parciais_nao_fingem_total_conhecido():
    controle = ControleOperacionalInteligenciaAI(
        limite_tokens_total=1000,
    )
    provider = Provider(
        uso=UsoInteligenciaAI(
            tokens_entrada=20,
            tokens_saida=10,
            tokens_total=None,
        )
    )

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "sugestao_ai_validada"
    )

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "limite_operacional_bloqueado"
    )

    obs = controle.snapshot().observabilidade
    assert provider.chamadas == 1
    assert obs.chamadas_com_tokens_conhecidos == 1
    assert obs.chamadas_com_tokens_total_conhecido == 0
    assert controle.snapshot().motivo_bloqueio_limite == "limite_tokens_total_indeterminavel"


def test_custo_desconhecido_fail_closed():
    controle = ControleOperacionalInteligenciaAI(
        limite_custo_estimado_usd=1.0,
    )
    provider = Provider(
        uso=UsoInteligenciaAI(
            tokens_total=50,
            custo_estimado_usd=None,
        )
    )

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "sugestao_ai_validada"
    )

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "limite_operacional_bloqueado"
    )

    assert provider.chamadas == 1
    assert controle.snapshot().motivo_bloqueio_limite == "limite_custo_usd_indeterminavel"


def test_limite_custo_bloqueia_apos_total_atingido():
    controle = ControleOperacionalInteligenciaAI(
        limite_custo_estimado_usd=0.01,
    )
    provider = Provider(
        uso=UsoInteligenciaAI(
            custo_estimado_usd=0.01,
        )
    )

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "sugestao_ai_validada"
    )

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "limite_operacional_bloqueado"
    )

    assert provider.chamadas == 1
    assert controle.snapshot().motivo_bloqueio_limite == "limite_custo_usd_atingido"


def test_limite_medido_impede_segunda_reserva_concorrente():
    controle = ControleOperacionalInteligenciaAI(
        limite_tokens_total=1000,
    )

    primeira = controle.avaliar_chamada_externa()
    segunda = controle.avaliar_chamada_externa()

    assert primeira.permitido is True
    assert segunda.permitido is False
    assert segunda.motivo == "limite_medicao_em_andamento"
    assert controle.snapshot().chamadas_reservadas == 1


def test_reserva_e_liberada_apos_evento_da_chamada():
    controle = ControleOperacionalInteligenciaAI(
        limite_tokens_total=1000,
    )
    provider = Provider(
        uso=UsoInteligenciaAI(
            tokens_total=10,
        )
    )

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "sugestao_ai_validada"
    )

    assert controle.snapshot().chamadas_reservadas == 0

    assert (
        _executar(
            controle=controle,
            provider=provider,
        ).status
        == "sugestao_ai_validada"
    )

    assert provider.chamadas == 2


def test_kill_switch_tem_precedencia():
    controle = ControleOperacionalInteligenciaAI(
        kill_switch_ativo=True,
        limite_chamadas_externas=1,
        limite_tokens_total=100,
        limite_custo_estimado_usd=0.01,
    )

    decisao = controle.avaliar_chamada_externa()

    assert decisao.permitido is False
    assert decisao.motivo == "kill_switch_ativo"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limite_chamadas_externas": 0},
        {"limite_chamadas_externas": -1},
        {"limite_chamadas_externas": True},
        {"limite_tokens_total": 0},
        {"limite_tokens_total": -1},
        {"limite_tokens_total": False},
        {"limite_custo_estimado_usd": 0.0},
        {"limite_custo_estimado_usd": -0.1},
        {"limite_custo_estimado_usd": float("nan")},
        {"limite_custo_estimado_usd": float("inf")},
        {"limite_custo_estimado_usd": True},
    ],
)
def test_limites_invalidos_rejeitados(kwargs):
    with pytest.raises((TypeError, ValueError)):
        ControleOperacionalInteligenciaAI(**kwargs)


def test_bloqueio_limite_nao_contamina_circuit_breaker():
    controle = ControleOperacionalInteligenciaAI(
        limite_chamadas_externas=1,
    )
    provider = Provider()

    _executar(
        controle=controle,
        provider=provider,
    )
    bloqueado = _executar(
        controle=controle,
        provider=provider,
    )

    assert bloqueado.status == "limite_operacional_bloqueado"

    obs = controle.snapshot().observabilidade
    assert obs.por_status["limite_operacional_bloqueado"] == 1
    assert obs.bloqueios_circuit_breaker_total == 0


# 63.8738, -149.7525
