from __future__ import annotations

import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

DEFAULT_REGISTER_LIMIT = 5
DEFAULT_REGISTER_WINDOW_SECONDS = 3600
DEFAULT_LOGIN_CLIENT_LIMIT = 20
DEFAULT_LOGIN_SUBJECT_LIMIT = 10
DEFAULT_LOGIN_WINDOW_SECONDS = 300
DEFAULT_MAX_BUCKETS = 4096


@dataclass(frozen=True, slots=True)
class DecisaoAbuseControl:
    permitido: bool
    retry_after_seconds: int = 0


class UserFacingAbuseControls:
    def __init__(
        self,
        *,
        register_limit: int = DEFAULT_REGISTER_LIMIT,
        register_window_seconds: int = DEFAULT_REGISTER_WINDOW_SECONDS,
        login_client_limit: int = DEFAULT_LOGIN_CLIENT_LIMIT,
        login_subject_limit: int = DEFAULT_LOGIN_SUBJECT_LIMIT,
        login_window_seconds: int = DEFAULT_LOGIN_WINDOW_SECONDS,
        max_buckets: int = DEFAULT_MAX_BUCKETS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.register_limit = self._positivo(
            "register_limit",
            register_limit,
        )
        self.register_window_seconds = self._positivo(
            "register_window_seconds",
            register_window_seconds,
        )
        self.login_client_limit = self._positivo(
            "login_client_limit",
            login_client_limit,
        )
        self.login_subject_limit = self._positivo(
            "login_subject_limit",
            login_subject_limit,
        )
        self.login_window_seconds = self._positivo(
            "login_window_seconds",
            login_window_seconds,
        )
        self.max_buckets = self._positivo(
            "max_buckets",
            max_buckets,
        )
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[
            tuple[str, str],
            deque[float],
        ] = {}

    @staticmethod
    def _positivo(nome: str, valor: int) -> int:
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise TypeError(f"{nome} precisa ser inteiro.")
        if valor <= 0:
            raise ValueError(f"{nome} precisa ser positivo.")
        return valor

    @staticmethod
    def _env_positivo(
        nome: str,
        default: int,
    ) -> int:
        bruto = os.getenv(nome)
        if bruto is None or not bruto.strip():
            return default

        try:
            valor = int(bruto)
        except ValueError as erro:
            raise ValueError(f"{nome} precisa ser inteiro positivo.") from erro

        if valor <= 0:
            raise ValueError(f"{nome} precisa ser inteiro positivo.")

        return valor

    @classmethod
    def from_env(cls) -> UserFacingAbuseControls:
        return cls(
            register_limit=cls._env_positivo(
                "API_USER_REGISTER_RATE_LIMIT",
                DEFAULT_REGISTER_LIMIT,
            ),
            register_window_seconds=cls._env_positivo(
                "API_USER_REGISTER_RATE_WINDOW_SECONDS",
                DEFAULT_REGISTER_WINDOW_SECONDS,
            ),
            login_client_limit=cls._env_positivo(
                "API_USER_LOGIN_RATE_LIMIT",
                DEFAULT_LOGIN_CLIENT_LIMIT,
            ),
            login_subject_limit=cls._env_positivo(
                "API_USER_LOGIN_SUBJECT_RATE_LIMIT",
                DEFAULT_LOGIN_SUBJECT_LIMIT,
            ),
            login_window_seconds=cls._env_positivo(
                "API_USER_LOGIN_RATE_WINDOW_SECONDS",
                DEFAULT_LOGIN_WINDOW_SECONDS,
            ),
        )

    @staticmethod
    def _normalizar_cliente(valor: str) -> str:
        normalizado = valor.strip().lower()
        return normalizado or "desconhecido"

    @staticmethod
    def _normalizar_subject(
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        normalizado = valor.strip().lower()
        if not normalizado or len(normalizado) > 320 or "@" not in normalizado:
            return None

        return normalizado

    @staticmethod
    def _podar(
        bucket: deque[float],
        *,
        agora: float,
        janela: int,
    ) -> None:
        corte = agora - janela
        while bucket and bucket[0] <= corte:
            bucket.popleft()

    def _limpar_expirados_globais(
        self,
        agora: float,
    ) -> None:
        vazios: list[tuple[str, str]] = []

        for chave, bucket in self._buckets.items():
            janela = (
                self.register_window_seconds
                if chave[0] == "register-client"
                else self.login_window_seconds
            )
            self._podar(
                bucket,
                agora=agora,
                janela=janela,
            )
            if not bucket:
                vazios.append(chave)

        for chave in vazios:
            self._buckets.pop(chave, None)

    def _bucket(
        self,
        chave: tuple[str, str],
        *,
        agora: float,
    ) -> deque[float] | None:
        existente = self._buckets.get(chave)
        if existente is not None:
            return existente

        if len(self._buckets) >= self.max_buckets:
            self._limpar_expirados_globais(agora)

        if len(self._buckets) >= self.max_buckets:
            return None

        novo: deque[float] = deque()
        self._buckets[chave] = novo
        return novo

    @staticmethod
    def _retry_after(
        bucket: deque[float],
        *,
        agora: float,
        janela: int,
    ) -> int:
        if not bucket:
            return 1

        restante = janela - (agora - bucket[0])
        return max(1, math.ceil(restante))

    def _avaliar(
        self,
        regras: list[
            tuple[
                tuple[str, str],
                int,
                int,
                bool,
            ]
        ],
    ) -> DecisaoAbuseControl:
        agora = float(self._clock())

        with self._lock:
            buckets: list[
                tuple[
                    deque[float],
                    int,
                    int,
                ]
            ] = []

            for (
                chave,
                limite,
                janela,
                opcional,
            ) in regras:
                bucket = self._bucket(
                    chave,
                    agora=agora,
                )

                if bucket is None:
                    if opcional:
                        continue
                    return DecisaoAbuseControl(
                        permitido=False,
                        retry_after_seconds=janela,
                    )

                self._podar(
                    bucket,
                    agora=agora,
                    janela=janela,
                )
                buckets.append(
                    (
                        bucket,
                        limite,
                        janela,
                    )
                )

            bloqueios = [
                self._retry_after(
                    bucket,
                    agora=agora,
                    janela=janela,
                )
                for bucket, limite, janela in buckets
                if len(bucket) >= limite
            ]

            if bloqueios:
                return DecisaoAbuseControl(
                    permitido=False,
                    retry_after_seconds=max(bloqueios),
                )

            for bucket, _, _ in buckets:
                bucket.append(agora)

            return DecisaoAbuseControl(
                permitido=True,
            )

    def avaliar_register(
        self,
        client_key: str,
    ) -> DecisaoAbuseControl:
        cliente = self._normalizar_cliente(client_key)

        return self._avaliar(
            [
                (
                    ("register-client", cliente),
                    self.register_limit,
                    self.register_window_seconds,
                    False,
                )
            ]
        )

    def avaliar_login(
        self,
        client_key: str,
        *,
        subject: str | None = None,
    ) -> DecisaoAbuseControl:
        cliente = self._normalizar_cliente(client_key)
        subject_normalizado = self._normalizar_subject(subject)

        regras: list[
            tuple[
                tuple[str, str],
                int,
                int,
                bool,
            ]
        ] = [
            (
                ("login-client", cliente),
                self.login_client_limit,
                self.login_window_seconds,
                False,
            )
        ]

        if subject_normalizado is not None:
            regras.append(
                (
                    ("login-subject", subject_normalizado),
                    self.login_subject_limit,
                    self.login_window_seconds,
                    True,
                )
            )

        return self._avaliar(regras)
