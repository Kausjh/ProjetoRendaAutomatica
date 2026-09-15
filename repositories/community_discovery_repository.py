from __future__ import annotations

import sqlite3
from pathlib import Path

from models.community_discovery import DescobertaComunitaria


class CommunityDiscoveryRepository:
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
                CREATE TABLE IF NOT EXISTS community_discoveries (
                    id TEXT PRIMARY KEY,
                    conta_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    url_normalizada TEXT NOT NULL,
                    url_hash TEXT NOT NULL,
                    marketplace TEXT,
                    status TEXT NOT NULL
                        CHECK (
                            status IN (
                                'received',
                                'processing',
                                'retry',
                                'approved',
                                'rejected'
                            )
                        ),
                    tentativas INTEGER NOT NULL DEFAULT 0
                        CHECK (tentativas >= 0),
                    disponivel_em TEXT NOT NULL,
                    processando_desde TEXT,
                    motivo_status TEXT,
                    canonical_key TEXT,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    FOREIGN KEY (conta_id)
                        REFERENCES contas_usuario(id)
                        ON DELETE CASCADE,
                    UNIQUE (conta_id, url_hash)
                );

                CREATE INDEX IF NOT EXISTS idx_community_discoveries_account
                    ON community_discoveries(conta_id, criado_em DESC);

                CREATE INDEX IF NOT EXISTS idx_community_discoveries_status
                    ON community_discoveries(status, disponivel_em);
            """)

    @staticmethod
    def _da_linha(linha: sqlite3.Row) -> DescobertaComunitaria:
        return DescobertaComunitaria(
            id=str(linha["id"]),
            conta_id=str(linha["conta_id"]),
            url=str(linha["url"]),
            url_normalizada=str(linha["url_normalizada"]),
            marketplace=(str(linha["marketplace"]) if linha["marketplace"] is not None else None),
            status=str(linha["status"]),
            tentativas=int(linha["tentativas"]),
            disponivel_em=str(linha["disponivel_em"]),
            processando_desde=(
                str(linha["processando_desde"]) if linha["processando_desde"] is not None else None
            ),
            motivo_status=(
                str(linha["motivo_status"]) if linha["motivo_status"] is not None else None
            ),
            canonical_key=(
                str(linha["canonical_key"]) if linha["canonical_key"] is not None else None
            ),
            criado_em=str(linha["criado_em"]),
            atualizado_em=str(linha["atualizado_em"]),
        )

    def obter_por_conta_hash(
        self,
        *,
        conta_id: str,
        url_hash: str,
    ) -> DescobertaComunitaria | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT *
                FROM community_discoveries
                WHERE conta_id = ?
                  AND url_hash = ?
                """,
                (conta_id, url_hash),
            ).fetchone()

        return self._da_linha(linha) if linha is not None else None

    def registrar(
        self,
        *,
        descoberta_id: str,
        conta_id: str,
        url: str,
        url_normalizada: str,
        url_hash: str,
        marketplace: str | None,
        agora: str,
    ) -> tuple[DescobertaComunitaria, bool]:
        try:
            with self._conectar() as conexao:
                conexao.execute(
                    """
                    INSERT INTO community_discoveries (
                        id,
                        conta_id,
                        url,
                        url_normalizada,
                        url_hash,
                        marketplace,
                        status,
                        tentativas,
                        disponivel_em,
                        processando_desde,
                        motivo_status,
                        canonical_key,
                        criado_em,
                        atualizado_em
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'received', 0, ?, NULL, NULL, NULL, ?, ?)
                    """,
                    (
                        descoberta_id,
                        conta_id,
                        url,
                        url_normalizada,
                        url_hash,
                        marketplace,
                        agora,
                        agora,
                        agora,
                    ),
                )
            criada = True
        except sqlite3.IntegrityError as erro:
            existente = self.obter_por_conta_hash(
                conta_id=conta_id,
                url_hash=url_hash,
            )
            if existente is None:
                raise erro
            return existente, False

        item = self.obter_por_id(descoberta_id)
        if item is None:
            raise RuntimeError("Descoberta comunitaria desapareceu apos persistencia.")
        return item, criada

    def obter_por_id(
        self,
        descoberta_id: str,
    ) -> DescobertaComunitaria | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT *
                FROM community_discoveries
                WHERE id = ?
                """,
                (str(descoberta_id or "").strip(),),
            ).fetchone()

        return self._da_linha(linha) if linha is not None else None

    def listar_por_conta(
        self,
        conta_id: str,
        *,
        limite: int = 50,
    ) -> list[DescobertaComunitaria]:
        limite_seguro = max(1, min(int(limite), 100))

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM community_discoveries
                WHERE conta_id = ?
                ORDER BY criado_em DESC, id DESC
                LIMIT ?
                """,
                (str(conta_id or "").strip(), limite_seguro),
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]

    def contar_recentes(
        self,
        *,
        conta_id: str,
        criado_desde: str,
    ) -> int:
        with self._conectar() as conexao:
            return int(
                conexao.execute(
                    """
                    SELECT COUNT(*)
                    FROM community_discoveries
                    WHERE conta_id = ?
                      AND criado_em >= ?
                    """,
                    (str(conta_id or "").strip(), criado_desde),
                ).fetchone()[0]
            )

    def listar_pendentes(
        self,
        *,
        disponivel_ate: str,
        limite: int = 50,
    ) -> list[DescobertaComunitaria]:
        limite_seguro = max(1, min(int(limite), 200))

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM community_discoveries
                WHERE status IN ('received', 'retry')
                  AND disponivel_em <= ?
                ORDER BY disponivel_em ASC, criado_em ASC, id ASC
                LIMIT ?
                """,
                (disponivel_ate, limite_seguro),
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]
