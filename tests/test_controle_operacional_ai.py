from __future__ import annotations

import math

import pytest

from models.observabilidade_ai import (
    ESTADO_CIRCUITO_ABERTO,
    ESTADO_CIRCUITO_FECHADO,
    ESTADO_CIRCUITO_MEIO_ABERTO,
    EventoObservabilidadeInteligenciaAI,
    UsoInteligenciaAI,
)
from services.controle_operacional_ai import (
    CircuitBreakerInteligenciaAI,
    ControleOperacionalInteligenciaAI,
    ObservabilidadeInteligenciaAI,
)


class RelogioFake:
    def __init__(
        self,
        valor: float = 1000.0,
    ) -> None:
        self.valor = valor

    def agora(
        self,
    ) -> float:
        return self.valor

    def avancar(
        self,
        segundos: float,
    ) -> None:
        self.valor += segundos


def _evento(
    *,
    tarefa="desambiguar_categoria_produto",
    status="sugestao_ai_validada",
    duracao_ms=25.0,
    chamada_externa=True,
    fallback=False,
    validado=True,
    erro=False,
    bloqueado=False,
    uso=None,
):
    return EventoObservabilidadeInteligenciaAI(
        tarefa=tarefa,
        status=status,
        duracao_ms=duracao_ms,
        chamada_externa_realizada=(chamada_externa),
        fallback_usado=fallback,
        resultado_ai_validado=validado,
        erro=erro,
        bloqueada_circuit_breaker=bloqueado,
        provedor="fake",
        modelo="fake-v1",
        uso=uso,
    )


def test_uso_ai_aceita_campos_ausentes():
    uso = UsoInteligenciaAI()

    assert uso.tokens_entrada is None
    assert uso.tokens_saida is None
    assert uso.tokens_total is None
    assert uso.custo_estimado_usd is None


@pytest.mark.parametrize(
    "campo,valor",
    [
        (
            "tokens_entrada",
            -1,
        ),
        (
            "tokens_saida",
            -1,
        ),
        (
            "tokens_total",
            -1,
        ),
        (
            "tokens_total",
            True,
        ),
    ],
)
def test_uso_ai_rejeita_tokens_invalidos(
    campo,
    valor,
):
    kwargs = {campo: valor}

    with pytest.raises(
        (
            TypeError,
            ValueError,
        )
    ):
        UsoInteligenciaAI(**kwargs)


@pytest.mark.parametrize(
    "valor",
    [
        -0.01,
        math.inf,
        math.nan,
        True,
    ],
)
def test_uso_ai_rejeita_custo_invalido(
    valor,
):
    with pytest.raises(
        (
            TypeError,
            ValueError,
        )
    ):
        UsoInteligenciaAI(custo_estimado_usd=valor)


def test_evento_rejeita_contradicao_ai_validada_com_fallback():
    with pytest.raises(ValueError):
        EventoObservabilidadeInteligenciaAI(
            tarefa="teste",
            status="teste",
            duracao_ms=1.0,
            chamada_externa_realizada=True,
            fallback_usado=True,
            resultado_ai_validado=True,
            erro=False,
        )


def test_evento_bloqueado_nao_pode_marcar_chamada_externa():
    with pytest.raises(ValueError):
        EventoObservabilidadeInteligenciaAI(
            tarefa="teste",
            status="circuit_breaker_aberto",
            duracao_ms=0.1,
            chamada_externa_realizada=True,
            fallback_usado=True,
            resultado_ai_validado=False,
            erro=False,
            bloqueada_circuit_breaker=True,
        )


