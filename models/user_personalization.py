from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PreferenciasUsuario:
    conta_id: str
    notificacoes_preco_habilitadas: bool
    marketplaces_preferidos: tuple[str, ...]
    atualizado_em: str


@dataclass(frozen=True, slots=True)
class ItemWatchlistUsuario:
    id: str
    conta_id: str
    canonical_key: str
    preco_alvo: Decimal | None
    notificar_queda_preco: bool
    criado_em: str
    atualizado_em: str
