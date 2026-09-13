from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EventoAlertaPersonalizavel:
    evento_id: str
    canonical_key: str
    tipo_evento: str
    preco_atual: Decimal
    ocorrido_em: str
    preco_anterior: Decimal | None = None
    marketplace: str | None = None


@dataclass(frozen=True, slots=True)
class CorrespondenciaAlertaPersonalizado:
    id: str
    evento_alerta_id: str
    watchlist_id: str
    conta_id: str
    canonical_key: str
    tipo_evento: str
    preco_atual: Decimal
    marketplace: str | None
    motivos: tuple[str, ...]
    criado_em: str
