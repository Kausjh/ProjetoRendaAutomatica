from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real

ESTADO_CIRCUITO_FECHADO = "fechado"
ESTADO_CIRCUITO_ABERTO = "aberto"
ESTADO_CIRCUITO_MEIO_ABERTO = "meio_aberto"


def _validar_inteiro_nao_negativo_opcional(
    valor: int | None,
    *,
    campo: str,
) -> None:
    if valor is None:
        return

    if not isinstance(
        valor,
        int,
    ) or isinstance(
        valor,
        bool,
    ):
        raise TypeError(f"{campo} precisa ser inteiro ou None")

    if valor < 0:
        raise ValueError(f"{campo} nao pode ser negativo")


def _validar_numero_nao_negativo(
    valor: float,
    *,
    campo: str,
) -> float:
    if not isinstance(
        valor,
        Real,
    ) or isinstance(
        valor,
        bool,
    ):
        raise TypeError(f"{campo} precisa ser numerico")

    numero = float(valor)

    if not isfinite(numero) or numero < 0.0:
        raise ValueError(f"{campo} precisa ser finito e nao negativo")

    return numero


def _validar_numero_nao_negativo_opcional(
    valor: float | None,
    *,
    campo: str,
) -> None:
    if valor is None:
        return

    _validar_numero_nao_negativo(
        valor,
        campo=campo,
    )


@dataclass(
    frozen=True,
    slots=True,
)
class UsoInteligenciaAI:
    """Uso/custo conhecido de uma chamada.

    Todos os campos sao opcionais de proposito.
    Ausencia de informacao nunca deve ser convertida
    silenciosamente em consumo zero conhecido.
    """

    tokens_entrada: int | None = None
    tokens_saida: int | None = None
    tokens_total: int | None = None
    custo_estimado_usd: float | None = None

    def __post_init__(
        self,
    ) -> None:
        _validar_inteiro_nao_negativo_opcional(
            self.tokens_entrada,
            campo="tokens_entrada",
        )

        _validar_inteiro_nao_negativo_opcional(
            self.tokens_saida,
            campo="tokens_saida",
        )

        _validar_inteiro_nao_negativo_opcional(
            self.tokens_total,
            campo="tokens_total",
        )

        _validar_numero_nao_negativo_opcional(
            self.custo_estimado_usd,
            campo="custo_estimado_usd",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class EventoObservabilidadeInteligenciaAI:
    tarefa: str
    status: str
    duracao_ms: float

    chamada_externa_realizada: bool
    fallback_usado: bool
    resultado_ai_validado: bool
    erro: bool
    bloqueada_circuit_breaker: bool = False

    provedor: str | None = None
    modelo: str | None = None
    tipo_erro: str | None = None

    uso: UsoInteligenciaAI | None = None

    def __post_init__(
        self,
    ) -> None:
        tarefa = str(self.tarefa or "").strip()

        status = str(self.status or "").strip()

        if not tarefa:
            raise ValueError("tarefa precisa ser informada")

        if not status:
            raise ValueError("status precisa ser informado")

        _validar_numero_nao_negativo(
            self.duracao_ms,
            campo="duracao_ms",
        )

        for campo in (
            "chamada_externa_realizada",
            "fallback_usado",
            "resultado_ai_validado",
            "erro",
            "bloqueada_circuit_breaker",
        ):
            if not isinstance(
                getattr(
                    self,
                    campo,
                ),
                bool,
            ):
                raise TypeError(f"{campo} precisa ser bool")

        if self.resultado_ai_validado and self.fallback_usado:
            raise ValueError("resultado validado por AI nao pode usar fallback")

        if self.resultado_ai_validado and self.erro:
            raise ValueError("resultado validado por AI nao pode ser erro")

        if self.bloqueada_circuit_breaker and self.chamada_externa_realizada:
            raise ValueError(
                "chamada bloqueada pelo circuito nao pode " "ter chamada externa realizada"
            )

        if self.uso is not None and not isinstance(
            self.uso,
            UsoInteligenciaAI,
        ):
            raise TypeError("uso precisa ser UsoInteligenciaAI ou None")


@dataclass(
    frozen=True,
    slots=True,
)
class SnapshotObservabilidadeInteligenciaAI:
    eventos_total: int
    chamadas_externas_total: int
    resultados_ai_validados_total: int
    fallbacks_total: int
    erros_total: int
    bloqueios_circuit_breaker_total: int

    duracao_media_ms: float
    duracao_maxima_ms: float

    por_tarefa: dict[str, int]
    por_status: dict[str, int]
    status_por_tarefa: dict[str, dict[str, int]]

    chamadas_com_tokens_conhecidos: int
    tokens_entrada_total: int
    tokens_saida_total: int
    tokens_total: int

    chamadas_com_custo_conhecido: int
    custo_estimado_usd_total: float


@dataclass(
    frozen=True,
    slots=True,
)
class DecisaoCircuitBreakerAI:
    permitido: bool
    estado: str
    motivo: str


@dataclass(
    frozen=True,
    slots=True,
)
class SnapshotCircuitBreakerAI:
    estado: str
    falhas_consecutivas: int
    limite_falhas_consecutivas: int
    cooldown_segundos: float
    cooldown_restante_segundos: float
    tentativa_meio_aberto_em_andamento: bool


@dataclass(
    frozen=True,
    slots=True,
)
class SnapshotControleOperacionalAI:
    observabilidade: SnapshotObservabilidadeInteligenciaAI
    circuit_breaker: SnapshotCircuitBreakerAI
