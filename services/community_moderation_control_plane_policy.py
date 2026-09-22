from __future__ import annotations

import re
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from math import ceil
from threading import Lock
from time import monotonic
from uuid import uuid4

AuditSink = Callable[..., bool | None]


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoRateLimitModeration:
    permitido: bool
    limite: int
    restantes: int
    retry_after_segundos: int | None


class CommunityModerationControlPlanePolicy:
    READ_SCOPE = "read"
    DECISION_SCOPE = "decision"

    DEFAULT_READ_LIMIT = 120
    DEFAULT_DECISION_LIMIT = 30
    DEFAULT_WINDOW_SECONDS = 60.0

    _REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")

    ERROR_CODES = {
        400: "moderation_bad_request",
        401: "moderation_unauthorized",
        404: "moderation_not_found",
        409: "moderation_conflict",
        429: "moderation_rate_limited",
        500: "moderation_internal_error",
        503: "moderation_unavailable",
    }

    def __init__(
        self,
        *,
        read_limit: int = DEFAULT_READ_LIMIT,
        decision_limit: int = DEFAULT_DECISION_LIMIT,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        clock: Callable[[], float] | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.read_limit = self._positive_int(
            read_limit,
            "read_limit",
        )

        self.decision_limit = self._positive_int(
            decision_limit,
            "decision_limit",
        )

        self.window_seconds = float(window_seconds)

        if self.window_seconds <= 0:
            raise ValueError("window_seconds precisa ser positivo.")

        self._clock = clock if clock is not None else monotonic

        self._audit_sink = audit_sink

        self._buckets: dict[
            str,
            deque[float],
        ] = defaultdict(deque)

        self._lock = Lock()

    @staticmethod
    def _positive_int(
        value: object,
        field: str,
    ) -> int:
        try:
            parsed = int(value)
        except (
            TypeError,
            ValueError,
        ) as erro:
            raise ValueError(f"{field} precisa ser inteiro.") from erro

        if parsed < 1:
            raise ValueError(f"{field} precisa ser positivo.")

        return parsed

    def normalizar_request_id(
        self,
        value: object | None,
    ) -> str:
        supplied = str(value if value is not None else "").strip()

        if supplied and self._REQUEST_ID_PATTERN.fullmatch(supplied):
            return supplied

        return uuid4().hex

    def consumir_rate_limit(
        self,
        *,
        escopo: str,
        chave: object,
    ) -> ResultadoRateLimitModeration:
        scope = str(escopo).strip().casefold()

        if scope == self.READ_SCOPE:
            limite = self.read_limit

        elif scope == self.DECISION_SCOPE:
            limite = self.decision_limit

        else:
            raise ValueError("escopo de rate limit invalido.")

        client_key = str(chave if chave is not None else "").strip() or "unknown"

        bucket_key = f"{scope}:{client_key}"

        now = float(self._clock())

        cutoff = now - self.window_seconds

        with self._lock:
            bucket = self._buckets[bucket_key]

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= limite:
                oldest = bucket[0]

                retry_after = max(
                    1,
                    int(ceil(self.window_seconds - (now - oldest))),
                )

                return ResultadoRateLimitModeration(
                    permitido=False,
                    limite=limite,
                    restantes=0,
                    retry_after_segundos=(retry_after),
                )

            bucket.append(now)

            restantes = max(
                0,
                limite - len(bucket),
            )

            return ResultadoRateLimitModeration(
                permitido=True,
                limite=limite,
                restantes=restantes,
                retry_after_segundos=None,
            )

    @classmethod
    def codigo_erro(
        cls,
        status: int,
    ) -> str | None:
        return cls.ERROR_CODES.get(int(status))

    @staticmethod
    def resultado_auditoria(
        status: int,
    ) -> str:
        status = int(status)

        if 200 <= status < 300:
            return "sucesso"

        if status == 401:
            return "negado_auth"

        if status == 409:
            return "conflito"

        if status == 429:
            return "rate_limited"

        if status == 503:
            return "indisponivel"

        if 400 <= status < 500:
            return "erro_cliente"

        if status >= 500:
            return "erro_interno"

        return "outro"

    def auditar(
        self,
        *,
        acao: str,
        alvo: str | None,
        detalhes: dict[str, object],
        dispositivo: str | None,
        resultado: str,
    ) -> bool:
        sink = self._audit_sink

        if sink is None:
            return False

        try:
            persisted = sink(
                acao=acao,
                alvo=alvo,
                detalhes=detalhes,
                dispositivo=dispositivo,
                resultado=resultado,
            )
        except Exception:
            return False

        return persisted is not False