def test_observabilidade_acumula_metricas():
    observabilidade = ObservabilidadeInteligenciaAI()

    observabilidade.registrar(
        _evento(
            duracao_ms=20.0,
            uso=UsoInteligenciaAI(
                tokens_entrada=100,
                tokens_saida=25,
                tokens_total=125,
                custo_estimado_usd=0.002,
            ),
        )
    )

    observabilidade.registrar(
        _evento(
            tarefa=("interpretar_incerteza_editorial"),
            status="erro_provedor",
            duracao_ms=40.0,
            chamada_externa=True,
            fallback=True,
            validado=False,
            erro=True,
        )
    )

    observabilidade.registrar(
        _evento(
            tarefa=("interpretar_incerteza_editorial"),
            status="circuit_breaker_aberto",
            duracao_ms=0.0,
            chamada_externa=False,
            fallback=True,
            validado=False,
            erro=False,
            bloqueado=True,
        )
    )

    snapshot = observabilidade.snapshot()

    assert snapshot.eventos_total == 3
    assert snapshot.chamadas_externas_total == 2

    assert snapshot.resultados_ai_validados_total == 1

    assert snapshot.fallbacks_total == 2
    assert snapshot.erros_total == 1

    assert snapshot.bloqueios_circuit_breaker_total == 1

    assert snapshot.duracao_media_ms == 20.0
    assert snapshot.duracao_maxima_ms == 40.0

    assert snapshot.por_tarefa == {
        "desambiguar_categoria_produto": 1,
        "interpretar_incerteza_editorial": 2,
    }

    assert snapshot.por_status == {
        "sugestao_ai_validada": 1,
        "erro_provedor": 1,
        "circuit_breaker_aberto": 1,
    }

    assert snapshot.status_por_tarefa["interpretar_incerteza_editorial"]["erro_provedor"] == 1

    assert snapshot.chamadas_com_tokens_conhecidos == 1

    assert snapshot.tokens_entrada_total == 100
    assert snapshot.tokens_saida_total == 25
    assert snapshot.tokens_total == 125

    assert snapshot.chamadas_com_custo_conhecido == 1

    assert snapshot.custo_estimado_usd_total == pytest.approx(0.002)


def test_custo_desconhecido_nao_vira_zero_conhecido():
    observabilidade = ObservabilidadeInteligenciaAI()

    observabilidade.registrar(_evento(uso=None))

    snapshot = observabilidade.snapshot()

    assert snapshot.chamadas_com_custo_conhecido == 0

    assert snapshot.chamadas_com_tokens_conhecidos == 0

    assert snapshot.custo_estimado_usd_total == 0.0


def test_circuit_breaker_inicia_fechado():
    relogio = RelogioFake()

    breaker = CircuitBreakerInteligenciaAI(
        limite_falhas_consecutivas=2,
        cooldown_segundos=30.0,
        agora=relogio.agora,
    )

    decisao = breaker.avaliar_chamada()

    assert decisao.permitido is True

    assert decisao.estado == ESTADO_CIRCUITO_FECHADO

    assert decisao.motivo == "circuito_fechado"


def test_falhas_consecutivas_abrem_circuito():
    relogio = RelogioFake()

    breaker = CircuitBreakerInteligenciaAI(
        limite_falhas_consecutivas=2,
        cooldown_segundos=30.0,
        agora=relogio.agora,
    )

    breaker.registrar_falha()

    snapshot = breaker.snapshot()

    assert snapshot.estado == ESTADO_CIRCUITO_FECHADO

    assert snapshot.falhas_consecutivas == 1

    breaker.registrar_falha()

    snapshot = breaker.snapshot()

    assert snapshot.estado == ESTADO_CIRCUITO_ABERTO

    assert snapshot.falhas_consecutivas == 2

    assert snapshot.cooldown_restante_segundos == pytest.approx(30.0)


def test_circuito_aberto_bloqueia_chamada():
    relogio = RelogioFake()

    breaker = CircuitBreakerInteligenciaAI(
        limite_falhas_consecutivas=1,
        cooldown_segundos=30.0,
        agora=relogio.agora,
    )

    breaker.registrar_falha()

    decisao = breaker.avaliar_chamada()

    assert decisao.permitido is False

    assert decisao.estado == ESTADO_CIRCUITO_ABERTO

    assert decisao.motivo == "circuito_aberto_em_cooldown"


