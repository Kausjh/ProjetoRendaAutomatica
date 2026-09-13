from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ItemOutboxNotificacaoPersonalizada:
    id: str
    match_id: str
    conta_id: str
    canonical_key: str
    canal: str
    status: str
    tentativas: int
    disponivel_em: str
    criado_em: str
    atualizado_em: str
    entregue_em: str | None
    ultimo_erro: str | None
