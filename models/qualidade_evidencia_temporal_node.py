# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class QualidadeTemporalEvidenciaSinalNode:
    codigo: str
    observado_agora: bool

    quantidade_episodios: int | None
    reaparecimentos: int | None

    inicio_historico_truncado: bool | None
    episodio_atual_aberto: bool | None

    duracao_episodio_atual_segundos: float | None
    maior_duracao_acompanhada_segundos: float | None

    qualidade_relacionada_tipo: str | None
    qualidade_relacionada_nome: str | None

    cobertura_recente_percentual: float | None
    cobertura_baseline_percentual: float | None

    cobertura_referencia_percentual: float

    cobertura_recente_atinge_referencia: bool | None
    cobertura_baseline_atinge_referencia: bool | None

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "observado_agora": self.observado_agora,
            "quantidade_episodios": self.quantidade_episodios,
            "reaparecimentos": self.reaparecimentos,
            "inicio_historico_truncado": (self.inicio_historico_truncado),
            "episodio_atual_aberto": (self.episodio_atual_aberto),
            "duracao_episodio_atual_segundos": (self.duracao_episodio_atual_segundos),
            "maior_duracao_acompanhada_segundos": (self.maior_duracao_acompanhada_segundos),
            "qualidade_relacionada_tipo": (self.qualidade_relacionada_tipo),
            "qualidade_relacionada_nome": (self.qualidade_relacionada_nome),
            "cobertura_recente_percentual": (self.cobertura_recente_percentual),
            "cobertura_baseline_percentual": (self.cobertura_baseline_percentual),
            "cobertura_referencia_percentual": (self.cobertura_referencia_percentual),
            "cobertura_recente_atinge_referencia": (self.cobertura_recente_atinge_referencia),
            "cobertura_baseline_atinge_referencia": (self.cobertura_baseline_atinge_referencia),
        }


@dataclass(frozen=True, slots=True)
class QualidadeTemporalSupressaoNode:
    codigo: str
    motivo: str

    qualidade_relacionada_tipo: str | None
    qualidade_relacionada_nome: str | None

    cobertura_recente_percentual: float | None
    cobertura_baseline_percentual: float | None

    cobertura_referencia_percentual: float | None

    cobertura_recente_atinge_referencia: bool | None
    cobertura_baseline_atinge_referencia: bool | None

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "motivo": self.motivo,
            "qualidade_relacionada_tipo": (self.qualidade_relacionada_tipo),
            "qualidade_relacionada_nome": (self.qualidade_relacionada_nome),
            "cobertura_recente_percentual": (self.cobertura_recente_percentual),
            "cobertura_baseline_percentual": (self.cobertura_baseline_percentual),
            "cobertura_referencia_percentual": (self.cobertura_referencia_percentual),
            "cobertura_recente_atinge_referencia": (self.cobertura_recente_atinge_referencia),
            "cobertura_baseline_atinge_referencia": (self.cobertura_baseline_atinge_referencia),
        }


@dataclass(frozen=True, slots=True)
class AnaliseQualidadeTemporalEvidenciaNode:
    versao_schema: int
    node_id: str
    referencia_temporal: str

    cobertura_referencia_percentual: float

    janela_recente_cobertura_percentual: float | None
    janela_baseline_cobertura_percentual: float | None

    janela_recente_amostras_esperadas: int | None
    janela_recente_amostras_observadas: int | None

    janela_baseline_amostras_esperadas: int | None
    janela_baseline_amostras_observadas: int | None

    janela_recente_gaps_2x_cadencia: int | None
    janela_baseline_gaps_2x_cadencia: int | None

    janela_recente_timestamps_repetidos: int | None
    janela_baseline_timestamps_repetidos: int | None

    quantidade_sinais: int
    quantidade_supressoes: int

    sinais: tuple[
        QualidadeTemporalEvidenciaSinalNode,
        ...,
    ]

    supressoes: tuple[
        QualidadeTemporalSupressaoNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "cobertura_referencia_percentual": (self.cobertura_referencia_percentual),
            "janela_recente_cobertura_percentual": (self.janela_recente_cobertura_percentual),
            "janela_baseline_cobertura_percentual": (self.janela_baseline_cobertura_percentual),
            "janela_recente_amostras_esperadas": (self.janela_recente_amostras_esperadas),
            "janela_recente_amostras_observadas": (self.janela_recente_amostras_observadas),
            "janela_baseline_amostras_esperadas": (self.janela_baseline_amostras_esperadas),
            "janela_baseline_amostras_observadas": (self.janela_baseline_amostras_observadas),
            "janela_recente_gaps_2x_cadencia": (self.janela_recente_gaps_2x_cadencia),
            "janela_baseline_gaps_2x_cadencia": (self.janela_baseline_gaps_2x_cadencia),
            "janela_recente_timestamps_repetidos": (self.janela_recente_timestamps_repetidos),
            "janela_baseline_timestamps_repetidos": (self.janela_baseline_timestamps_repetidos),
            "quantidade_sinais": self.quantidade_sinais,
            "quantidade_supressoes": (self.quantidade_supressoes),
            "sinais": [sinal.para_dict() for sinal in self.sinais],
            "supressoes": [supressao.para_dict() for supressao in self.supressoes],
        }
