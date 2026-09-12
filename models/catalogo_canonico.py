from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnuncioCatalogoCanonico:
    marketplace: str
    identificador: str
    chave_canonica: str
    id_anuncio: str | None
    id_produto: str | None
    link: str
    loja: str | None
    criado_em: str
    atualizado_em: str


@dataclass(frozen=True)
class ProdutoCatalogoCanonico:
    chave_canonica: str
    nome_canonico: str
    categoria: str | None
    marca: str | None
    modelo: str | None
    confianca: float
    criado_em: str
    atualizado_em: str
    anuncios: tuple[AnuncioCatalogoCanonico, ...] = ()


@dataclass(frozen=True)
class ResultadoObservacaoCatalogoCanonico:
    status: str
    registrado: bool
    chave_canonica: str | None
    marketplace: str | None
    identificador_anuncio: str | None
    motivo: str
