# 63.8738, -149.7525

from __future__ import annotations

import random


class CadenciaPublicacao:
    """Calcula uma pausa editorial variável entre publicações.

    A variação evita rajadas mecânicas e dá espaço para cada oferta respirar.
    Ela não tenta fingir que há uma pessoa publicando; apenas distribui o
    fluxo de forma mais natural para o leitor.
    """

    def __init__(
        self,
        intervalo_minimo_segundos: float = 55.0,
        intervalo_maximo_segundos: float = 300.0,
        intervalo_modo_segundos: float = 130.0,
        chance_intervalo_curto: float = 0.12,
        intervalo_curto_minimo_segundos: float = 20.0,
        intervalo_curto_maximo_segundos: float = 50.0,
        urgente_minimo_segundos: float = 8.0,
        urgente_maximo_segundos: float = 25.0,
        gerador: random.Random | None = None,
    ) -> None:
        self.intervalo_minimo_segundos = intervalo_minimo_segundos
        self.intervalo_maximo_segundos = intervalo_maximo_segundos
        self.intervalo_modo_segundos = intervalo_modo_segundos
        self.chance_intervalo_curto = chance_intervalo_curto
        self.intervalo_curto_minimo_segundos = intervalo_curto_minimo_segundos
        self.intervalo_curto_maximo_segundos = intervalo_curto_maximo_segundos
        self.urgente_minimo_segundos = urgente_minimo_segundos
        self.urgente_maximo_segundos = urgente_maximo_segundos
        self.gerador = gerador or random.Random()

        self._validar()

    def proximo_intervalo(self, tipo_oportunidade: str = "normal") -> float:
        if tipo_oportunidade in {"possivel_preco_bugado", "anomalia_forte"}:
            return self.gerador.uniform(
                self.urgente_minimo_segundos,
                self.urgente_maximo_segundos,
            )

        if self.gerador.random() < self.chance_intervalo_curto:
            return self.gerador.uniform(
                self.intervalo_curto_minimo_segundos,
                self.intervalo_curto_maximo_segundos,
            )

        return self.gerador.triangular(
            self.intervalo_minimo_segundos,
            self.intervalo_maximo_segundos,
            self.intervalo_modo_segundos,
        )

    def _validar(self) -> None:
        if self.intervalo_minimo_segundos <= 0:
            raise ValueError("Intervalo mínimo precisa ser maior que zero.")

        if self.intervalo_maximo_segundos < self.intervalo_minimo_segundos:
            raise ValueError("Intervalo máximo não pode ser menor que o mínimo.")

        if not (
            self.intervalo_minimo_segundos
            <= self.intervalo_modo_segundos
            <= self.intervalo_maximo_segundos
        ):
            raise ValueError("Modo precisa ficar entre mínimo e máximo.")

        if not 0 <= self.chance_intervalo_curto <= 1:
            raise ValueError("Chance de intervalo curto precisa ficar entre 0 e 1.")
