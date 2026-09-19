from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EventoGamificacao:
    id: str
    conta_id: str
    chave_idempotencia: str
    tipo_evento: str
    origem: str
    origem_id: str | None
    xp_delta: int
    reputacao_delta: int
    regra_versao: str
    metadados: dict[str, Any]
    ocorrido_em: str
    criado_em: str


@dataclass(frozen=True, slots=True)
class SaldoGamificacao:
    conta_id: str
    xp_total: int
    reputacao_total: int
    eventos_total: int
    atualizado_em: str | None


@dataclass(frozen=True, slots=True)
class PerfilGamificacao:
    conta_id: str
    xp_total: int
    reputacao_total: int
    nivel: int
    eventos_total: int
    atualizado_em: str | None


@dataclass(frozen=True, slots=True)
class ResultadoEventoGamificacao:
    evento: EventoGamificacao
    perfil: PerfilGamificacao
    criado: bool
