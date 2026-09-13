from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResultadoObservacaoPriceIntelligence:
    status: str
    registrado: bool
    nova_observacao_historica: bool
    chave_canonica: str | None
    marketplace: str | None
    identificador: str | None
    preco: float | None
    motivo: str


@dataclass(frozen=True, slots=True)
class PrecoAtualCanonico:
    chave_canonica: str
    marketplace: str
    identificador: str
    nome_canonico: str
    preco_atual: float
    link: str
    primeiro_observado_em: str
    ultimo_observado_em: str


@dataclass(frozen=True, slots=True)
class SnapshotPriceIntelligence:
    chave_canonica: str
    nome_canonico: str
    preco_minimo_atual: float
    preco_maximo_atual: float
    mediana_atual: float
    marketplace_melhor_preco: str
    identificador_melhor_preco: str
    anuncios_observados: int
    marketplaces_observados: tuple[str, ...]
    menor_preco_historico: float
    mediana_historica: float
    observacoes_historicas: int
    atualizado_em: str
