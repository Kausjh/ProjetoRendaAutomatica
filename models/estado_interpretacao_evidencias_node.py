# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EstadoObservacaoInterpretacaoNode:
    codigo: str
    categoria: str
    sujeito: str
    descricao: str

    primeira_observacao: str
    inicio_sequencia_atual: str
    ultima_observacao: str

    observado_agora: bool

    observacoes_consecutivas: int
    observacoes_totais: int

    ciclos_ausente_consecutivos: int
    deixou_de_ser_observado_em: str | None

    transicao_ultimo_ciclo: str

    dados_mais_recentes: dict[str, Any]
    fontes_mais_recentes: tuple[str, ...]

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "categoria": self.categoria,
            "sujeito": self.sujeito,
            "descricao": self.descricao,
            "primeira_observacao": self.primeira_observacao,
            "inicio_sequencia_atual": (self.inicio_sequencia_atual),
            "ultima_observacao": self.ultima_observacao,
            "observado_agora": self.observado_agora,
            "observacoes_consecutivas": (self.observacoes_consecutivas),
            "observacoes_totais": self.observacoes_totais,
            "ciclos_ausente_consecutivos": (self.ciclos_ausente_consecutivos),
            "deixou_de_ser_observado_em": (self.deixou_de_ser_observado_em),
            "transicao_ultimo_ciclo": (self.transicao_ultimo_ciclo),
            "dados_mais_recentes": self.dados_mais_recentes,
            "fontes_mais_recentes": list(self.fontes_mais_recentes),
        }


@dataclass(frozen=True, slots=True)
class EstadoInterpretacaoEvidenciasNode:
    versao_schema: int
    node_id: str
    referencia_temporal: str

    quantidade_observacoes_conhecidas: int
    quantidade_observadas_agora: int

    observacoes: tuple[
        EstadoObservacaoInterpretacaoNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "quantidade_observacoes_conhecidas": (self.quantidade_observacoes_conhecidas),
            "quantidade_observadas_agora": (self.quantidade_observadas_agora),
            "observacoes": [observacao.para_dict() for observacao in self.observacoes],
        }
