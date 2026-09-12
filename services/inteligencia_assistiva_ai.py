from __future__ import annotations

from collections.abc import Callable, Mapping
from time import perf_counter
from typing import Any, Protocol, runtime_checkable

from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
    ResultadoInteligenciaAssistivaAI,
    SolicitacaoInteligenciaAI,
)
from models.observabilidade_ai import (
    EventoObservabilidadeInteligenciaAI,
)
from services.controle_operacional_ai import (
    ControleOperacionalInteligenciaAI,
)

CONFIANCA_MINIMA_PADRAO = 0.70


@runtime_checkable
class ProvedorInteligenciaAI(Protocol):
    def interpretar(
        self,
        solicitacao: SolicitacaoInteligenciaAI,
    ) -> RespostaProvedorInteligenciaAI: ...


ValidadorDeterministicoAI = Callable[
    [Mapping[str, Any]],
    bool,
]


def interpretar_com_inteligencia_assistiva(
    *,
    solicitacao: SolicitacaoInteligenciaAI,
    fallback: Mapping[str, Any],
    habilitado: bool = False,
    provedor: ProvedorInteligenciaAI | None = None,
    validador: ValidadorDeterministicoAI | None = None,
    confianca_minima: float = CONFIANCA_MINIMA_PADRAO,
    controle_operacional: ControleOperacionalInteligenciaAI | None = None,
) -> ResultadoInteligenciaAssistivaAI:
    """Executa IA somente como camada interpretativa assistiva.

    A IA nunca possui autoridade para publicar, alterar budget ou
    substituir regras deterministicas. Qualquer falha retorna o
    fallback fornecido pelo chamador.

    O controle operacional e opcional. Quando fornecido, ele registra
    observabilidade e protege chamadas externas com circuit breaker.
    Sua ausencia preserva integralmente o comportamento legado.
    """

    inicio = perf_counter()

    if not isinstance(
        solicitacao,
        SolicitacaoInteligenciaAI,
    ):
        raise TypeError("solicitacao deve ser SolicitacaoInteligenciaAI")

    if not isinstance(
        fallback,
        Mapping,
    ):
        raise TypeError("fallback precisa ser um Mapping")

    if controle_operacional is not None and not isinstance(
        controle_operacional,
        ControleOperacionalInteligenciaAI,
    ):
        raise TypeError(
            "controle_operacional precisa ser " "ControleOperacionalInteligenciaAI ou None"
        )

    limite = _validar_confianca_minima(confianca_minima)

    fallback_normalizado = dict(fallback)

    if not habilitado:
        return _finalizar(
            resultado=_resultado_fallback(
                status="desabilitado",
                fallback=fallback_normalizado,
            ),
            solicitacao=solicitacao,
            controle_operacional=controle_operacional,
            inicio=inicio,
            chamada_externa_realizada=False,
            erro=False,
            bloqueada_circuit_breaker=False,
        )

    if provedor is None:
        return _finalizar(
            resultado=_resultado_fallback(
                status="sem_provedor",
                fallback=fallback_normalizado,
            ),
            solicitacao=solicitacao,
            controle_operacional=controle_operacional,
            inicio=inicio,
            chamada_externa_realizada=False,
            erro=False,
            bloqueada_circuit_breaker=False,
        )

    if validador is None:
        return _finalizar(
            resultado=_resultado_fallback(
                status="sem_validador_deterministico",
                fallback=fallback_normalizado,
            ),
            solicitacao=solicitacao,
            controle_operacional=controle_operacional,
            inicio=inicio,
            chamada_externa_realizada=False,
            erro=False,
            bloqueada_circuit_breaker=False,
        )

    if controle_operacional is not None:
        try:
            decisao = controle_operacional.avaliar_chamada_externa()
        except Exception as erro:
            return _finalizar(
                resultado=_resultado_fallback(
                    status="erro_controle_operacional",
                    fallback=fallback_normalizado,
                    tipo_erro=type(erro).__name__,
                ),
                solicitacao=solicitacao,
                controle_operacional=controle_operacional,
                inicio=inicio,
                chamada_externa_realizada=False,
                erro=True,
                bloqueada_circuit_breaker=False,
            )

        if not decisao.permitido:
            return _finalizar(
                resultado=_resultado_fallback(
                    status=(
                        "kill_switch_bloqueado"
                        if decisao.motivo == "kill_switch_ativo"
                        else "circuit_breaker_bloqueado"
                    ),
                    fallback=fallback_normalizado,
                ),
                solicitacao=solicitacao,
                controle_operacional=controle_operacional,
                inicio=inicio,
                chamada_externa_realizada=False,
                erro=False,
                bloqueada_circuit_breaker=(decisao.motivo != "kill_switch_ativo"),
            )

    try:
        resposta = provedor.interpretar(solicitacao)
    except Exception as erro:
        _registrar_falha_provedor(controle_operacional)

        return _finalizar(
            resultado=_resultado_fallback(
                status="erro_provedor",
                fallback=fallback_normalizado,
                tipo_erro=type(erro).__name__,
            ),
            solicitacao=solicitacao,
            controle_operacional=controle_operacional,
            inicio=inicio,
            chamada_externa_realizada=True,
            erro=True,
            bloqueada_circuit_breaker=False,
        )

    if not isinstance(
        resposta,
        RespostaProvedorInteligenciaAI,
    ):
        _registrar_falha_provedor(controle_operacional)

        return _finalizar(
            resultado=_resultado_fallback(
                status="resposta_provedor_invalida",
                fallback=fallback_normalizado,
            ),
            solicitacao=solicitacao,
            controle_operacional=controle_operacional,
            inicio=inicio,
            chamada_externa_realizada=True,
            erro=True,
            bloqueada_circuit_breaker=False,
        )

    _registrar_sucesso_provedor(controle_operacional)

    confianca = float(resposta.confianca)

    if confianca < limite:
        return _finalizar(
            resultado=_resultado_fallback(
                status="confianca_insuficiente",
                fallback=fallback_normalizado,
                provedor=resposta.provedor,
                modelo=resposta.modelo,
                confianca=confianca,
            ),
            solicitacao=solicitacao,
            controle_operacional=controle_operacional,
            inicio=inicio,
            chamada_externa_realizada=True,
            erro=False,
            bloqueada_circuit_breaker=False,
            uso=resposta.uso,
        )

    sugestao = dict(resposta.conteudo)

    try:
        valida = validador(sugestao)
    except Exception as erro:
        return _finalizar(
            resultado=_resultado_fallback(
                status="erro_validacao_deterministica",
                fallback=fallback_normalizado,
                provedor=resposta.provedor,
                modelo=resposta.modelo,
                confianca=confianca,
                tipo_erro=type(erro).__name__,
            ),
            solicitacao=solicitacao,
            controle_operacional=controle_operacional,
            inicio=inicio,
            chamada_externa_realizada=True,
            erro=True,
            bloqueada_circuit_breaker=False,
            uso=resposta.uso,
        )

    if valida is not True:
        return _finalizar(
            resultado=_resultado_fallback(
                status="rejeitado_validacao_deterministica",
                fallback=fallback_normalizado,
                provedor=resposta.provedor,
                modelo=resposta.modelo,
                confianca=confianca,
            ),
            solicitacao=solicitacao,
            controle_operacional=controle_operacional,
            inicio=inicio,
            chamada_externa_realizada=True,
            erro=False,
            bloqueada_circuit_breaker=False,
            uso=resposta.uso,
        )

    return _finalizar(
        resultado=ResultadoInteligenciaAssistivaAI(
            status="sugestao_ai_validada",
            sugestao=sugestao,
            origem="ai",
            confianca=confianca,
            provedor=resposta.provedor,
            modelo=resposta.modelo,
            fallback_usado=False,
            validada_deterministicamente=True,
        ),
        solicitacao=solicitacao,
        controle_operacional=controle_operacional,
        inicio=inicio,
        chamada_externa_realizada=True,
        erro=False,
        bloqueada_circuit_breaker=False,
        uso=resposta.uso,
    )


