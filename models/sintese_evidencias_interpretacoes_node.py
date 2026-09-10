# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SinteseInterpretacaoEvidenciaNode:
    codigo: str
    categoria: str
    sujeito: str
    descricao: str

    observado_agora: bool
    transicao_ultimo_ciclo: str

    duracao_estado_atual_segundos: float
    duracao_estado_atual_percentual_janela: float

    quantidade_episodios_observados: int
    reaparecimentos: int
    quantidade_periodos_ausentes: int

    inicio_historico_truncado: bool

    primeira_evidencia: str
    ultima_evidencia: str
    janela_evidencia_segundos: float

    registros_com_evidencia: int
    registros_esperados_desde_primeira_evidencia: int
    registros_ausentes_estimados: int

    razao_amostras_percentual: float
    cobertura_evidencia_percentual: float

    maior_gap_evidencia_segundos: float
    gaps_igual_ou_acima_2x_cadencia: int

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "categoria": self.categoria,
            "sujeito": self.sujeito,
            "descricao": self.descricao,
            "observado_agora": self.observado_agora,
            "transicao_ultimo_ciclo": (self.transicao_ultimo_ciclo),
            "duracao_estado_atual_segundos": (self.duracao_estado_atual_segundos),
            "duracao_estado_atual_percentual_janela": (self.duracao_estado_atual_percentual_janela),
            "quantidade_episodios_observados": (self.quantidade_episodios_observados),
            "reaparecimentos": self.reaparecimentos,
            "quantidade_periodos_ausentes": (self.quantidade_periodos_ausentes),
            "inicio_historico_truncado": (self.inicio_historico_truncado),
            "primeira_evidencia": self.primeira_evidencia,
            "ultima_evidencia": self.ultima_evidencia,
            "janela_evidencia_segundos": (self.janela_evidencia_segundos),
            "registros_com_evidencia": (self.registros_com_evidencia),
            "registros_esperados_desde_primeira_evidencia": (
                self.registros_esperados_desde_primeira_evidencia
            ),
            "registros_ausentes_estimados": (self.registros_ausentes_estimados),
            "razao_amostras_percentual": (self.razao_amostras_percentual),
            "cobertura_evidencia_percentual": (self.cobertura_evidencia_percentual),
            "maior_gap_evidencia_segundos": (self.maior_gap_evidencia_segundos),
            "gaps_igual_ou_acima_2x_cadencia": (self.gaps_igual_ou_acima_2x_cadencia),
        }


@dataclass(frozen=True, slots=True)
class SinteseEvidenciasInterpretacoesNode:
    versao_schema: int
    node_id: str
    referencia_temporal: str
    cadencia_nominal_segundos: float

    quantidade_interpretacoes: int
    observadas_agora: int
    ausentes_agora: int

    com_reaparecimento_historico: tuple[str, ...]
    com_lacunas_evidencia_estimadas: tuple[str, ...]
    com_gaps_igual_ou_acima_2x_cadencia: tuple[str, ...]
    com_inicio_historico_truncado: tuple[str, ...]

    observadas_por_maior_duracao_atual: tuple[str, ...]
    ausentes_por_maior_duracao_atual: tuple[str, ...]
    por_menor_cobertura_evidencia: tuple[str, ...]

    interpretacoes: tuple[
        SinteseInterpretacaoEvidenciaNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "cadencia_nominal_segundos": (self.cadencia_nominal_segundos),
            "quantidade_interpretacoes": (self.quantidade_interpretacoes),
            "observadas_agora": self.observadas_agora,
            "ausentes_agora": self.ausentes_agora,
            "com_reaparecimento_historico": list(self.com_reaparecimento_historico),
            "com_lacunas_evidencia_estimadas": list(self.com_lacunas_evidencia_estimadas),
            "com_gaps_igual_ou_acima_2x_cadencia": list(self.com_gaps_igual_ou_acima_2x_cadencia),
            "com_inicio_historico_truncado": list(self.com_inicio_historico_truncado),
            "observadas_por_maior_duracao_atual": list(self.observadas_por_maior_duracao_atual),
            "ausentes_por_maior_duracao_atual": list(self.ausentes_por_maior_duracao_atual),
            "por_menor_cobertura_evidencia": list(self.por_menor_cobertura_evidencia),
            "interpretacoes": [item.para_dict() for item in self.interpretacoes],
        }
