# 63.8738, -149.7525

from __future__ import annotations

import sqlite3
from pathlib import Path


class LinksAfiliadosAwinRepository:
    """Cache persistente dos short links oficiais gerados pela Awin."""

    def __init__(
        self,
        caminho_arquivo: str | Path = "database/links_afiliados_awin.sqlite3",
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)
        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._criar_estrutura()

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_arquivo,
            timeout=15,
        )
        conexao.execute("PRAGMA journal_mode=WAL")
        conexao.execute("PRAGMA synchronous=NORMAL")
        return conexao

    def _criar_estrutura(self) -> None:
        with self._conectar() as conexao:
            conexao.execute("""
                CREATE TABLE IF NOT EXISTS links_awin (
                    chave TEXT PRIMARY KEY,
                    short_url TEXT NOT NULL,
                    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """)

    def obter(
        self,
        chave: str,
    ) -> str | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT short_url
                FROM links_awin
                WHERE chave = ?
                """,
                (chave,),
            ).fetchone()

        if linha is None:
            return None

        valor = str(linha[0]).strip()

        return valor or None

    def salvar(
        self,
        chave: str,
        short_url: str,
    ) -> None:
        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO links_awin (
                    chave,
                    short_url
                )
                VALUES (?, ?)
                ON CONFLICT(chave) DO UPDATE SET
                    short_url = excluded.short_url,
                    atualizado_em = CURRENT_TIMESTAMP
                """,
                (
                    chave,
                    short_url,
                ),
            )
