# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ObservacaoEstruturadaEvidenciaNode:
    codigo: str
    categoria: str
    sujeito: str
    descricao: str
    dados: dict[str, Any]
    fontes: tuple[str, ...]

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "categoria": self.categoria,
            "sujeito": self.sujeito,
            "descricao": self.descricao,
            "dados": self.dados,
            "fontes": list(self.fontes),
        }


@dataclass(frozen=True, slots=True)
class InterpretacaoObservacionalEvidenciasNode:
    versao_schema: int
    node_id: str
    referencia_temporal: str

    quantidade_observacoes: int

    observacoes: tuple[
        ObservacaoEstruturadaEvidenciaNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "quantidade_observacoes": (self.quantidade_observacoes),
            "observacoes": [observacao.para_dict() for observacao in self.observacoes],
        }
