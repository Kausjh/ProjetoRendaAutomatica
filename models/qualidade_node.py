# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class QualidadeJanelaNode:
    nome: str
    inicio: str
    fim: str
    duracao_minutos: int

    cadencia_nominal_segundos: float

    amostras_esperadas: int
    amostras_observadas: int
    razao_amostras_percentual: float | None

    primeira_amostra: str | None
    ultima_amostra: str | None

    maior_gap_segundos: float | None
    maior_gap_multiplo_cadencia: float | None

    gaps_igual_ou_acima_2x_cadencia: int
    timestamps_repetidos: int

    def para_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "inicio": self.inicio,
            "fim": self.fim,
            "duracao_minutos": self.duracao_minutos,
            "cadencia_nominal_segundos": (self.cadencia_nominal_segundos),
            "amostras_esperadas": self.amostras_esperadas,
            "amostras_observadas": self.amostras_observadas,
            "razao_amostras_percentual": (self.razao_amostras_percentual),
            "primeira_amostra": self.primeira_amostra,
            "ultima_amostra": self.ultima_amostra,
            "maior_gap_segundos": self.maior_gap_segundos,
            "maior_gap_multiplo_cadencia": (self.maior_gap_multiplo_cadencia),
            "gaps_igual_ou_acima_2x_cadencia": (self.gaps_igual_ou_acima_2x_cadencia),
            "timestamps_repetidos": self.timestamps_repetidos,
        }


@dataclass(frozen=True, slots=True)
class CoberturaMetricaNode:
    nome: str

    amostras_com_valor_recente: int
    amostras_com_valor_baseline: int

    percentual_presenca_recente: float | None
    percentual_presenca_baseline: float | None

    comparacao_disponivel: bool
    inclinacao_recente_disponivel: bool

    def para_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "amostras_com_valor_recente": (self.amostras_com_valor_recente),
            "amostras_com_valor_baseline": (self.amostras_com_valor_baseline),
            "percentual_presenca_recente": (self.percentual_presenca_recente),
            "percentual_presenca_baseline": (self.percentual_presenca_baseline),
            "comparacao_disponivel": (self.comparacao_disponivel),
            "inclinacao_recente_disponivel": (self.inclinacao_recente_disponivel),
        }


@dataclass(frozen=True, slots=True)
class QualidadeServicoNode:
    nome: str

    amostras_observadas_recente: int
    amostras_observadas_baseline: int

    percentual_presenca_recente: float | None
    percentual_presenca_baseline: float | None

    memoria_rss_bytes: CoberturaMetricaNode

    def para_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "amostras_observadas_recente": (self.amostras_observadas_recente),
            "amostras_observadas_baseline": (self.amostras_observadas_baseline),
            "percentual_presenca_recente": (self.percentual_presenca_recente),
            "percentual_presenca_baseline": (self.percentual_presenca_baseline),
            "memoria_rss_bytes": (self.memoria_rss_bytes.para_dict()),
        }


@dataclass(frozen=True, slots=True)
class AnaliseQualidadeDadosNode:
    versao_schema: int
    node_id: str | None
    referencia_temporal: str

    cadencia_nominal_segundos: float

    janela_recente: QualidadeJanelaNode
    janela_baseline: QualidadeJanelaNode

    metricas: tuple[CoberturaMetricaNode, ...]
    servicos: tuple[QualidadeServicoNode, ...]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "cadencia_nominal_segundos": (self.cadencia_nominal_segundos),
            "janela_recente": self.janela_recente.para_dict(),
            "janela_baseline": self.janela_baseline.para_dict(),
            "metricas": [metrica.para_dict() for metrica in self.metricas],
            "servicos": [servico.para_dict() for servico in self.servicos],
        }
