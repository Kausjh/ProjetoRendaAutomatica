from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable
from threading import Lock, RLock
from time import monotonic

from models.observabilidade_ai import (
    ESTADO_CIRCUITO_ABERTO,
    ESTADO_CIRCUITO_FECHADO,
    ESTADO_CIRCUITO_MEIO_ABERTO,
    DecisaoCircuitBreakerAI,
    EventoObservabilidadeInteligenciaAI,
    SnapshotCircuitBreakerAI,
    SnapshotControleOperacionalAI,
    SnapshotObservabilidadeInteligenciaAI,
)

LIMITE_FALHAS_CONSECUTIVAS_PADRAO = 3
COOLDOWN_CIRCUIT_BREAKER_SEGUNDOS_PADRAO = 60.0


class ObservabilidadeInteligenciaAI:
    def __init__(
        self,
    ) -> None:
        self._lock = Lock()

        self._eventos_total = 0
        self._chamadas_externas_total = 0
        self._resultados_ai_validados_total = 0
        self._fallbacks_total = 0
        self._erros_total = 0
        self._bloqueios_circuit_breaker_total = 0

        self._duracao_total_ms = 0.0
        self._duracao_maxima_ms = 0.0

        self._por_tarefa: dict[str, int] = defaultdict(int)

        self._por_status: dict[str, int] = defaultdict(int)

        self._status_por_tarefa: dict[
            str,
            dict[str, int],
        ] = defaultdict(lambda: defaultdict(int))

        self._chamadas_com_tokens_conhecidos = 0
        self._chamadas_com_tokens_total_conhecido = 0
        self._tokens_entrada_total = 0
        self._tokens_saida_total = 0
        self._tokens_total = 0

        self._chamadas_com_custo_conhecido = 0
        self._custo_estimado_usd_total = 0.0

    def registrar(
        self,
        evento: EventoObservabilidadeInteligenciaAI,
    ) -> None:
        if not isinstance(
            evento,
            EventoObservabilidadeInteligenciaAI,
        ):
            raise TypeError("evento precisa ser " "EventoObservabilidadeInteligenciaAI")

        with self._lock:
            self._eventos_total += 1

            self._por_tarefa[evento.tarefa] += 1

            self._por_status[evento.status] += 1

            self._status_por_tarefa[evento.tarefa][evento.status] += 1

            if evento.chamada_externa_realizada:
                self._chamadas_externas_total += 1

            if evento.resultado_ai_validado:
                self._resultados_ai_validados_total += 1

            if evento.fallback_usado:
                self._fallbacks_total += 1

            if evento.erro:
                self._erros_total += 1

            if evento.bloqueada_circuit_breaker:
                self._bloqueios_circuit_breaker_total += 1

            duracao_ms = float(evento.duracao_ms)

            self._duracao_total_ms += duracao_ms

            self._duracao_maxima_ms = max(
                self._duracao_maxima_ms,
                duracao_ms,
            )

            uso = evento.uso

            if uso is None:
                return

            possui_tokens = any(
                valor is not None
                for valor in (
                    uso.tokens_entrada,
                    uso.tokens_saida,
                    uso.tokens_total,
                )
            )

            if possui_tokens:
                self._chamadas_com_tokens_conhecidos += 1

            if uso.tokens_entrada is not None:
                self._tokens_entrada_total += uso.tokens_entrada

            if uso.tokens_saida is not None:
                self._tokens_saida_total += uso.tokens_saida

            if uso.tokens_total is not None:
                self._chamadas_com_tokens_total_conhecido += 1
                self._tokens_total += uso.tokens_total

            if uso.custo_estimado_usd is not None:
                self._chamadas_com_custo_conhecido += 1

                self._custo_estimado_usd_total += float(uso.custo_estimado_usd)

    def snapshot(
        self,
    ) -> SnapshotObservabilidadeInteligenciaAI:
        with self._lock:
            eventos_total = self._eventos_total

            duracao_media_ms = self._duracao_total_ms / eventos_total if eventos_total else 0.0

            status_por_tarefa = {
                tarefa: dict(status) for tarefa, status in (self._status_por_tarefa.items())
            }

            return SnapshotObservabilidadeInteligenciaAI(
                eventos_total=eventos_total,
                chamadas_externas_total=(self._chamadas_externas_total),
                resultados_ai_validados_total=(self._resultados_ai_validados_total),
                fallbacks_total=self._fallbacks_total,
                erros_total=self._erros_total,
                bloqueios_circuit_breaker_total=(self._bloqueios_circuit_breaker_total),
                duracao_media_ms=duracao_media_ms,
                duracao_maxima_ms=(self._duracao_maxima_ms),
                por_tarefa=dict(self._por_tarefa),
                por_status=dict(self._por_status),
                status_por_tarefa=status_por_tarefa,
                chamadas_com_tokens_conhecidos=(self._chamadas_com_tokens_conhecidos),
                tokens_entrada_total=(self._tokens_entrada_total),
                tokens_saida_total=(self._tokens_saida_total),
                tokens_total=(self._tokens_total),
                chamadas_com_custo_conhecido=(self._chamadas_com_custo_conhecido),
                custo_estimado_usd_total=(self._custo_estimado_usd_total),
                chamadas_com_tokens_total_conhecido=(self._chamadas_com_tokens_total_conhecido),
            )