def _finalizar(
    *,
    resultado: ResultadoInteligenciaAssistivaAI,
    solicitacao: SolicitacaoInteligenciaAI,
    controle_operacional: ControleOperacionalInteligenciaAI | None,
    inicio: float,
    chamada_externa_realizada: bool,
    erro: bool,
    bloqueada_circuit_breaker: bool,
    uso: Any = None,
) -> ResultadoInteligenciaAssistivaAI:
    if controle_operacional is None:
        return resultado

    duracao_ms = max(
        0.0,
        (perf_counter() - inicio) * 1000.0,
    )

    evento = EventoObservabilidadeInteligenciaAI(
        tarefa=solicitacao.tarefa,
        status=resultado.status,
        duracao_ms=duracao_ms,
        chamada_externa_realizada=(chamada_externa_realizada),
        fallback_usado=resultado.fallback_usado,
        resultado_ai_validado=(
            resultado.status == "sugestao_ai_validada" and resultado.fallback_usado is False
        ),
        erro=erro,
        bloqueada_circuit_breaker=(bloqueada_circuit_breaker),
        provedor=resultado.provedor,
        modelo=resultado.modelo,
        tipo_erro=resultado.tipo_erro,
        uso=uso,
    )

    try:
        controle_operacional.registrar_evento(evento)
    except Exception:
        # Observabilidade nunca pode quebrar o fluxo deterministico.
        pass

    return resultado


def _registrar_sucesso_provedor(
    controle_operacional: ControleOperacionalInteligenciaAI | None,
) -> None:
    if controle_operacional is None:
        return

    try:
        controle_operacional.registrar_sucesso_provedor()
    except Exception:
        # Falha da camada de controle nao ganha autoridade operacional.
        pass


def _registrar_falha_provedor(
    controle_operacional: ControleOperacionalInteligenciaAI | None,
) -> None:
    if controle_operacional is None:
        return

    try:
        controle_operacional.registrar_falha_provedor()
    except Exception:
        # O pipeline deterministico deve continuar disponivel.
        pass


def _validar_confianca_minima(
    valor: float,
) -> float:
    try:
        limite = float(valor)
    except (
        TypeError,
        ValueError,
    ) as erro:
        raise ValueError("confianca_minima deve ser numerica") from erro

    if not 0.0 <= limite <= 1.0:
        raise ValueError("confianca_minima precisa ficar entre 0 e 1")

    return limite


def _resultado_fallback(
    *,
    status: str,
    fallback: Mapping[str, Any],
    provedor: str | None = None,
    modelo: str | None = None,
    confianca: float | None = None,
    tipo_erro: str | None = None,
) -> ResultadoInteligenciaAssistivaAI:
    return ResultadoInteligenciaAssistivaAI(
        status=status,
        sugestao=dict(fallback),
        origem="fallback_deterministico",
        confianca=confianca,
        provedor=provedor,
        modelo=modelo,
        fallback_usado=True,
        validada_deterministicamente=False,
        tipo_erro=tipo_erro,
    )
