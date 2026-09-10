# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class SinalDiscoveryComercialHunter:
    fonte_hunter: str
    marketplace: str
    direcao: str
    sinais_distintos: int
    limite_base: int
    limite_sugerido: int
    motivo: str

    @property
    def aumento(self) -> int:
        return max(
            self.limite_sugerido - self.limite_base,
            0,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoDiscoveryComercialHunter:
    limites_base: tuple[tuple[str, int], ...]
    limites_sugeridos: tuple[tuple[str, int], ...]
    sinais: tuple[SinalDiscoveryComercialHunter, ...]

    @property
    def houve_ajuste(
        self,
    ) -> bool:
        return bool(self.sinais)

    @property
    def fontes_impulsionadas(
        self,
    ) -> tuple[str, ...]:
        return tuple(sinal.fonte_hunter for sinal in self.sinais)

    def como_mapping(
        self,
    ) -> dict[str, int]:
        return dict(self.limites_sugeridos)