def test_cooldown_libera_uma_probe_meio_aberta():
    relogio = RelogioFake()

    breaker = CircuitBreakerInteligenciaAI(
        limite_falhas_consecutivas=1,
        cooldown_segundos=30.0,
        agora=relogio.agora,
    )

    breaker.registrar_falha()

    relogio.avancar(30.0)

    decisao = breaker.avaliar_chamada()

    assert decisao.permitido is True

    assert decisao.estado == ESTADO_CIRCUITO_MEIO_ABERTO

    assert decisao.motivo == "probe_meio_aberto"

    segunda = breaker.avaliar_chamada()

    assert segunda.permitido is False

    assert segunda.estado == ESTADO_CIRCUITO_MEIO_ABERTO

    assert segunda.motivo == "probe_meio_aberto_ja_em_andamento"


def test_sucesso_na_probe_fecha_circuito():
    relogio = RelogioFake()

    breaker = CircuitBreakerInteligenciaAI(
        limite_falhas_consecutivas=1,
        cooldown_segundos=10.0,
        agora=relogio.agora,
    )

    breaker.registrar_falha()

    relogio.avancar(10.0)

    assert breaker.avaliar_chamada().permitido is True

    breaker.registrar_sucesso()

    snapshot = breaker.snapshot()

    assert snapshot.estado == ESTADO_CIRCUITO_FECHADO

    assert snapshot.falhas_consecutivas == 0

    assert snapshot.tentativa_meio_aberto_em_andamento is False


def test_falha_na_probe_reabre_circuito():
    relogio = RelogioFake()

    breaker = CircuitBreakerInteligenciaAI(
        limite_falhas_consecutivas=1,
        cooldown_segundos=10.0,
        agora=relogio.agora,
    )

    breaker.registrar_falha()

    relogio.avancar(10.0)

    assert breaker.avaliar_chamada().permitido is True

    breaker.registrar_falha()

    snapshot = breaker.snapshot()

    assert snapshot.estado == ESTADO_CIRCUITO_ABERTO

    assert snapshot.cooldown_restante_segundos == pytest.approx(10.0)


def test_sucesso_reseta_falhas_consecutivas():
    relogio = RelogioFake()

    breaker = CircuitBreakerInteligenciaAI(
        limite_falhas_consecutivas=3,
        cooldown_segundos=10.0,
        agora=relogio.agora,
    )

    breaker.registrar_falha()
    breaker.registrar_falha()
    breaker.registrar_sucesso()

    snapshot = breaker.snapshot()

    assert snapshot.estado == ESTADO_CIRCUITO_FECHADO

    assert snapshot.falhas_consecutivas == 0


@pytest.mark.parametrize(
    "limite",
    [
        0,
        -1,
        True,
    ],
)
def test_limite_falhas_invalido_falha(
    limite,
):
    with pytest.raises(ValueError):
        CircuitBreakerInteligenciaAI(limite_falhas_consecutivas=limite)


@pytest.mark.parametrize(
    "cooldown",
    [
        0,
        -1,
        "abc",
    ],
)
def test_cooldown_invalido_falha(
    cooldown,
):
    with pytest.raises(ValueError):
        CircuitBreakerInteligenciaAI(cooldown_segundos=cooldown)


def test_controle_operacional_compoe_metricas_e_circuito():
    relogio = RelogioFake()

    controle = ControleOperacionalInteligenciaAI(
        limite_falhas_consecutivas=1,
        cooldown_segundos=15.0,
        agora=relogio.agora,
    )

    decisao = controle.avaliar_chamada_externa()

    assert decisao.permitido is True

    controle.registrar_falha_provedor()

    controle.registrar_evento(
        _evento(
            status="erro_provedor",
            chamada_externa=True,
            fallback=True,
            validado=False,
            erro=True,
        )
    )

    snapshot = controle.snapshot()

    assert snapshot.observabilidade.eventos_total == 1

    assert snapshot.observabilidade.erros_total == 1

    assert snapshot.circuit_breaker.estado == ESTADO_CIRCUITO_ABERTO


def test_foundation_nao_conhece_pipeline_publicador_ou_oferta():
    from pathlib import Path

    service = Path("services/controle_operacional_ai.py").read_text(encoding="utf-8-sig")

    model = Path("models/observabilidade_ai.py").read_text(encoding="utf-8-sig")

    texto = service + "\n" + model

    for proibido in (
        "ExecutorPipeline",
        "Publicador",
        "FilaPublicacao",
        "Oferta",
        "Telegram",
        "httpx",
    ):
        assert proibido not in texto
