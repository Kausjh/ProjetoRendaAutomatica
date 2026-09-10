# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EvolucaoCicloSinteseInterpretacoesNode:
    referencia_temporal: str
    quantidade_interpretacoes: int
    observadas_agora: int
    ausentes_agora: int

    com_reaparecimento_historico: int
    com_lacunas_evidencia_estimadas: int
    com_gaps_igual_ou_acima_2x_cadencia: int
    com_inicio_historico_truncado: int

    novas_interpretacoes: tuple[str, ...]
    interpretacoes_removidas: tuple[str, ...]
    passaram_a_ser_observadas: tuple[str, ...]
    deixaram_de_ser_observadas: tuple[str, ...]
    reaparecimentos_incrementados: tuple[str, ...]

    cobertura_media_percentual: float
    menor_cobertura_percentual: float
    maior_gap_evidencia_segundos: float

    def para_dict(self) -> dict[str, Any]:
        return {
            "referencia_temporal": self.referencia_temporal,
            "quantidade_interpretacoes": self.quantidade_interpretacoes,
            "observadas_agora": self.observadas_agora,
            "ausentes_agora": self.ausentes_agora,
            "com_reaparecimento_historico": (self.com_reaparecimento_historico),
            "com_lacunas_evidencia_estimadas": (self.com_lacunas_evidencia_estimadas),
            "com_gaps_igual_ou_acima_2x_cadencia": (self.com_gaps_igual_ou_acima_2x_cadencia),
            "com_inicio_historico_truncado": (self.com_inicio_historico_truncado),
            "novas_interpretacoes": list(self.novas_interpretacoes),
            "interpretacoes_removidas": list(self.interpretacoes_removidas),
            "passaram_a_ser_observadas": list(self.passaram_a_ser_observadas),
            "deixaram_de_ser_observadas": list(self.deixaram_de_ser_observadas),
            "reaparecimentos_incrementados": list(self.reaparecimentos_incrementados),
            "cobertura_media_percentual": (self.cobertura_media_percentual),
            "menor_cobertura_percentual": (self.menor_cobertura_percentual),
            "maior_gap_evidencia_segundos": (self.maior_gap_evidencia_segundos),
        }


@dataclass(frozen=True, slots=True)
class HistoricoSinteseInterpretacaoNode:
    codigo: str

    primeira_evidencia_no_historico: str
    ultima_evidencia_no_historico: str

    registros_presente: int
    registros_observada: int
    registros_ausente: int

    mudancas_estado_observado: int
    incrementos_reaparecimento: int

    cobertura_minima_percentual: float
    cobertura_media_percentual: float
    maior_gap_evidencia_segundos: float

    presente_agora: bool
    observado_agora: bool | None
    reaparecimentos_agora: int | None

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "primeira_evidencia_no_historico": (self.primeira_evidencia_no_historico),
            "ultima_evidencia_no_historico": (self.ultima_evidencia_no_historico),
            "registros_presente": self.registros_presente,
            "registros_observada": self.registros_observada,
            "registros_ausente": self.registros_ausente,
            "mudancas_estado_observado": (self.mudancas_estado_observado),
            "incrementos_reaparecimento": (self.incrementos_reaparecimento),
            "cobertura_minima_percentual": (self.cobertura_minima_percentual),
            "cobertura_media_percentual": (self.cobertura_media_percentual),
            "maior_gap_evidencia_segundos": (self.maior_gap_evidencia_segundos),
            "presente_agora": self.presente_agora,
            "observado_agora": self.observado_agora,
            "reaparecimentos_agora": (self.reaparecimentos_agora),
        }


@dataclass(frozen=True, slots=True)
class AnaliseHistoricoSintesesInterpretacoesNode:
    versao_schema: int
    node_id: str

    inicio_historico: str
    fim_historico: str

    quantidade_registros: int
    quantidade_interpretacoes_ultima_sintese: int
    quantidade_interpretacoes_distintas: int

    novas_interpretacoes_total: int
    interpretacoes_removidas_total: int
    mudancas_estado_observado_total: int
    incrementos_reaparecimento_total: int

    ciclos_com_lacunas_evidencia: int
    ciclos_com_gaps_igual_ou_acima_2x_cadencia: int
    ciclos_com_inicio_historico_truncado: int

    cobertura_minima_historica_percentual: float
    cobertura_media_historica_percentual: float
    maior_gap_evidencia_historico_segundos: float

    ciclos: tuple[
        EvolucaoCicloSinteseInterpretacoesNode,
        ...,
    ]

    interpretacoes: tuple[
        HistoricoSinteseInterpretacaoNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "inicio_historico": self.inicio_historico,
            "fim_historico": self.fim_historico,
            "quantidade_registros": self.quantidade_registros,
            "quantidade_interpretacoes_ultima_sintese": (
                self.quantidade_interpretacoes_ultima_sintese
            ),
            "quantidade_interpretacoes_distintas": (self.quantidade_interpretacoes_distintas),
            "novas_interpretacoes_total": (self.novas_interpretacoes_total),
            "interpretacoes_removidas_total": (self.interpretacoes_removidas_total),
            "mudancas_estado_observado_total": (self.mudancas_estado_observado_total),
            "incrementos_reaparecimento_total": (self.incrementos_reaparecimento_total),
            "ciclos_com_lacunas_evidencia": (self.ciclos_com_lacunas_evidencia),
            "ciclos_com_gaps_igual_ou_acima_2x_cadencia": (
                self.ciclos_com_gaps_igual_ou_acima_2x_cadencia
            ),
            "ciclos_com_inicio_historico_truncado": (self.ciclos_com_inicio_historico_truncado),
            "cobertura_minima_historica_percentual": (self.cobertura_minima_historica_percentual),
            "cobertura_media_historica_percentual": (self.cobertura_media_historica_percentual),
            "maior_gap_evidencia_historico_segundos": (self.maior_gap_evidencia_historico_segundos),
            "ciclos": [ciclo.para_dict() for ciclo in self.ciclos],
            "interpretacoes": [item.para_dict() for item in self.interpretacoes],
        }
