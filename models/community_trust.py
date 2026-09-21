from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenciaCommunityTrust:
    id: str
    conta_id: str
    chave_idempotencia: str
    tipo_evidencia: str
    classificacao: str
    origem: str
    origem_id: str
    motivo: str | None
    politica_versao: str | None
    metadados: dict[str, Any]
    ocorrido_em: str
    criado_em: str


@dataclass(frozen=True, slots=True)
class PerfilCommunityTrust:
    conta_id: str
    evidencias_total: int
    positivas_total: int
    negativas_total: int
    neutras_total: int
    atualizado_em: str | None


@dataclass(frozen=True, slots=True)
class ResultadoRegistroCommunityTrust:
    evidencia: EvidenciaCommunityTrust
    perfil: PerfilCommunityTrust
    criado: bool
