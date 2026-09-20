from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EventoProgressoMissao:
    id: str
    conta_id: str
    missao_codigo: str
    regra_versao: str
    instancia_chave: str
    chave_idempotencia: str
    tipo_evento: str
    origem: str
    origem_id: str
    delta: int
    metadados: dict[str, Any]
    ocorrido_em: str
    criado_em: str


@dataclass(frozen=True, slots=True)
class ProgressoMissao:
    conta_id: str
    missao_codigo: str
    regra_versao: str
    instancia_chave: str
    progresso_total: int
    alvo_total: int
    concluida_em: str | None
    atualizado_em: str

    @property
    def concluida(self) -> bool:
        return self.concluida_em is not None


@dataclass(frozen=True, slots=True)
class ConcessaoRecompensaMissao:
    id: str
    conta_id: str
    missao_codigo: str
    regra_versao: str
    instancia_chave: str
    tipo_recompensa: str
    quantidade: int
    status: str
    referencia_concessao: str | None
    criado_em: str
    concedida_em: str | None


@dataclass(frozen=True, slots=True)
class ResultadoProgressoMissao:
    status: str
    evento: EventoProgressoMissao | None
    progresso: ProgressoMissao
    recompensa: ConcessaoRecompensaMissao | None
    concluida_agora: bool
    recompensa_criada: bool
