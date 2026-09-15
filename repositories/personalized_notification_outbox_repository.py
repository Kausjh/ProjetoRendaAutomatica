from __future__ import annotations

import sqlite3
from pathlib import Path

from models.personalized_notification_outbox import (
    ItemOutboxNotificacaoPersonalizada,
)


class PersonalizedNotificationOutboxRepository:
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
                CREATE TABLE IF NOT EXISTS personalized_notification_outbox (
                    id TEXT PRIMARY KEY,
                    match_id TEXT NOT NULL,
                    conta_id TEXT NOT NULL,
                    canonical_key TEXT NOT NULL,
                    canal TEXT NOT NULL
                        CHECK (canal IN ('push')),
                    status TEXT NOT NULL
                        CHECK (
                            status IN (
                                'pending',
                                'processing',
                                'delivered',
                                'failed'
                            )
                        ),
                    tentativas INTEGER NOT NULL DEFAULT 0
                        CHECK (tentativas >= 0),
                    disponivel_em TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    entregue_em TEXT,
                    ultimo_erro TEXT,
                    FOREIGN KEY (match_id)
                        REFERENCES personalized_alert_matches(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (conta_id)
                        REFERENCES contas_usuario(id)
                        ON DELETE CASCADE,
                    UNIQUE (match_id, canal)
                );

                CREATE INDEX IF NOT EXISTS idx_notification_outbox_status
                    ON personalized_notification_outbox(
                        status,
                        disponivel_em
                    );

                CREATE INDEX IF NOT EXISTS idx_notification_outbox_conta
                    ON personalized_notification_outbox(conta_id);
                """)

    @staticmethod
    def _da_linha(
        linha: sqlite3.Row,
    ) -> ItemOutboxNotificacaoPersonalizada:
        return ItemOutboxNotificacaoPersonalizada(
            id=str(linha["id"]),
            match_id=str(linha["match_id"]),
            conta_id=str(linha["conta_id"]),
            canonical_key=str(linha["canonical_key"]),
            canal=str(linha["canal"]),
            status=str(linha["status"]),
            tentativas=int(linha["tentativas"]),
            disponivel_em=str(linha["disponivel_em"]),
            criado_em=str(linha["criado_em"]),
            atualizado_em=str(linha["atualizado_em"]),
            entregue_em=(str(linha["entregue_em"]) if linha["entregue_em"] is not None else None),
            ultimo_erro=(str(linha["ultimo_erro"]) if linha["ultimo_erro"] is not None else None),
        )

    def listar_matches_sem_outbox(
        self,
        *,
        limite: int = 100,
    ) -> list[tuple[str, str, str]]:
        limite_seguro = max(1, min(int(limite), 500))

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    pam.id AS match_id,
                    pam.conta_id,
                    pam.canonical_key
                FROM personalized_alert_matches AS pam
                LEFT JOIN personalized_notification_outbox AS pno
                  ON pno.match_id = pam.id
                 AND pno.canal = 'push'
                WHERE pno.id IS NULL
                ORDER BY pam.criado_em ASC, pam.id ASC
                LIMIT ?
                """,
                (limite_seguro,),
            ).fetchall()

        return [
            (
                str(linha["match_id"]),
                str(linha["conta_id"]),
                str(linha["canonical_key"]),
            )
            for linha in linhas
        ]

    def enfileirar(
        self,
        *,
        outbox_id: str,
        match_id: str,
        conta_id: str,
        canonical_key: str,
        disponivel_em: str,
        agora: str,
    ) -> tuple[ItemOutboxNotificacaoPersonalizada, bool]:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT OR IGNORE INTO personalized_notification_outbox (
                    id,
                    match_id,
                    conta_id,
                    canonical_key,
                    canal,
                    status,
                    tentativas,
                    disponivel_em,
                    criado_em,
                    atualizado_em,
                    entregue_em,
                    ultimo_erro
                )
                VALUES (?, ?, ?, ?, 'push', 'pending', 0, ?, ?, ?, NULL, NULL)
                """,
                (
                    outbox_id,
                    match_id,
                    conta_id,
                    canonical_key,
                    disponivel_em,
                    agora,
                    agora,
                ),
            )
            criado = cursor.rowcount == 1

        item = self.obter_por_match(
            match_id=match_id,
            canal="push",
        )

        if item is None:
            raise RuntimeError("Falha ao persistir item da outbox.")

        return item, criado

    def obter_por_match(
        self,
        *,
        match_id: str,
        canal: str,
    ) -> ItemOutboxNotificacaoPersonalizada | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    id,
                    match_id,
                    conta_id,
                    canonical_key,
                    canal,
                    status,
                    tentativas,
                    disponivel_em,
                    criado_em,
                    atualizado_em,
                    entregue_em,
                    ultimo_erro
                FROM personalized_notification_outbox
                WHERE match_id = ?
                  AND canal = ?
                """,
                (match_id, canal),
            ).fetchone()

        if linha is None:
            return None

        return self._da_linha(linha)

    def obter_por_id(
        self,
        outbox_id: str,
    ) -> ItemOutboxNotificacaoPersonalizada | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    id,
                    match_id,
                    conta_id,
                    canonical_key,
                    canal,
                    status,
                    tentativas,
                    disponivel_em,
                    criado_em,
                    atualizado_em,
                    entregue_em,
                    ultimo_erro
                FROM personalized_notification_outbox
                WHERE id = ?
                """,
                (outbox_id,),
            ).fetchone()

        if linha is None:
            return None

        return self._da_linha(linha)

    def listar_disponiveis(
        self,
        *,
        agora: str,
        limite: int = 25,
    ) -> list[ItemOutboxNotificacaoPersonalizada]:
        limite_seguro = max(1, min(int(limite), 100))

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    match_id,
                    conta_id,
                    canonical_key,
                    canal,
                    status,
                    tentativas,
                    disponivel_em,
                    criado_em,
                    atualizado_em,
                    entregue_em,
                    ultimo_erro
                FROM personalized_notification_outbox
                WHERE status = 'pending'
                  AND disponivel_em <= ?
                ORDER BY disponivel_em ASC, criado_em ASC, id ASC
                LIMIT ?
                """,
                (agora, limite_seguro),
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]

    def reservar(
        self,
        *,
        outbox_id: str,
        agora: str,
    ) -> bool:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE personalized_notification_outbox
                SET
                    status = 'processing',
                    tentativas = tentativas + 1,
                    atualizado_em = ?,
                    ultimo_erro = NULL
                WHERE id = ?
                  AND status = 'pending'
                  AND disponivel_em <= ?
                """,
                (agora, outbox_id, agora),
            )

        return cursor.rowcount == 1

    def marcar_entregue(
        self,
        *,
        outbox_id: str,
        agora: str,
    ) -> bool:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE personalized_notification_outbox
                SET
                    status = 'delivered',
                    entregue_em = ?,
                    atualizado_em = ?,
                    ultimo_erro = NULL
                WHERE id = ?
                  AND status = 'processing'
                """,
                (agora, agora, outbox_id),
            )

        return cursor.rowcount == 1

    def marcar_retry(
        self,
        *,
        outbox_id: str,
        disponivel_em: str,
        erro: str,
        agora: str,
    ) -> bool:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE personalized_notification_outbox
                SET
                    status = 'pending',
                    disponivel_em = ?,
                    atualizado_em = ?,
                    ultimo_erro = ?,
                    entregue_em = NULL
                WHERE id = ?
                  AND status = 'processing'
                """,
                (
                    disponivel_em,
                    agora,
                    erro,
                    outbox_id,
                ),
            )

        return cursor.rowcount == 1

    def marcar_falha_terminal(
        self,
        *,
        outbox_id: str,
        erro: str,
        agora: str,
    ) -> bool:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE personalized_notification_outbox
                SET
                    status = 'failed',
                    atualizado_em = ?,
                    ultimo_erro = ?,
                    entregue_em = NULL
                WHERE id = ?
                  AND status = 'processing'
                """,
                (
                    agora,
                    erro,
                    outbox_id,
                ),
            )

        return cursor.rowcount == 1

    def listar_processando_ate(
        self,
        *,
        atualizado_ate: str,
        limite: int = 100,
    ) -> list[ItemOutboxNotificacaoPersonalizada]:
        corte = str(atualizado_ate or "").strip()
        if not corte:
            raise ValueError("Corte de processing stale nao pode ser vazio.")

        limite_seguro = max(1, min(int(limite), 500))

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    match_id,
                    conta_id,
                    canonical_key,
                    canal,
                    status,
                    tentativas,
                    disponivel_em,
                    criado_em,
                    atualizado_em,
                    entregue_em,
                    ultimo_erro
                FROM personalized_notification_outbox
                WHERE status = 'processing'
                  AND atualizado_em <= ?
                ORDER BY atualizado_em ASC, criado_em ASC, id ASC
                LIMIT ?
                """,
                (corte, limite_seguro),
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]

    def listar_por_conta(
        self,
        conta_id: str,
        *,
        limite: int = 100,
    ) -> list[ItemOutboxNotificacaoPersonalizada]:
        limite_seguro = max(1, min(int(limite), 500))

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    match_id,
                    conta_id,
                    canonical_key,
                    canal,
                    status,
                    tentativas,
                    disponivel_em,
                    criado_em,
                    atualizado_em,
                    entregue_em,
                    ultimo_erro
                FROM personalized_notification_outbox
                WHERE conta_id = ?
                ORDER BY criado_em DESC, id DESC
                LIMIT ?
                """,
                (conta_id, limite_seguro),
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]
