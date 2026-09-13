from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path

from models.user_personalization import (
    ItemWatchlistUsuario,
    PreferenciasUsuario,
)


class UserPersonalizationRepository:
    def __init__(self, caminho_banco: str | Path) -> None:
        self.caminho_banco = Path(caminho_banco)
        self.caminho_banco.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar()

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self.caminho_banco)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        return conexao

    def _inicializar(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS preferencias_usuario (
                    conta_id TEXT PRIMARY KEY,
                    notificacoes_preco_habilitadas INTEGER NOT NULL DEFAULT 1
                        CHECK (notificacoes_preco_habilitadas IN (0, 1)),
                    marketplaces_preferidos_json TEXT NOT NULL DEFAULT '[]',
                    atualizado_em TEXT NOT NULL,
                    FOREIGN KEY (conta_id)
                        REFERENCES contas_usuario(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS watchlist_usuario (
                    id TEXT PRIMARY KEY,
                    conta_id TEXT NOT NULL,
                    canonical_key TEXT NOT NULL,
                    preco_alvo_centavos INTEGER,
                    notificar_queda_preco INTEGER NOT NULL DEFAULT 1
                        CHECK (notificar_queda_preco IN (0, 1)),
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    FOREIGN KEY (conta_id)
                        REFERENCES contas_usuario(id)
                        ON DELETE CASCADE,
                    UNIQUE (conta_id, canonical_key),
                    CHECK (
                        preco_alvo_centavos IS NULL
                        OR preco_alvo_centavos > 0
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_watchlist_usuario_conta
                    ON watchlist_usuario(conta_id);

                CREATE INDEX IF NOT EXISTS idx_watchlist_usuario_canonical
                    ON watchlist_usuario(canonical_key);
                """)

    @staticmethod
    def _preco_de_centavos(valor: int | None) -> Decimal | None:
        if valor is None:
            return None
        return Decimal(valor) / Decimal(100)

    @staticmethod
    def _preferencias_da_linha(
        linha: sqlite3.Row,
    ) -> PreferenciasUsuario:
        marketplaces = tuple(json.loads(str(linha["marketplaces_preferidos_json"])))
        return PreferenciasUsuario(
            conta_id=str(linha["conta_id"]),
            notificacoes_preco_habilitadas=bool(linha["notificacoes_preco_habilitadas"]),
            marketplaces_preferidos=marketplaces,
            atualizado_em=str(linha["atualizado_em"]),
        )

    @classmethod
    def _watchlist_da_linha(
        cls,
        linha: sqlite3.Row,
    ) -> ItemWatchlistUsuario:
        return ItemWatchlistUsuario(
            id=str(linha["id"]),
            conta_id=str(linha["conta_id"]),
            canonical_key=str(linha["canonical_key"]),
            preco_alvo=cls._preco_de_centavos(
                int(linha["preco_alvo_centavos"])
                if linha["preco_alvo_centavos"] is not None
                else None
            ),
            notificar_queda_preco=bool(linha["notificar_queda_preco"]),
            criado_em=str(linha["criado_em"]),
            atualizado_em=str(linha["atualizado_em"]),
        )

    def salvar_preferencias(
        self,
        *,
        conta_id: str,
        notificacoes_preco_habilitadas: bool,
        marketplaces_preferidos: tuple[str, ...],
        atualizado_em: str,
    ) -> PreferenciasUsuario:
        marketplaces_json = json.dumps(
            list(marketplaces_preferidos),
            ensure_ascii=False,
            separators=(",", ":"),
        )

        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO preferencias_usuario (
                    conta_id,
                    notificacoes_preco_habilitadas,
                    marketplaces_preferidos_json,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(conta_id)
                DO UPDATE SET
                    notificacoes_preco_habilitadas =
                        excluded.notificacoes_preco_habilitadas,
                    marketplaces_preferidos_json =
                        excluded.marketplaces_preferidos_json,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    conta_id,
                    int(notificacoes_preco_habilitadas),
                    marketplaces_json,
                    atualizado_em,
                ),
            )

        preferencias = self.obter_preferencias(conta_id)
        if preferencias is None:
            raise RuntimeError("Falha ao persistir preferencias.")
        return preferencias

    def obter_preferencias(
        self,
        conta_id: str,
    ) -> PreferenciasUsuario | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    conta_id,
                    notificacoes_preco_habilitadas,
                    marketplaces_preferidos_json,
                    atualizado_em
                FROM preferencias_usuario
                WHERE conta_id = ?
                """,
                (conta_id,),
            ).fetchone()

        if linha is None:
            return None

        return self._preferencias_da_linha(linha)

    def salvar_item_watchlist(
        self,
        *,
        item_id: str,
        conta_id: str,
        canonical_key: str,
        preco_alvo_centavos: int | None,
        notificar_queda_preco: bool,
        criado_em: str,
        atualizado_em: str,
    ) -> ItemWatchlistUsuario:
        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO watchlist_usuario (
                    id,
                    conta_id,
                    canonical_key,
                    preco_alvo_centavos,
                    notificar_queda_preco,
                    criado_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conta_id, canonical_key)
                DO UPDATE SET
                    preco_alvo_centavos =
                        excluded.preco_alvo_centavos,
                    notificar_queda_preco =
                        excluded.notificar_queda_preco,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    item_id,
                    conta_id,
                    canonical_key,
                    preco_alvo_centavos,
                    int(notificar_queda_preco),
                    criado_em,
                    atualizado_em,
                ),
            )

        item = self.obter_item_watchlist(
            conta_id=conta_id,
            canonical_key=canonical_key,
        )
        if item is None:
            raise RuntimeError("Falha ao persistir item da watchlist.")
        return item

    def obter_item_watchlist(
        self,
        *,
        conta_id: str,
        canonical_key: str,
    ) -> ItemWatchlistUsuario | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    id,
                    conta_id,
                    canonical_key,
                    preco_alvo_centavos,
                    notificar_queda_preco,
                    criado_em,
                    atualizado_em
                FROM watchlist_usuario
                WHERE conta_id = ?
                  AND canonical_key = ?
                """,
                (conta_id, canonical_key),
            ).fetchone()

        if linha is None:
            return None

        return self._watchlist_da_linha(linha)

    def listar_watchlist(
        self,
        conta_id: str,
    ) -> list[ItemWatchlistUsuario]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    conta_id,
                    canonical_key,
                    preco_alvo_centavos,
                    notificar_queda_preco,
                    criado_em,
                    atualizado_em
                FROM watchlist_usuario
                WHERE conta_id = ?
                ORDER BY criado_em ASC, id ASC
                """,
                (conta_id,),
            ).fetchall()

        return [self._watchlist_da_linha(linha) for linha in linhas]

    def remover_item_watchlist(
        self,
        *,
        conta_id: str,
        canonical_key: str,
    ) -> bool:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                DELETE FROM watchlist_usuario
                WHERE conta_id = ?
                  AND canonical_key = ?
                """,
                (conta_id, canonical_key),
            )

        return cursor.rowcount == 1

    def listar_watchlists_por_canonical_key(
        self,
        canonical_key: str,
    ) -> list[ItemWatchlistUsuario]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    conta_id,
                    canonical_key,
                    preco_alvo_centavos,
                    notificar_queda_preco,
                    criado_em,
                    atualizado_em
                FROM watchlist_usuario
                WHERE canonical_key = ?
                ORDER BY conta_id ASC, criado_em ASC, id ASC
                """,
                (canonical_key,),
            ).fetchall()

        return [self._watchlist_da_linha(linha) for linha in linhas]
