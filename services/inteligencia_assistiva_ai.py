from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
    ResultadoInteligenciaAssistivaAI,
    SolicitacaoInteligenciaAI,
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
) -> ResultadoInteligenciaAssistivaAI:
    """Executa IA somente como camada interpretativa assistiva.

    A IA nunca possui autoridade para publicar, alterar budget ou
    substituir regras deterministicas. Qualquer falha retorna o
    fallback fornecido pelo chamador.
    """

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

    limite = _validar_confianca_minima(confianca_minima)

    fallback_normalizado = dict(fallback)

    if not habilitado:
        return _resultado_fallback(
            status="desabilitado",
            fallback=fallback_normalizado,
        )

    if provedor is None:
        return _resultado_fallback(
            status="sem_provedor",
            fallback=fallback_normalizado,
        )

    if validador is None:
        return _resultado_fallback(
            status="sem_validador_deterministico",
            fallback=fallback_normalizado,
        )

    try:
        resposta = provedor.interpretar(solicitacao)
    except Exception as erro:
        return _resultado_fallback(
            status="erro_provedor",
            fallback=fallback_normalizado,
            tipo_erro=type(erro).__name__,
        )

    if not isinstance(
        resposta,
        RespostaProvedorInteligenciaAI,
    ):
        return _resultado_fallback(
            status="resposta_provedor_invalida",
            fallback=fallback_normalizado,
        )

    confianca = float(resposta.confianca)

    if confianca < limite:
        return _resultado_fallback(
            status="confianca_insuficiente",
            fallback=fallback_normalizado,
            provedor=resposta.provedor,
            modelo=resposta.modelo,
            confianca=confianca,
        )

    sugestao = dict(resposta.conteudo)

    try:
        valida = validador(sugestao)
    except Exception as erro:
        return _resultado_fallback(
            status="erro_validacao_deterministica",
            fallback=fallback_normalizado,
            provedor=resposta.provedor,
            modelo=resposta.modelo,
            confianca=confianca,
            tipo_erro=type(erro).__name__,
        )

    if valida is not True:
        return _resultado_fallback(
            status="rejeitado_validacao_deterministica",
            fallback=fallback_normalizado,
            provedor=resposta.provedor,
            modelo=resposta.modelo,
            confianca=confianca,
        )

    return ResultadoInteligenciaAssistivaAI(
        status="sugestao_ai_validada",
        sugestao=sugestao,
        origem="ai",
        confianca=confianca,
        provedor=resposta.provedor,
        modelo=resposta.modelo,
        fallback_usado=False,
        validada_deterministicamente=True,
    )


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
