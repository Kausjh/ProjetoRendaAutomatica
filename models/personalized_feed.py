from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ItemFeedPersonalizado:
    canonical_key: str
    nome_canonico: str
    categoria: str | None
    marca: str | None
    modelo: str | None
    score_relevancia: int
    motivos: tuple[str, ...]
    em_watchlist: bool
    preco_alvo: Decimal | None
    preco_atual: Decimal | None
    marketplace: str | None
    identificador: str | None
    link: str | None
    atualizado_em: str


@dataclass(frozen=True, slots=True)
class PaginaFeedPersonalizado:
    total: int
    limite: int
    offset: int
    itens: tuple[ItemFeedPersonalizado, ...]
