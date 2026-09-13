from __future__ import annotations

import json
import sqlite3

from models.oferta import Oferta
from repositories.catalogo_canonico_repository import (
    CatalogoCanonicoRepository,
)
from services.bootstrap_catalogo_canonico_service import (
    BootstrapCatalogoCanonicoService,
)


def oferta_payload(
    *,
    marketplace: str = "Mercado Livre",
    identificador: str | None = "MLB1",
    chave: str | None = "produto_a",
    produto: str | None = "Produto A",
    confianca: float = 95.0,
) -> dict:
    oferta = Oferta(
        nome=produto or "Produto",
        loja=marketplace,
        preco=100.0,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace=marketplace,
        id_anuncio=identificador,
        id_produto=identificador,
    )
    oferta.produto_canonico = produto
    oferta.chave_produto_canonica = chave
    oferta.modelo_produto = produto
    oferta.confianca_normalizacao = confianca
    return oferta.__dict__


def criar_fila(
    caminho,
    *,
    ativos: list[object],
    historico: list[object],
) -> None:
    conexao = sqlite3.connect(caminho)

    try:
        conexao.execute("""
            CREATE TABLE fila_publicacao (
                id INTEGER PRIMARY KEY,
                oferta_json TEXT
            )
            """)
        conexao.execute("""
            CREATE TABLE historico_publicacoes_fila (
                id INTEGER PRIMARY KEY,
                oferta_json TEXT
            )
            """)

        for indice, payload in enumerate(
            ativos,
            start=1,
        ):
            if isinstance(
                payload,
                str,
            ):
                valor = payload
            else:
                valor = json.dumps(
                    payload,
                    ensure_ascii=False,
                )

            conexao.execute(
                """
                INSERT INTO fila_publicacao (
                    id,
                    oferta_json
                )
                VALUES (?, ?)
                """,
                (
                    indice,
                    valor,
                ),
            )

        for indice, payload in enumerate(
            historico,
            start=1,
        ):
            if isinstance(
                payload,
                str,
            ):
                valor = payload
            else:
                valor = json.dumps(
                    payload,
                    ensure_ascii=False,
                )

            conexao.execute(
                """
                INSERT INTO historico_publicacoes_fila (
                    id,
                    oferta_json
                )
                VALUES (?, ?)
                """,
                (
                    indice,
                    valor,
                ),
            )

        conexao.commit()
    finally:
        conexao.close()


def test_bootstrap_importa_fila_e_historico(
    tmp_path,
):
    fila = tmp_path / "fila.sqlite3"
    catalogo = tmp_path / "catalogo.sqlite3"

    criar_fila(
        fila,
        ativos=[
            oferta_payload(
                identificador="MLB1",
                chave="produto_a",
            ),
        ],
        historico=[
            oferta_payload(
                marketplace="Shopee",
                identificador="SHP1",
                chave="produto_a",
            ),
            oferta_payload(
                identificador="MLB2",
                chave="produto_b",
                produto="Produto B",
            ),
        ],
    )

    service = BootstrapCatalogoCanonicoService(
        caminho_fila=fila,
        caminho_catalogo=catalogo,
    )

    resultado = service.executar()
    repository = CatalogoCanonicoRepository(catalogo)

    assert resultado["totais"]["elegiveis"] == 3
    assert resultado["totais"]["registrados"] == 3
    assert repository.quantidade_produtos() == 2
    assert repository.quantidade_anuncios() == 3


def test_bootstrap_prioriza_fila_e_registra_conflito_sem_remapear(
    tmp_path,
):
    fila = tmp_path / "fila.sqlite3"
    catalogo = tmp_path / "catalogo.sqlite3"

    criar_fila(
        fila,
        ativos=[
            oferta_payload(
                identificador="MLB1",
                chave="produto_a",
            ),
        ],
        historico=[
            oferta_payload(
                identificador="MLB1",
                chave="produto_b",
                produto="Produto B",
            ),
        ],
    )

    service = BootstrapCatalogoCanonicoService(
        caminho_fila=fila,
        caminho_catalogo=catalogo,
    )

    resultado = service.executar()
    repository = CatalogoCanonicoRepository(catalogo)

    produto = repository.obter_por_anuncio(
        marketplace="mercado_livre",
        identificador="MLB1",
    )

    assert produto is not None
    assert produto.chave_canonica == "produto_a"
    assert repository.obter_produto("produto_b") is None
    assert repository.quantidade_conflitos() == 1
    assert resultado["totais"]["conflitos_registrados"] == 1


