from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path

from models.personalized_alert_match import (
    CorrespondenciaAlertaPersonalizado,
)


class PersonalizedAlertMatchRepository:
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
                CREATE TABLE IF NOT EXISTS personalized_alert_matches (
                    id TEXT PRIMARY KEY,
                    evento_alerta_id TEXT NOT NULL,
                    watchlist_id TEXT NOT NULL,
                    conta_id TEXT NOT NULL,
                    canonical_key TEXT NOT NULL,
                    tipo_evento TEXT NOT NULL,
                    preco_atual_centavos INTEGER NOT NULL,
                    marketplace TEXT,
                    motivos_json TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (watchlist_id)
                        REFERENCES watchlist_usuario(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (conta_id)
                        REFERENCES contas_usuario(id)
                        ON DELETE CASCADE,
                    UNIQUE (evento_alerta_id, watchlist_id),
                    CHECK (preco_atual_centavos > 0)
                );

                CREATE INDEX IF NOT EXISTS idx_personalized_alert_matches_conta
                    ON personalized_alert_matches(conta_id);

                CREATE INDEX IF NOT EXISTS idx_personalized_alert_matches_evento
                    ON personalized_alert_matches(evento_alerta_id);

                CREATE INDEX IF NOT EXISTS idx_personalized_alert_matches_canonical
                    ON personalized_alert_matches(canonical_key);
                """)

    @staticmethod
    def _da_linha(
        linha: sqlite3.Row,
    ) -> CorrespondenciaAlertaPersonalizado:
        return CorrespondenciaAlertaPersonalizado(
            id=str(linha["id"]),
            evento_alerta_id=str(linha["evento_alerta_id"]),
            watchlist_id=str(linha["watchlist_id"]),
            conta_id=str(linha["conta_id"]),
            canonical_key=str(linha["canonical_key"]),
            tipo_evento=str(linha["tipo_evento"]),
            preco_atual=(Decimal(int(linha["preco_atual_centavos"])) / Decimal(100)),
            marketplace=(str(linha["marketplace"]) if linha["marketplace"] is not None else None),
            motivos=tuple(json.loads(str(linha["motivos_json"]))),
            criado_em=str(linha["criado_em"]),
        )

    def salvar_correspondencia(
        self,
        *,
        match_id: str,
        evento_alerta_id: str,
        watchlist_id: str,
        conta_id: str,
        canonical_key: str,
        tipo_evento: str,
        preco_atual_centavos: int,
        marketplace: str | None,
        motivos: tuple[str, ...],
        criado_em: str,
    ) -> tuple[CorrespondenciaAlertaPersonalizado, bool]:
        motivos_json = json.dumps(
            list(motivos),
            ensure_ascii=False,
            separators=(",", ":"),
        )

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT OR IGNORE INTO personalized_alert_matches (
                    id,
                    evento_alerta_id,
                    watchlist_id,
                    conta_id,
                    canonical_key,
                    tipo_evento,
                    preco_atual_centavos,
                    marketplace,
                    motivos_json,
                    criado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    evento_alerta_id,
                    watchlist_id,
                    conta_id,
                    canonical_key,
                    tipo_evento,
                    preco_atual_centavos,
                    marketplace,
                    motivos_json,
                    criado_em,
                ),
            )
            criado = cursor.rowcount == 1

        match = self.obter_por_evento_watchlist(
            evento_alerta_id=evento_alerta_id,
            watchlist_id=watchlist_id,
        )

        if match is None:
            raise RuntimeError("Falha ao persistir correspondencia personalizada.")

        return match, criado

    def obter_por_id(
        self,
        match_id: str,
    ) -> CorrespondenciaAlertaPersonalizado | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    id,
                    evento_alerta_id,
                    watchlist_id,
                    conta_id,
                    canonical_key,
                    tipo_evento,
                    preco_atual_centavos,
                    marketplace,
                    motivos_json,
                    criado_em
                FROM personalized_alert_matches
                WHERE id = ?
                """,
                (str(match_id or "").strip(),),
            ).fetchone()

        return self._da_linha(linha) if linha is not None else None

    def obter_por_evento_watchlist(
        self,
        *,
        evento_alerta_id: str,
        watchlist_id: str,
    ) -> CorrespondenciaAlertaPersonalizado | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    id,
                    evento_alerta_id,
                    watchlist_id,
                    conta_id,
                    canonical_key,
                    tipo_evento,
                    preco_atual_centavos,
                    marketplace,
                    motivos_json,
                    criado_em
                FROM personalized_alert_matches
                WHERE evento_alerta_id = ?
                  AND watchlist_id = ?
                """,
                (evento_alerta_id, watchlist_id),
            ).fetchone()

        if linha is None:
            return None

        return self._da_linha(linha)

    def listar_por_conta(
        self,
        conta_id: str,
        *,
        limite: int = 100,
    ) -> list[CorrespondenciaAlertaPersonalizado]:
        limite_seguro = max(1, min(int(limite), 500))

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    evento_alerta_id,
                    watchlist_id,
                    conta_id,
                    canonical_key,
                    tipo_evento,
                    preco_atual_centavos,
                    marketplace,
                    motivos_json,
                    criado_em
                FROM personalized_alert_matches
                WHERE conta_id = ?
                ORDER BY criado_em DESC, id DESC
                LIMIT ?
                """,
                (conta_id, limite_seguro),
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]
