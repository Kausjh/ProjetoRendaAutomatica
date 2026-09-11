# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class AlvoDiscoveryComercialHunter:
    fonte_hunter: str
    marketplace: str
    estrategia: str
    termo_busca: str | None
    direcao: str
    sinais_distintos: int
    motivo: str
    evidencias: tuple[str, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoAlvosDiscoveryComercialHunter:
    alvos: tuple[AlvoDiscoveryComercialHunter, ...]

    @property
    def houve_alvos(
        self,
    ) -> bool:
        return bool(self.alvos)

    @property
    def fontes_hunter(
        self,
    ) -> tuple[str, ...]:
        return tuple(dict.fromkeys(alvo.fonte_hunter for alvo in self.alvos))
