# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SinalNode:
    codigo: str
    origem: str
    titulo: str
    descricao: str
    evidencias: dict[str, Any]

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "origem": self.origem,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "evidencias": self.evidencias,
        }


@dataclass(frozen=True, slots=True)
class SupressaoSinalNode:
    codigo: str
    motivo: str
    evidencias: dict[str, Any]

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "motivo": self.motivo,
            "evidencias": self.evidencias,
        }


@dataclass(frozen=True, slots=True)
class AnaliseSinaisNode:
    versao_schema: int
    node_id: str | None
    referencia_temporal: str | None

    servicos_continuos: tuple[str, ...]
    dependencias_persistentes: tuple[str, ...]
    workloads_intermitentes: tuple[str, ...]

    sinais: tuple[SinalNode, ...]
    supressoes: tuple[SupressaoSinalNode, ...]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "servicos_continuos": list(self.servicos_continuos),
            "dependencias_persistentes": list(self.dependencias_persistentes),
            "workloads_intermitentes": list(self.workloads_intermitentes),
            "sinais": [sinal.para_dict() for sinal in self.sinais],
            "supressoes": [supressao.para_dict() for supressao in self.supressoes],
        }