class CircuitBreakerInteligenciaAI:
    def __init__(
        self,
        *,
        limite_falhas_consecutivas: int = (LIMITE_FALHAS_CONSECUTIVAS_PADRAO),
        cooldown_segundos: float = (COOLDOWN_CIRCUIT_BREAKER_SEGUNDOS_PADRAO),
        agora: Callable[
            [],
            float,
        ] = monotonic,
    ) -> None:
        if (
            not isinstance(
                limite_falhas_consecutivas,
                int,
            )
            or isinstance(
                limite_falhas_consecutivas,
                bool,
            )
            or limite_falhas_consecutivas <= 0
        ):
            raise ValueError("limite_falhas_consecutivas " "precisa ser inteiro positivo")

        try:
            cooldown = float(cooldown_segundos)
        except (
            TypeError,
            ValueError,
        ) as erro:
            raise ValueError("cooldown_segundos precisa ser numerico") from erro

        if cooldown <= 0.0:
            raise ValueError("cooldown_segundos precisa ser positivo")

        if not callable(agora):
            raise TypeError("agora precisa ser callable")

        self.limite_falhas_consecutivas = limite_falhas_consecutivas

        self.cooldown_segundos = cooldown
        self._agora = agora

        self._lock = Lock()

        self._estado = ESTADO_CIRCUITO_FECHADO
        self._falhas_consecutivas = 0
        self._aberto_ate = 0.0
        self._tentativa_meio_aberto_em_andamento = False

    def avaliar_chamada(
        self,
    ) -> DecisaoCircuitBreakerAI:
        with self._lock:
            agora = float(self._agora())

            if self._estado == ESTADO_CIRCUITO_FECHADO:
                return DecisaoCircuitBreakerAI(
                    permitido=True,
                    estado=self._estado,
                    motivo="circuito_fechado",
                )

            if self._estado == ESTADO_CIRCUITO_ABERTO:
                if agora < self._aberto_ate:
                    return DecisaoCircuitBreakerAI(
                        permitido=False,
                        estado=self._estado,
                        motivo=("circuito_aberto_em_cooldown"),
                    )

                self._estado = ESTADO_CIRCUITO_MEIO_ABERTO

                self._tentativa_meio_aberto_em_andamento = True

                return DecisaoCircuitBreakerAI(
                    permitido=True,
                    estado=self._estado,
                    motivo="probe_meio_aberto",
                )

            if self._estado == ESTADO_CIRCUITO_MEIO_ABERTO:
                if self._tentativa_meio_aberto_em_andamento:
                    return DecisaoCircuitBreakerAI(
                        permitido=False,
                        estado=self._estado,
                        motivo=("probe_meio_aberto_ja_em_andamento"),
                    )

                self._tentativa_meio_aberto_em_andamento = True

                return DecisaoCircuitBreakerAI(
                    permitido=True,
                    estado=self._estado,
                    motivo="probe_meio_aberto",
                )

            raise RuntimeError("estado interno do circuit breaker invalido")

    def registrar_sucesso(
        self,
    ) -> None:
        with self._lock:
            self._estado = ESTADO_CIRCUITO_FECHADO
            self._falhas_consecutivas = 0
            self._aberto_ate = 0.0
            self._tentativa_meio_aberto_em_andamento = False

    def registrar_falha(
        self,
    ) -> None:
        with self._lock:
            agora = float(self._agora())

            if self._estado == ESTADO_CIRCUITO_MEIO_ABERTO:
                self._falhas_consecutivas = max(
                    self._falhas_consecutivas,
                    self.limite_falhas_consecutivas,
                )

                self._abrir(agora=agora)

                return

            self._falhas_consecutivas += 1

            if self._estado == ESTADO_CIRCUITO_ABERTO:
                self._abrir(agora=agora)

                return

            if self._falhas_consecutivas >= self.limite_falhas_consecutivas:
                self._abrir(agora=agora)

    def snapshot(
        self,
    ) -> SnapshotCircuitBreakerAI:
        with self._lock:
            agora = float(self._agora())

            restante = 0.0

            if self._estado == ESTADO_CIRCUITO_ABERTO:
                restante = max(
                    0.0,
                    self._aberto_ate - agora,
                )

            return SnapshotCircuitBreakerAI(
                estado=self._estado,
                falhas_consecutivas=(self._falhas_consecutivas),
                limite_falhas_consecutivas=(self.limite_falhas_consecutivas),
                cooldown_segundos=(self.cooldown_segundos),
                cooldown_restante_segundos=restante,
                tentativa_meio_aberto_em_andamento=(self._tentativa_meio_aberto_em_andamento),
            )

    def _abrir(
        self,
        *,
        agora: float,
    ) -> None:
        self._estado = ESTADO_CIRCUITO_ABERTO

        self._aberto_ate = agora + self.cooldown_segundos

        self._tentativa_meio_aberto_em_andamento = False


