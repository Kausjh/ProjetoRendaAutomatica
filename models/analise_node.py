# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ResumoMetricaNode:
    atual: float | None
    minimo: float | None
    maximo: float | None
    media: float | None
    mediana: float | None
    delta_primeira_ultima: float | None
    quantidade_amostras: int

    def para_dict(self) -> dict[str, Any]:
        return {
            "atual": self.atual,
            "minimo": self.minimo,
            "maximo": self.maximo,
            "media": self.media,
            "mediana": self.mediana,
            "delta_primeira_ultima": (self.delta_primeira_ultima),
            "quantidade_amostras": (self.quantidade_amostras),
        }


@dataclass(frozen=True, slots=True)
class ResumoServicoNode:
    nome: str
    amostras_observadas: int
    amostras_ativas: int
    percentual_ativo: float | None
    memoria_rss_bytes: ResumoMetricaNode

    def para_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "amostras_observadas": (self.amostras_observadas),
            "amostras_ativas": (self.amostras_ativas),
            "percentual_ativo": (self.percentual_ativo),
            "memoria_rss_bytes": (self.memoria_rss_bytes.para_dict()),
        }


@dataclass(frozen=True, slots=True)
class AnaliseHistoricoNode:
    versao_schema: int
    node_id: str | None
    inicio_periodo: str
    fim_periodo: str

    quantidade_amostras: int
    quantidade_amostras_v13: int
    reinicios_detectados: int

    cpu_percentual: ResumoMetricaNode
    memoria_host_percentual: ResumoMetricaNode
    memoria_processos_projeto_bytes: ResumoMetricaNode
    quantidade_processos_projeto: ResumoMetricaNode

    servicos: tuple[ResumoServicoNode, ...]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "inicio_periodo": self.inicio_periodo,
            "fim_periodo": self.fim_periodo,
            "quantidade_amostras": (self.quantidade_amostras),
            "quantidade_amostras_v13": (self.quantidade_amostras_v13),
            "reinicios_detectados": (self.reinicios_detectados),
            "cpu_percentual": (self.cpu_percentual.para_dict()),
            "memoria_host_percentual": (self.memoria_host_percentual.para_dict()),
            "memoria_processos_projeto_bytes": (self.memoria_processos_projeto_bytes.para_dict()),
            "quantidade_processos_projeto": (self.quantidade_processos_projeto.para_dict()),
            "servicos": [servico.para_dict() for servico in self.servicos],
        }