def test_bootstrap_e_idempotente_inclusive_para_conflitos(
    tmp_path,
):
    fila = tmp_path / "fila.sqlite3"
    catalogo = tmp_path / "catalogo.sqlite3"

    criar_fila(
        fila,
        ativos=[
            oferta_payload(
                identificador="MLB1",
                chave="produto_a",
            ),
        ],
        historico=[
            oferta_payload(
                identificador="MLB1",
                chave="produto_b",
                produto="Produto B",
            ),
        ],
    )

    service = BootstrapCatalogoCanonicoService(
        caminho_fila=fila,
        caminho_catalogo=catalogo,
    )

    service.executar()

    repository = CatalogoCanonicoRepository(catalogo)
    antes = repository.obter_metricas()
    conflito_antes = repository.listar_conflitos()[0]

    segunda = service.executar()

    depois = repository.obter_metricas()
    conflito_depois = repository.listar_conflitos()[0]

    assert depois == antes
    assert conflito_depois["ocorrencias"] == conflito_antes["ocorrencias"]
    assert segunda["totais"]["ja_presentes"] == 1
    assert segunda["totais"]["conflitos_ja_registrados"] == 1


def test_bootstrap_ignora_incompletos_baixa_confianca_e_json_ruim(
    tmp_path,
):
    fila = tmp_path / "fila.sqlite3"
    catalogo = tmp_path / "catalogo.sqlite3"

    criar_fila(
        fila,
        ativos=[
            oferta_payload(
                identificador=None,
            ),
            oferta_payload(
                identificador="MLB2",
                confianca=40.0,
            ),
            "{json quebrado",
        ],
        historico=[],
    )

    resultado = BootstrapCatalogoCanonicoService(
        caminho_fila=fila,
        caminho_catalogo=catalogo,
    ).executar()

    totais = resultado["totais"]

    assert totais["incompletos"] == 1
    assert totais["baixa_confianca"] == 1
    assert totais["json_invalidos"] == 1

    repository = CatalogoCanonicoRepository(catalogo)
    assert repository.quantidade_produtos() == 0
    assert repository.quantidade_anuncios() == 0


def test_simulacao_nao_altera_catalogo_real(
    tmp_path,
):
    fila = tmp_path / "fila.sqlite3"
    catalogo = tmp_path / "catalogo.sqlite3"

    criar_fila(
        fila,
        ativos=[
            oferta_payload(),
        ],
        historico=[],
    )

    repository = CatalogoCanonicoRepository(catalogo)
    antes = repository.obter_metricas()

    resultado = BootstrapCatalogoCanonicoService(
        caminho_fila=fila,
        caminho_catalogo=catalogo,
    ).simular()

    depois = repository.obter_metricas()

    assert antes == depois
    assert resultado["modo"] == "simulacao"
    assert resultado["catalogo_depois"]["produtos"] == 1


def test_fonte_e_aberta_em_modo_read_only(
    tmp_path,
):
    fila = tmp_path / "fila.sqlite3"
    catalogo = tmp_path / "catalogo.sqlite3"

    criar_fila(
        fila,
        ativos=[
            oferta_payload(),
        ],
        historico=[],
    )

    service = BootstrapCatalogoCanonicoService(
        caminho_fila=fila,
        caminho_catalogo=catalogo,
    )

    service.executar()

    conexao = sqlite3.connect(fila)

    try:
        total = conexao.execute("""
            SELECT COUNT(*)
            FROM fila_publicacao
            """).fetchone()[0]
    finally:
        conexao.close()

    assert total == 1


def test_bootstrap_nao_e_wirado_no_startup():
    from pathlib import Path

    for caminho in (
        "main.py",
        "services/runtime/orquestrador.py",
    ):
        texto = Path(caminho).read_text(encoding="utf-8-sig")
        assert "BootstrapCatalogoCanonicoService" not in texto


# 63.8738, -149.7525
