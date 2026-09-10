# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class IntervaloInterpretacaoNode:
    inicio: str
    fim: str

    inicio_confirmado: bool
    fim_confirmado: bool

    duracao_acompanhada_segundos: float

    def para_dict(self) -> dict[str, Any]:
        return {
            "inicio": self.inicio,
            "fim": self.fim,
            "inicio_confirmado": self.inicio_confirmado,
            "fim_confirmado": self.fim_confirmado,
            "duracao_acompanhada_segundos": (self.duracao_acompanhada_segundos),
        }


@dataclass(frozen=True, slots=True)
class AnaliseHistoricaInterpretacaoNode:
    codigo: str
    categoria: str
    sujeito: str
    descricao: str

    primeira_referencia: str
    ultima_referencia: str

    observado_agora: bool
    observacoes_explicitas: int

    quantidade_episodios_observados: int
    reaparecimentos: int

    quantidade_periodos_ausentes: int

    episodio_atual_aberto: bool
    periodo_ausencia_atual_aberto: bool

    duracao_episodio_atual_segundos: float | None
    duracao_ausencia_atual_segundos: float | None

    maior_duracao_observada_segundos: float | None
    maior_duracao_ausencia_segundos: float | None

    episodios_observados: tuple[
        IntervaloInterpretacaoNode,
        ...,
    ]

    periodos_ausentes: tuple[
        IntervaloInterpretacaoNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "categoria": self.categoria,
            "sujeito": self.sujeito,
            "descricao": self.descricao,
            "primeira_referencia": self.primeira_referencia,
            "ultima_referencia": self.ultima_referencia,
            "observado_agora": self.observado_agora,
            "observacoes_explicitas": (self.observacoes_explicitas),
            "quantidade_episodios_observados": (self.quantidade_episodios_observados),
            "reaparecimentos": self.reaparecimentos,
            "quantidade_periodos_ausentes": (self.quantidade_periodos_ausentes),
            "episodio_atual_aberto": (self.episodio_atual_aberto),
            "periodo_ausencia_atual_aberto": (self.periodo_ausencia_atual_aberto),
            "duracao_episodio_atual_segundos": (self.duracao_episodio_atual_segundos),
            "duracao_ausencia_atual_segundos": (self.duracao_ausencia_atual_segundos),
            "maior_duracao_observada_segundos": (self.maior_duracao_observada_segundos),
            "maior_duracao_ausencia_segundos": (self.maior_duracao_ausencia_segundos),
            "episodios_observados": [item.para_dict() for item in self.episodios_observados],
            "periodos_ausentes": [item.para_dict() for item in self.periodos_ausentes],
        }


@dataclass(frozen=True, slots=True)
class AnaliseHistoricoInterpretacoesNode:
    versao_schema: int

    node_id: str

    inicio_periodo: str
    fim_periodo: str

    quantidade_registros: int
    quantidade_interpretacoes: int

    interpretacoes: tuple[
        AnaliseHistoricaInterpretacaoNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "inicio_periodo": self.inicio_periodo,
            "fim_periodo": self.fim_periodo,
            "quantidade_registros": (self.quantidade_registros),
            "quantidade_interpretacoes": (self.quantidade_interpretacoes),
            "interpretacoes": [item.para_dict() for item in self.interpretacoes],
        }
