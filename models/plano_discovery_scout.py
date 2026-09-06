# 63.8738, -149.7525

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlanoDiscoveryScout:
    fonte: str
    id_externo: str
    marketplace: str | None

    estrategia: str
    termos_busca: tuple[str, ...] = ()

    utilizavel: bool = True
    motivo: str = ""
