from __future__ import annotations

from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
    SolicitacaoInteligenciaAI,
)
from services.controle_operacional_ai import (
    ControleOperacionalInteligenciaAI,
)
from services.inteligencia_assistiva_ai import (
    interpretar_com_inteligencia_assistiva,
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


class ProvedorFake:
    def __init__(
        self,
        *,
        resposta=None,
        erro=None,
    ) -> None:
        self.resposta = resposta
        self.erro = erro
        self.chamadas = 0

    def interpretar(
        self,
        solicitacao,
    ):
        self.chamadas += 1

        if self.erro is not None:
            raise self.erro

        return self.resposta


def _solicitacao():
    return SolicitacaoInteligenciaAI(
        tarefa="teste_v19e2",
        contexto={
            "titulo": "Produto de teste",
        },
    )


def _fallback():
    return {
        "categoria_sugerida": "outros",
    }


def _resposta(
    *,
    confianca=0.95,
):
    return RespostaProvedorInteligenciaAI(
        conteudo={
            "categoria_sugerida": "gpu",
        },
        confianca=confianca,
        provedor="fake",
        modelo="fake-v1",
    )


def _validar_gpu(
    sugestao,
):
    return sugestao.get("categoria_sugerida") == "gpu"


def _controle(
    *,
    limite=3,
    cooldown=30.0,
    relogio=None,
):
    kwargs = {
        "limite_falhas_consecutivas": limite,
        "cooldown_segundos": cooldown,
    }

    if relogio is not None:
        kwargs["agora"] = relogio.agora

    return ControleOperacionalInteligenciaAI(**kwargs)


def test_sem_controle_preserva_comportamento_legado():
    provedor = ProvedorFake(resposta=_resposta())

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
    )

    assert provedor.chamadas == 1

    assert resultado.status == "sugestao_ai_validada"

    assert resultado.fallback_usado is False


def test_desabilitado_registra_evento_sem_chamada_externa():
    provedor = ProvedorFake(resposta=_resposta())

    controle = _controle()

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=False,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    assert resultado.status == "desabilitado"
    assert provedor.chamadas == 0

    snapshot = controle.snapshot()

    assert snapshot.observabilidade.eventos_total == 1

    assert snapshot.observabilidade.chamadas_externas_total == 0

    assert snapshot.observabilidade.fallbacks_total == 1

    assert snapshot.circuit_breaker.estado == "fechado"
    assert snapshot.circuit_breaker.falhas_consecutivas == 0


def test_sucesso_provedor_registra_telemetria():
    provedor = ProvedorFake(resposta=_resposta())

    controle = _controle()

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    assert resultado.status == "sugestao_ai_validada"

    snapshot = controle.snapshot()

    obs = snapshot.observabilidade

    assert obs.eventos_total == 1
    assert obs.chamadas_externas_total == 1

    assert obs.resultados_ai_validados_total == 1

    assert obs.fallbacks_total == 0
    assert obs.erros_total == 0

    assert obs.por_tarefa["teste_v19e2"] == 1

    assert obs.por_status["sugestao_ai_validada"] == 1

    assert obs.duracao_maxima_ms >= 0.0

    assert snapshot.circuit_breaker.estado == "fechado"
    assert snapshot.circuit_breaker.falhas_consecutivas == 0


def test_erros_provider_abrem_circuito_e_terceira_chamada_e_bloqueada():
    provedor = ProvedorFake(erro=RuntimeError("provider indisponivel"))

    controle = _controle(
        limite=2,
        cooldown=30.0,
    )

    primeiro = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    segundo = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    terceiro = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    assert primeiro.status == "erro_provedor"
    assert segundo.status == "erro_provedor"

    assert terceiro.status == "circuit_breaker_bloqueado"

    assert provedor.chamadas == 2

    snapshot = controle.snapshot()

    assert snapshot.circuit_breaker.estado == "aberto"

    assert snapshot.circuit_breaker.falhas_consecutivas == 2

    obs = snapshot.observabilidade

    assert obs.eventos_total == 3
    assert obs.chamadas_externas_total == 2
    assert obs.erros_total == 2

    assert obs.bloqueios_circuit_breaker_total == 1