class ControleOperacionalInteligenciaAI:
    def __init__(
        self,
        *,
        limite_falhas_consecutivas: int = LIMITE_FALHAS_CONSECUTIVAS_PADRAO,
        cooldown_segundos: float = COOLDOWN_CIRCUIT_BREAKER_SEGUNDOS_PADRAO,
        agora: Callable[[], float] = monotonic,
        kill_switch_ativo: bool = False,
        limite_chamadas_externas: int | None = None,
        limite_tokens_total: int | None = None,
        limite_custo_estimado_usd: float | None = None,
    ) -> None:
        if not isinstance(kill_switch_ativo, bool):
            raise TypeError("kill_switch_ativo precisa ser bool")

        self._validar_limite_inteiro(
            limite_chamadas_externas,
            campo="limite_chamadas_externas",
        )
        self._validar_limite_inteiro(
            limite_tokens_total,
            campo="limite_tokens_total",
        )
        self._validar_limite_custo(limite_custo_estimado_usd)

        self._lock = RLock()
        self._kill_switch_ativo = kill_switch_ativo
        self.limite_chamadas_externas = limite_chamadas_externas
        self.limite_tokens_total = limite_tokens_total
        self.limite_custo_estimado_usd = (
            float(limite_custo_estimado_usd) if limite_custo_estimado_usd is not None else None
        )
        self._chamadas_reservadas = 0

        self.observabilidade = ObservabilidadeInteligenciaAI()
        self.circuit_breaker = CircuitBreakerInteligenciaAI(
            limite_falhas_consecutivas=limite_falhas_consecutivas,
            cooldown_segundos=cooldown_segundos,
            agora=agora,
        )

    @staticmethod
    def _validar_limite_inteiro(
        valor: int | None,
        *,
        campo: str,
    ) -> None:
        if valor is None:
            return

        if isinstance(valor, bool) or not isinstance(valor, int):
            raise TypeError(f"{campo} precisa ser int positivo ou None")

        if valor <= 0:
            raise ValueError(f"{campo} precisa ser maior que zero")

    @staticmethod
    def _validar_limite_custo(
        valor: float | None,
    ) -> None:
        if valor is None:
            return

        if isinstance(valor, bool):
            raise TypeError("limite_custo_estimado_usd precisa ser numero positivo ou None")

        try:
            convertido = float(valor)
        except (TypeError, ValueError) as erro:
            raise TypeError(
                "limite_custo_estimado_usd precisa ser numero positivo ou None"
            ) from erro

        if not math.isfinite(convertido) or convertido <= 0.0:
            raise ValueError("limite_custo_estimado_usd precisa ser finito e maior que zero")

    @property
    def kill_switch_ativo(self) -> bool:
        with self._lock:
            return self._kill_switch_ativo

    def ativar_kill_switch(self) -> None:
        with self._lock:
            self._kill_switch_ativo = True

    def desativar_kill_switch(self) -> None:
        with self._lock:
            self._kill_switch_ativo = False

    def _motivo_bloqueio_limite(
        self,
        observabilidade: SnapshotObservabilidadeInteligenciaAI,
    ) -> str | None:
        chamadas_comprometidas = observabilidade.chamadas_externas_total + self._chamadas_reservadas

        if (
            self.limite_chamadas_externas is not None
            and chamadas_comprometidas >= self.limite_chamadas_externas
        ):
            return "limite_chamadas_externas_atingido"

        possui_limite_medido = (
            self.limite_tokens_total is not None or self.limite_custo_estimado_usd is not None
        )

        if possui_limite_medido and self._chamadas_reservadas > 0:
            return "limite_medicao_em_andamento"

        if self.limite_tokens_total is not None:
            if (
                observabilidade.chamadas_externas_total
                > observabilidade.chamadas_com_tokens_total_conhecido
            ):
                return "limite_tokens_total_indeterminavel"

            if observabilidade.tokens_total >= self.limite_tokens_total:
                return "limite_tokens_total_atingido"

        if self.limite_custo_estimado_usd is not None:
            if (
                observabilidade.chamadas_externas_total
                > observabilidade.chamadas_com_custo_conhecido
            ):
                return "limite_custo_usd_indeterminavel"

            if observabilidade.custo_estimado_usd_total >= self.limite_custo_estimado_usd:
                return "limite_custo_usd_atingido"

        return None

    def avaliar_chamada_externa(
        self,
    ) -> DecisaoCircuitBreakerAI:
        with self._lock:
            if self._kill_switch_ativo:
                snapshot_circuito = self.circuit_breaker.snapshot()
                return DecisaoCircuitBreakerAI(
                    permitido=False,
                    estado=snapshot_circuito.estado,
                    motivo="kill_switch_ativo",
                )

            observabilidade = self.observabilidade.snapshot()
            motivo_limite = self._motivo_bloqueio_limite(observabilidade)

            if motivo_limite is not None:
                snapshot_circuito = self.circuit_breaker.snapshot()
                return DecisaoCircuitBreakerAI(
                    permitido=False,
                    estado=snapshot_circuito.estado,
                    motivo=motivo_limite,
                )

            decisao = self.circuit_breaker.avaliar_chamada()

            if decisao.permitido:
                self._chamadas_reservadas += 1

            return decisao

    def registrar_sucesso_provedor(self) -> None:
        self.circuit_breaker.registrar_sucesso()

    def registrar_falha_provedor(self) -> None:
        self.circuit_breaker.registrar_falha()

    def registrar_evento(
        self,
        evento: EventoObservabilidadeInteligenciaAI,
    ) -> None:
        with self._lock:
            self.observabilidade.registrar(evento)

            if evento.chamada_externa_realizada and self._chamadas_reservadas > 0:
                self._chamadas_reservadas -= 1

    def snapshot(self) -> SnapshotControleOperacionalAI:
        with self._lock:
            observabilidade = self.observabilidade.snapshot()
            motivo_limite = self._motivo_bloqueio_limite(observabilidade)

            return SnapshotControleOperacionalAI(
                observabilidade=observabilidade,
                circuit_breaker=self.circuit_breaker.snapshot(),
                kill_switch_ativo=self._kill_switch_ativo,
                limite_chamadas_externas=self.limite_chamadas_externas,
                limite_tokens_total=self.limite_tokens_total,
                limite_custo_estimado_usd=self.limite_custo_estimado_usd,
                chamadas_reservadas=self._chamadas_reservadas,
                bloqueio_limite_ativo=motivo_limite is not None,
                motivo_bloqueio_limite=motivo_limite,
            )
