# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EstadoTemporalSinalNode:
    codigo: str
    origem: str
    titulo: str

    primeira_observacao: str
    inicio_sequencia_atual: str | None
    ultima_observacao: str

    observado_agora: bool

    observacoes_consecutivas: int
    observacoes_totais: int
    ciclos_ausente_consecutivos: int

    deixou_de_ser_observado_em: str | None
    transicao_ultimo_ciclo: str

    evidencias_mais_recentes: dict[str, Any]

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "origem": self.origem,
            "titulo": self.titulo,
            "primeira_observacao": self.primeira_observacao,
            "inicio_sequencia_atual": (self.inicio_sequencia_atual),
            "ultima_observacao": self.ultima_observacao,
            "observado_agora": self.observado_agora,
            "observacoes_consecutivas": (self.observacoes_consecutivas),
            "observacoes_totais": self.observacoes_totais,
            "ciclos_ausente_consecutivos": (self.ciclos_ausente_consecutivos),
            "deixou_de_ser_observado_em": (self.deixou_de_ser_observado_em),
            "transicao_ultimo_ciclo": (self.transicao_ultimo_ciclo),
            "evidencias_mais_recentes": (self.evidencias_mais_recentes),
        }


@dataclass(frozen=True, slots=True)
class EstadoTemporalSinaisNode:
    versao_schema: int
    node_id: str | None
    referencia_temporal: str

    sinais: tuple[
        EstadoTemporalSinalNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": (self.referencia_temporal),
            "sinais": [sinal.para_dict() for sinal in self.sinais],
        }