def test_resposta_de_tipo_invalido_conta_como_falha_provider():
    provedor = ProvedorFake(
        resposta={
            "categoria_sugerida": "gpu",
        }
    )

    controle = _controle(limite=1)

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    assert resultado.status == "resposta_provedor_invalida"

    snapshot = controle.snapshot()

    assert snapshot.circuit_breaker.estado == "aberto"

    assert snapshot.circuit_breaker.falhas_consecutivas == 1

    assert snapshot.observabilidade.erros_total == 1


def test_baixa_confianca_nao_abre_circuito():
    provedor = ProvedorFake(resposta=_resposta(confianca=0.20))

    controle = _controle(limite=1)

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        confianca_minima=0.70,
        controle_operacional=controle,
    )

    assert resultado.status == "confianca_insuficiente"

    snapshot = controle.snapshot()

    assert snapshot.circuit_breaker.estado == "fechado"
    assert snapshot.circuit_breaker.falhas_consecutivas == 0

    assert snapshot.observabilidade.chamadas_externas_total == 1

    assert snapshot.observabilidade.erros_total == 0


def test_rejeicao_validador_nao_abre_circuito():
    provedor = ProvedorFake(resposta=_resposta())

    controle = _controle(limite=1)

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=lambda sugestao: False,
        controle_operacional=controle,
    )

    assert resultado.status == "rejeitado_validacao_deterministica"

    snapshot = controle.snapshot()

    assert snapshot.circuit_breaker.estado == "fechado"
    assert snapshot.circuit_breaker.falhas_consecutivas == 0

    assert snapshot.observabilidade.erros_total == 0


def test_erro_validador_nao_abre_circuito():
    provedor = ProvedorFake(resposta=_resposta())

    controle = _controle(limite=1)

    def validador_com_erro(
        sugestao,
    ):
        raise ValueError("erro local")

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=validador_com_erro,
        controle_operacional=controle,
    )

    assert resultado.status == "erro_validacao_deterministica"

    snapshot = controle.snapshot()

    assert snapshot.circuit_breaker.estado == "fechado"
    assert snapshot.circuit_breaker.falhas_consecutivas == 0

    assert snapshot.observabilidade.erros_total == 1


def test_sem_provider_nao_abre_circuito():
    controle = _controle(limite=1)

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=None,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    assert resultado.status == "sem_provedor"

    snapshot = controle.snapshot()

    assert snapshot.circuit_breaker.estado == "fechado"
    assert snapshot.circuit_breaker.falhas_consecutivas == 0

    assert snapshot.observabilidade.chamadas_externas_total == 0


def test_half_open_probe_com_sucesso_fecha_circuito():
    relogio = RelogioFake()

    provedor = ProvedorFake(erro=RuntimeError("falha inicial"))

    controle = _controle(
        limite=1,
        cooldown=10.0,
        relogio=relogio,
    )

    primeiro = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    assert primeiro.status == "erro_provedor"

    assert controle.snapshot().circuit_breaker.estado == "aberto"

    bloqueada = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    assert bloqueada.status == "circuit_breaker_bloqueado"

    assert provedor.chamadas == 1

    relogio.avancar(10.0)

    provedor.erro = None
    provedor.resposta = _resposta()

    probe = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    assert probe.status == "sugestao_ai_validada"

    snapshot = controle.snapshot()

    assert snapshot.circuit_breaker.estado == "fechado"
    assert snapshot.circuit_breaker.falhas_consecutivas == 0

    assert provedor.chamadas == 2


def test_controle_nao_inventa_tokens_ou_custo():
    provedor = ProvedorFake(resposta=_resposta())

    controle = _controle()

    interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=_fallback(),
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
        controle_operacional=controle,
    )

    obs = controle.snapshot().observabilidade

    assert obs.chamadas_com_tokens_conhecidos == 0

    assert obs.chamadas_com_custo_conhecido == 0

    assert obs.tokens_total == 0

    assert obs.custo_estimado_usd_total == 0.0
