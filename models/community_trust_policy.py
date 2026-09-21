from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DecisaoCommunityTrust:
    elegivel: bool
    classificacao: str | None
    impacto_unidades: int
    politica_versao: str
    chave_idempotencia: str | None
    motivo_politica: str
    metadados: dict[str, Any]
