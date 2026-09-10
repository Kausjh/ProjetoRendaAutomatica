# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EpisodioTemporalSinalNode:
    inicio_em: str
    fim_detectado_em: str | None
    inicio_confirmado: bool
    aberto_no_fim_da_janela: bool
    observacoes_ativas: int
    duracao_acompanhada_segundos: float

    def para_dict(self) -> dict[str, Any]:
        return {
            "inicio_em": self.inicio_em,
            "fim_detectado_em": self.fim_detectado_em,
            "inicio_confirmado": self.inicio_confirmado,
            "aberto_no_fim_da_janela": (self.aberto_no_fim_da_janela),
            "observacoes_ativas": self.observacoes_ativas,
            "duracao_acompanhada_segundos": (self.duracao_acompanhada_segundos),
        }


@dataclass(frozen=True, slots=True)
class ResumoHistoricoSinalNode:
    codigo: str
    origem: str
    titulo: str
    observado_agora: bool

    quantidade_episodios: int
    reaparecimentos: int

    duracao_episodio_atual_segundos: float | None
    maior_duracao_acompanhada_segundos: float | None
    media_duracao_episodios_encerrados_segundos: float | None

    ultimo_intervalo_entre_episodios_segundos: float | None
    media_intervalo_entre_episodios_segundos: float | None

    episodios: tuple[
        EpisodioTemporalSinalNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "origem": self.origem,
            "titulo": self.titulo,
            "observado_agora": self.observado_agora,
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
            "episodios": [episodio.para_dict() for episodio in self.episodios],
        }


@dataclass(frozen=True, slots=True)
class AnaliseHistoricoSinaisNode:
    versao_schema: int
    node_id: str | None

    inicio_periodo: str
    fim_periodo: str

    quantidade_amostras: int
    linhas_invalidas_ignoradas: int
    amostras_duplicadas_ignoradas: int

    sinais: tuple[
        ResumoHistoricoSinalNode,
        ...,
    ]

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "inicio_periodo": self.inicio_periodo,
            "fim_periodo": self.fim_periodo,
            "quantidade_amostras": self.quantidade_amostras,
            "linhas_invalidas_ignoradas": (self.linhas_invalidas_ignoradas),
            "amostras_duplicadas_ignoradas": (self.amostras_duplicadas_ignoradas),
            "sinais": [sinal.para_dict() for sinal in self.sinais],
        }
