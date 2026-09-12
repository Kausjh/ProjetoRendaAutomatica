from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from models.catalogo_canonico import (
    AnuncioCatalogoCanonico,
    ProdutoCatalogoCanonico,
)


class CatalogoCanonicoRepository:
    def __init__(
        self,
        caminho_banco: str | Path = "database/catalogo_canonico.sqlite3",
    ) -> None:
        self.caminho_banco = Path(caminho_banco)
        self.caminho_banco.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar()

    @contextmanager
    def _conectar(
        self,
    ) -> Iterator[sqlite3.Connection]:
        conexao = sqlite3.connect(
            self.caminho_banco,
            timeout=10,
        )
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")

        try:
            yield conexao
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        finally:
            conexao.close()

    def _inicializar(self) -> None:
        with self._conectar() as conexao:
            conexao.execute("""
                CREATE TABLE IF NOT EXISTS produtos_canonicos (
                    chave_canonica TEXT PRIMARY KEY,
                    nome_canonico TEXT NOT NULL,
                    categoria TEXT,
                    marca TEXT,
                    modelo TEXT,
                    confianca REAL NOT NULL,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                )
                """)
            conexao.execute("""
                CREATE TABLE IF NOT EXISTS anuncios_canonicos (
                    marketplace TEXT NOT NULL,
                    identificador TEXT NOT NULL,
                    chave_canonica TEXT NOT NULL,
                    id_anuncio TEXT,
                    id_produto TEXT,
                    link TEXT NOT NULL,
                    loja TEXT,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    PRIMARY KEY (marketplace, identificador),
                    FOREIGN KEY (chave_canonica)
                        REFERENCES produtos_canonicos (chave_canonica)
                        ON DELETE RESTRICT
                )
                """)
            conexao.execute("""
                CREATE INDEX IF NOT EXISTS idx_anuncios_canonicos_produto
                ON anuncios_canonicos (chave_canonica)
                """)

    def registrar_observacao(
        self,
        *,
        chave_canonica: str,
        nome_canonico: str,
        categoria: str | None,
        marca: str | None,
        modelo: str | None,
        confianca: float,
        marketplace: str,
        identificador: str,
        id_anuncio: str | None,
        id_produto: str | None,
        link: str,
        loja: str | None,
    ) -> str:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            existente = conexao.execute(
                """
                SELECT chave_canonica
                FROM anuncios_canonicos
                WHERE marketplace = ?
                  AND identificador = ?
                """,
                (marketplace, identificador),
            ).fetchone()

            if existente is not None and str(existente["chave_canonica"]) != chave_canonica:
                return "conflito_anuncio"

            produto_existente = conexao.execute(
                """
                SELECT chave_canonica
                FROM produtos_canonicos
                WHERE chave_canonica = ?
                """,
                (chave_canonica,),
            ).fetchone()

            conexao.execute(
                """
                INSERT INTO produtos_canonicos (
                    chave_canonica,
                    nome_canonico,
                    categoria,
                    marca,
                    modelo,
                    confianca,
                    criado_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (chave_canonica)
                DO UPDATE SET
                    categoria = COALESCE(
                        produtos_canonicos.categoria,
                        excluded.categoria
                    ),
                    marca = COALESCE(
                        produtos_canonicos.marca,
                        excluded.marca
                    ),
                    modelo = COALESCE(
                        produtos_canonicos.modelo,
                        excluded.modelo
                    ),
                    confianca = MAX(
                        produtos_canonicos.confianca,
                        excluded.confianca
                    ),
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    chave_canonica,
                    nome_canonico,
                    categoria,
                    marca,
                    modelo,
                    float(confianca),
                    agora,
                    agora,
                ),
            )

            if existente is None:
                conexao.execute(
                    """
                    INSERT INTO anuncios_canonicos (
                        marketplace,
                        identificador,
                        chave_canonica,
                        id_anuncio,
                        id_produto,
                        link,
                        loja,
                        criado_em,
                        atualizado_em
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        marketplace,
                        identificador,
                        chave_canonica,
                        id_anuncio,
                        id_produto,
                        link,
                        loja,
                        agora,
                        agora,
                    ),
                )
            else:
                conexao.execute(
                    """
                    UPDATE anuncios_canonicos
                    SET
                        id_anuncio = ?,
                        id_produto = ?,
                        link = ?,
                        loja = ?,
                        atualizado_em = ?
                    WHERE marketplace = ?
                      AND identificador = ?
                    """,
                    (
                        id_anuncio,
                        id_produto,
                        link,
                        loja,
                        agora,
                        marketplace,
                        identificador,
                    ),
                )

            if produto_existente is None and existente is None:
                return "produto_e_anuncio_criados"

            if existente is None:
                return "anuncio_criado"

            return "anuncio_atualizado"

    def obter_produto(
        self,
        chave_canonica: str,
    ) -> ProdutoCatalogoCanonico | None:
        chave = str(chave_canonica or "").strip()

        if not chave:
            return None

        with self._conectar() as conexao:
            return self._obter_produto(conexao, chave)

    def obter_por_anuncio(
        self,
        *,
        marketplace: str,
        identificador: str,
    ) -> ProdutoCatalogoCanonico | None:
        marketplace_norm = str(marketplace or "").strip()
        identificador_norm = str(identificador or "").strip()

        if not marketplace_norm or not identificador_norm:
            return None

        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT chave_canonica
                FROM anuncios_canonicos
                WHERE marketplace = ?
                  AND identificador = ?
                """,
                (marketplace_norm, identificador_norm),
            ).fetchone()

            if linha is None:
                return None

            return self._obter_produto(
                conexao,
                str(linha["chave_canonica"]),
            )

    def quantidade_produtos(self) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("SELECT COUNT(*) AS total FROM produtos_canonicos").fetchone()
            return int(linha["total"])

    def quantidade_anuncios(self) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("SELECT COUNT(*) AS total FROM anuncios_canonicos").fetchone()
            return int(linha["total"])

    def _obter_produto(
        self,
        conexao: sqlite3.Connection,
        chave_canonica: str,
    ) -> ProdutoCatalogoCanonico | None:
        produto = conexao.execute(
            """
            SELECT *
            FROM produtos_canonicos
            WHERE chave_canonica = ?
            """,
            (chave_canonica,),
        ).fetchone()

        if produto is None:
            return None

        anuncios_linhas = conexao.execute(
            """
            SELECT *
            FROM anuncios_canonicos
            WHERE chave_canonica = ?
            ORDER BY marketplace, identificador
            """,
            (chave_canonica,),
        ).fetchall()

        anuncios = tuple(
            AnuncioCatalogoCanonico(
                marketplace=str(linha["marketplace"]),
                identificador=str(linha["identificador"]),
                chave_canonica=str(linha["chave_canonica"]),
                id_anuncio=linha["id_anuncio"],
                id_produto=linha["id_produto"],
                link=str(linha["link"]),
                loja=linha["loja"],
                criado_em=str(linha["criado_em"]),
                atualizado_em=str(linha["atualizado_em"]),
            )
            for linha in anuncios_linhas
        )

        return ProdutoCatalogoCanonico(
            chave_canonica=str(produto["chave_canonica"]),
            nome_canonico=str(produto["nome_canonico"]),
            categoria=produto["categoria"],
            marca=produto["marca"],
            modelo=produto["modelo"],
            confianca=float(produto["confianca"]),
            criado_em=str(produto["criado_em"]),
            atualizado_em=str(produto["atualizado_em"]),
            anuncios=anuncios,
        )
