# 63.8738, -149.7525

from __future__ import annotations

import sqlite3
from pathlib import Path

from models.resolucao_scout import ResolucaoScout


class ResolucoesScoutRepository:
    """Persistencia local das resolucoes produzidas pelo Radar Scout."""

    def __init__(
        self,
        caminho_arquivo: str | Path = ("database/sinais_scout.sqlite3"),
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)

        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._criar_estrutura()

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_arquivo,
            timeout=15,
        )

        conexao.row_factory = sqlite3.Row

        conexao.execute("PRAGMA journal_mode=WAL")

        conexao.execute("PRAGMA synchronous=NORMAL")

        return conexao

    def _criar_estrutura(
        self,
    ) -> None:
        with self._conectar() as conexao:
            conexao.execute("""
                CREATE TABLE IF NOT EXISTS
                resolucoes_scout (
                    fonte TEXT NOT NULL,
                    id_externo TEXT NOT NULL,
                    status TEXT NOT NULL,
                    marketplace TEXT,
                    tipo_destino TEXT,
                    url_destino TEXT,
                    id_produto TEXT,
                    http_status INTEGER,
                    motivo TEXT NOT NULL
                        DEFAULT '',
                    criado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (
                        fonte,
                        id_externo
                    )
                )
                """)

    def salvar(
        self,
        resolucao: ResolucaoScout,
    ) -> None:
        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO resolucoes_scout (
                    fonte,
                    id_externo,
                    status,
                    marketplace,
                    tipo_destino,
                    url_destino,
                    id_produto,
                    http_status,
                    motivo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(
                    fonte,
                    id_externo
                )
                DO UPDATE SET
                    status = excluded.status,
                    marketplace =
                        excluded.marketplace,
                    tipo_destino =
                        excluded.tipo_destino,
                    url_destino =
                        excluded.url_destino,
                    id_produto =
                        excluded.id_produto,
                    http_status =
                        excluded.http_status,
                    motivo =
                        excluded.motivo,
                    atualizado_em =
                        CURRENT_TIMESTAMP
                """,
                (
                    resolucao.fonte,
                    resolucao.id_externo,
                    resolucao.status,
                    resolucao.marketplace,
                    resolucao.tipo_destino,
                    resolucao.url_destino,
                    resolucao.id_produto,
                    resolucao.http_status,
                    resolucao.motivo,
                ),
            )

    def obter(
        self,
        fonte: str,
        id_externo: str,
    ) -> ResolucaoScout | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    fonte,
                    id_externo,
                    status,
                    marketplace,
                    tipo_destino,
                    url_destino,
                    id_produto,
                    http_status,
                    motivo
                FROM resolucoes_scout
                WHERE fonte = ?
                  AND id_externo = ?
                """,
                (
                    fonte,
                    id_externo,
                ),
            ).fetchone()

        if linha is None:
            return None

        return ResolucaoScout(
            fonte=str(linha["fonte"]),
            id_externo=str(linha["id_externo"]),
            status=str(linha["status"]),
            marketplace=linha["marketplace"],
            tipo_destino=linha["tipo_destino"],
            url_destino=linha["url_destino"],
            id_produto=linha["id_produto"],
            http_status=linha["http_status"],
            motivo=str(linha["motivo"] or ""),
        )

    def quantidade(
        self,
    ) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(*) AS total
                FROM resolucoes_scout
                """).fetchone()

        return int(linha["total"])

    def estatisticas_status(
        self,
    ) -> dict[str, int]:
        with self._conectar() as conexao:
            linhas = conexao.execute("""
                SELECT
                    status,
                    COUNT(*) AS total
                FROM resolucoes_scout
                GROUP BY status
                ORDER BY status
                """).fetchall()

        return {str(linha["status"]): int(linha["total"]) for linha in linhas}

    def estatisticas_marketplace(
        self,
    ) -> dict[str, int]:
        with self._conectar() as conexao:
            linhas = conexao.execute("""
                SELECT
                    COALESCE(
                        marketplace,
                        'nao_identificado'
                    ) AS marketplace,
                    COUNT(*) AS total
                FROM resolucoes_scout
                GROUP BY marketplace
                ORDER BY marketplace
                """).fetchall()

        return {str(linha["marketplace"]): int(linha["total"]) for linha in linhas}
