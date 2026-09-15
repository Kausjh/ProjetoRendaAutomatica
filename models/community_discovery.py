from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DescobertaComunitaria:
    id: str
    conta_id: str
    url: str
    url_normalizada: str
    marketplace: str | None
    status: str
    tentativas: int
    disponivel_em: str
    processando_desde: str | None
    motivo_status: str | None
    canonical_key: str | None
    criado_em: str
    atualizado_em: str
