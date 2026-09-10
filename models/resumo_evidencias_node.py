# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ResumoEvidenciaSinalNode:
    codigo: str
    origem: str
    titulo: str

    observado_agora: bool
    transicao_ultimo_ciclo: str

    primeira_observacao: str
    inicio_sequencia_atual: str | None
    ultima_observacao: str

    observacoes_consecutivas: int
    observacoes_totais: int
    ciclos_ausente_consecutivos: int
    deixou_de_ser_observado_em: str | None

    evidencia_ciclo_atual: dict[str, Any] | None
    evidencias_mais_recentes: dict[str, Any]

    historico_disponivel: bool
    quantidade_episodios: int | None
    reaparecimentos: int | None

    duracao_episodio_atual_segundos: float | None
    maior_duracao_acompanhada_segundos: float | None
    media_duracao_episodios_encerrados_segundos: float | None

    ultimo_intervalo_entre_episodios_segundos: float | None
    media_intervalo_entre_episodios_segundos: float | None

    qualidade_relacionada: dict[str, Any] | None

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "origem": self.origem,
            "titulo": self.titulo,
            "observado_agora": self.observado_agora,
            "transicao_ultimo_ciclo": self.transicao_ultimo_ciclo,
            "primeira_observacao": self.primeira_observacao,
            "inicio_sequencia_atual": self.inicio_sequencia_atual,
            "ultima_observacao": self.ultima_observacao,
            "observacoes_consecutivas": self.observacoes_consecutivas,
            "observacoes_totais": self.observacoes_totais,
            "ciclos_ausente_consecutivos": (self.ciclos_ausente_consecutivos),
            "deixou_de_ser_observado_em": (self.deixou_de_ser_observado_em),
            "evidencia_ciclo_atual": self.evidencia_ciclo_atual,
            "evidencias_mais_recentes": (self.evidencias_mais_recentes),
            "historico_disponivel": self.historico_disponivel,
            "quantidade_episodios": self.quantidade_episodios,
            "reaparecimentos": self.reaparecimentos,
            "duracao_episodio_atual_segundos": (self.duracao_episodio_atual_segundos),
            "maior_duracao_acompanhada_segundos": (self.maior_duracao_acompanhada_segundos),
            "media_duracao_episodios_encerrados_segundos": (
                self.media_duracao_episodios_encerrados_segundos
            ),
            "ultimo_intervalo_entre_episodios_segundos": (
                self.ultimo_intervalo_entre_episodios_segundos
            ),
            "media_intervalo_entre_episodios_segundos": (
                self.media_intervalo_entre_episodios_segundos
            ),
            "qualidade_relacionada": self.qualidade_relacionada,
        }


@dataclass(frozen=True, slots=True)
class ResumoSupressaoEvidenciaNode:
    codigo: str
    motivo: str
    evidencias: dict[str, Any]
    qualidade_relacionada: dict[str, Any] | None

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "motivo": self.motivo,
            "evidencias": self.evidencias,
            "qualidade_relacionada": self.qualidade_relacionada,
        }


@dataclass(frozen=True, slots=True)
class ResumoEvidenciasNode:
    versao_schema: int
    node_id: str
    referencia_temporal: str

    quantidade_sinais_conhecidos: int
    quantidade_sinais_observados_agora: int
    quantidade_supressoes_atuais: int

    cadencia_nominal_segundos: float | None

    qualidade_janela_recente: dict[str, Any]
    qualidade_janela_baseline: dict[str, Any]

    sinais: tuple[
        ResumoEvidenciaSinalNode,
        ...,
    ]

    supressoes: tuple[
        ResumoSupressaoEvidenciaNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "referencia_temporal": self.referencia_temporal,
            "quantidade_sinais_conhecidos": (self.quantidade_sinais_conhecidos),
            "quantidade_sinais_observados_agora": (self.quantidade_sinais_observados_agora),
            "quantidade_supressoes_atuais": (self.quantidade_supressoes_atuais),
            "cadencia_nominal_segundos": (self.cadencia_nominal_segundos),
            "qualidade_janela_recente": (self.qualidade_janela_recente),
            "qualidade_janela_baseline": (self.qualidade_janela_baseline),
            "sinais": [sinal.para_dict() for sinal in self.sinais],
            "supressoes": [supressao.para_dict() for supressao in self.supressoes],
        }
