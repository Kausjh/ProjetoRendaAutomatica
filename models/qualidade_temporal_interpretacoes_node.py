# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class QualidadeTemporalInterpretacaoItemNode:
    codigo: str
    observado_agora: bool

    primeira_evidencia: str
    ultima_evidencia: str

    registros_com_evidencia: int
    registros_esperados_desde_primeira_evidencia: int
    registros_ausentes_estimados: int

    razao_amostras_percentual: float
    cobertura_normalizada_percentual: float

    maior_gap_evidencia_segundos: float
    gaps_igual_ou_acima_2x_cadencia: int

    janela_evidencia_segundos: float
    duracao_estado_atual_segundos: float
    duracao_estado_atual_percentual_janela: float

    quantidade_episodios_observados: int
    reaparecimentos: int
    quantidade_periodos_ausentes: int

    inicio_historico_truncado: bool

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "observado_agora": self.observado_agora,
            "primeira_evidencia": self.primeira_evidencia,
            "ultima_evidencia": self.ultima_evidencia,
            "registros_com_evidencia": (self.registros_com_evidencia),
            "registros_esperados_desde_primeira_evidencia": (
                self.registros_esperados_desde_primeira_evidencia
            ),
            "registros_ausentes_estimados": (self.registros_ausentes_estimados),
            "razao_amostras_percentual": (self.razao_amostras_percentual),
            "cobertura_normalizada_percentual": (self.cobertura_normalizada_percentual),
            "maior_gap_evidencia_segundos": (self.maior_gap_evidencia_segundos),
            "gaps_igual_ou_acima_2x_cadencia": (self.gaps_igual_ou_acima_2x_cadencia),
            "janela_evidencia_segundos": (self.janela_evidencia_segundos),
            "duracao_estado_atual_segundos": (self.duracao_estado_atual_segundos),
            "duracao_estado_atual_percentual_janela": (self.duracao_estado_atual_percentual_janela),
            "quantidade_episodios_observados": (self.quantidade_episodios_observados),
            "reaparecimentos": self.reaparecimentos,
            "quantidade_periodos_ausentes": (self.quantidade_periodos_ausentes),
            "inicio_historico_truncado": (self.inicio_historico_truncado),
        }


@dataclass(frozen=True, slots=True)
class QualidadeTemporalInterpretacoesNode:
    versao_schema: int
    node_id: str
    referencia_temporal: str

    cadencia_nominal_segundos: float

    inicio_historico: str
    fim_historico: str
    janela_historica_segundos: float

    registros_observados: int
    registros_esperados: int
    registros_excedentes: int

    razao_amostras_percentual: float
    cobertura_normalizada_percentual: float

    maior_gap_historico_segundos: float
    gaps_igual_ou_acima_2x_cadencia: int

    quantidade_interpretacoes: int
    com_inicio_historico_truncado: int

    interpretacoes_por_menor_cobertura_evidencia: tuple[
        str,
        ...,
    ]

    interpretacoes: tuple[
        QualidadeTemporalInterpretacaoItemNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "cadencia_nominal_segundos": (self.cadencia_nominal_segundos),
            "inicio_historico": self.inicio_historico,
            "fim_historico": self.fim_historico,
            "janela_historica_segundos": (self.janela_historica_segundos),
            "registros_observados": self.registros_observados,
            "registros_esperados": self.registros_esperados,
            "registros_excedentes": self.registros_excedentes,
            "razao_amostras_percentual": (self.razao_amostras_percentual),
            "cobertura_normalizada_percentual": (self.cobertura_normalizada_percentual),
            "maior_gap_historico_segundos": (self.maior_gap_historico_segundos),
            "gaps_igual_ou_acima_2x_cadencia": (self.gaps_igual_ou_acima_2x_cadencia),
            "quantidade_interpretacoes": (self.quantidade_interpretacoes),
            "com_inicio_historico_truncado": (self.com_inicio_historico_truncado),
            "interpretacoes_por_menor_cobertura_evidencia": list(
                self.interpretacoes_por_menor_cobertura_evidencia
            ),
            "interpretacoes": [item.para_dict() for item in self.interpretacoes],
        }
