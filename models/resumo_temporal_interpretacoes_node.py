# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ResumoTemporalInterpretacaoItemNode:
    codigo: str
    categoria: str
    sujeito: str
    descricao: str

    observado_agora: bool
    transicao_ultimo_ciclo: str

    primeira_observacao: str
    inicio_sequencia_atual: str
    ultima_observacao: str
    deixou_de_ser_observado_em: str | None

    observacoes_consecutivas: int
    observacoes_totais: int
    ciclos_ausente_consecutivos: int

    quantidade_episodios_observados: int
    reaparecimentos: int
    quantidade_periodos_ausentes: int

    inicio_historico_truncado: bool

    episodio_atual_aberto: bool
    periodo_ausencia_atual_aberto: bool

    duracao_estado_atual_segundos: float
    maior_duracao_observada_segundos: float | None
    maior_duracao_ausencia_segundos: float | None

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "categoria": self.categoria,
            "sujeito": self.sujeito,
            "descricao": self.descricao,
            "observado_agora": self.observado_agora,
            "transicao_ultimo_ciclo": (self.transicao_ultimo_ciclo),
            "primeira_observacao": self.primeira_observacao,
            "inicio_sequencia_atual": (self.inicio_sequencia_atual),
            "ultima_observacao": self.ultima_observacao,
            "deixou_de_ser_observado_em": (self.deixou_de_ser_observado_em),
            "observacoes_consecutivas": (self.observacoes_consecutivas),
            "observacoes_totais": self.observacoes_totais,
            "ciclos_ausente_consecutivos": (self.ciclos_ausente_consecutivos),
            "quantidade_episodios_observados": (self.quantidade_episodios_observados),
            "reaparecimentos": self.reaparecimentos,
            "quantidade_periodos_ausentes": (self.quantidade_periodos_ausentes),
            "inicio_historico_truncado": (self.inicio_historico_truncado),
            "episodio_atual_aberto": (self.episodio_atual_aberto),
            "periodo_ausencia_atual_aberto": (self.periodo_ausencia_atual_aberto),
            "duracao_estado_atual_segundos": (self.duracao_estado_atual_segundos),
            "maior_duracao_observada_segundos": (self.maior_duracao_observada_segundos),
            "maior_duracao_ausencia_segundos": (self.maior_duracao_ausencia_segundos),
        }


@dataclass(frozen=True, slots=True)
class ResumoTemporalInterpretacoesNode:
    versao_schema: int
    node_id: str
    referencia_temporal: str

    quantidade_interpretacoes: int
    observadas_agora: int
    ausentes_agora: int

    novas_no_ultimo_ciclo: int
    continuaram_observadas: int
    deixaram_de_ser_observadas: int
    continuaram_ausentes: int
    reapareceram_no_ultimo_ciclo: int

    com_reaparecimento_historico: int
    com_inicio_historico_truncado: int

    observadas_por_maior_duracao_atual: tuple[str, ...]
    ausentes_por_maior_duracao_atual: tuple[str, ...]

    interpretacoes: tuple[
        ResumoTemporalInterpretacaoItemNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "quantidade_interpretacoes": (self.quantidade_interpretacoes),
            "observadas_agora": self.observadas_agora,
            "ausentes_agora": self.ausentes_agora,
            "novas_no_ultimo_ciclo": (self.novas_no_ultimo_ciclo),
            "continuaram_observadas": (self.continuaram_observadas),
            "deixaram_de_ser_observadas": (self.deixaram_de_ser_observadas),
            "continuaram_ausentes": self.continuaram_ausentes,
            "reapareceram_no_ultimo_ciclo": (self.reapareceram_no_ultimo_ciclo),
            "com_reaparecimento_historico": (self.com_reaparecimento_historico),
            "com_inicio_historico_truncado": (self.com_inicio_historico_truncado),
            "observadas_por_maior_duracao_atual": list(self.observadas_por_maior_duracao_atual),
            "ausentes_por_maior_duracao_atual": list(self.ausentes_por_maior_duracao_atual),
            "interpretacoes": [item.para_dict() for item in self.interpretacoes],
        }
