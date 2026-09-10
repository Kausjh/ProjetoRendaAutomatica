# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ComparativoMetricaNode:
    atual: float | None

    media_recente: float | None
    media_baseline: float | None

    delta_media_absoluto: float | None
    delta_media_percentual: float | None

    inclinacao_recente_por_hora: float | None

    amostras_recente: int
    amostras_baseline: int

    def para_dict(self) -> dict[str, Any]:
        return {
            "atual": self.atual,
            "media_recente": self.media_recente,
            "media_baseline": self.media_baseline,
            "delta_media_absoluto": (self.delta_media_absoluto),
            "delta_media_percentual": (self.delta_media_percentual),
            "inclinacao_recente_por_hora": (self.inclinacao_recente_por_hora),
            "amostras_recente": self.amostras_recente,
            "amostras_baseline": self.amostras_baseline,
        }


@dataclass(frozen=True, slots=True)
class TendenciaServicoNode:
    nome: str

    memoria_rss_bytes: ComparativoMetricaNode

    percentual_ativo_recente: float | None
    percentual_ativo_baseline: float | None
    delta_percentual_ativo_pontos: float | None

    amostras_observadas_recente: int
    amostras_observadas_baseline: int

    def para_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "memoria_rss_bytes": (self.memoria_rss_bytes.para_dict()),
            "percentual_ativo_recente": (self.percentual_ativo_recente),
            "percentual_ativo_baseline": (self.percentual_ativo_baseline),
            "delta_percentual_ativo_pontos": (self.delta_percentual_ativo_pontos),
            "amostras_observadas_recente": (self.amostras_observadas_recente),
            "amostras_observadas_baseline": (self.amostras_observadas_baseline),
        }


@dataclass(frozen=True, slots=True)
class AnaliseTendenciaNode:
    versao_schema: int
    node_id: str | None

    referencia_temporal: str

    inicio_baseline: str
    fim_baseline: str

    inicio_recente: str
    fim_recente: str

    janela_recente_minutos: int
    janela_baseline_minutos: int

    quantidade_amostras_recente: int
    quantidade_amostras_baseline: int

    cpu_percentual: ComparativoMetricaNode
    memoria_host_percentual: ComparativoMetricaNode
    memoria_processos_projeto_bytes: ComparativoMetricaNode
    quantidade_processos_projeto: ComparativoMetricaNode

    servicos: tuple[TendenciaServicoNode, ...]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "inicio_baseline": self.inicio_baseline,
            "fim_baseline": self.fim_baseline,
            "inicio_recente": self.inicio_recente,
            "fim_recente": self.fim_recente,
            "janela_recente_minutos": (self.janela_recente_minutos),
            "janela_baseline_minutos": (self.janela_baseline_minutos),
            "quantidade_amostras_recente": (self.quantidade_amostras_recente),
            "quantidade_amostras_baseline": (self.quantidade_amostras_baseline),
            "cpu_percentual": self.cpu_percentual.para_dict(),
            "memoria_host_percentual": (self.memoria_host_percentual.para_dict()),
            "memoria_processos_projeto_bytes": (self.memoria_processos_projeto_bytes.para_dict()),
            "quantidade_processos_projeto": (self.quantidade_processos_projeto.para_dict()),
            "servicos": [servico.para_dict() for servico in self.servicos],
        }
