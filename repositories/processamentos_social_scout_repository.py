# 63.8738, -149.7525

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from models.mensagem_social_scout import (
    MensagemSocialScout,
)


class ProcessamentosSocialScoutRepository:
    """
    Estado persistente do processamento das mensagens
    capturadas pelo Social Scout.

    O conteudo bruto continua em MensagensSocialScoutRepository.

    Esta tabela guarda somente:
    - identidade da mensagem;
    - versao do processador;
    - fingerprint;
    - status;
    - motivo.

    Nenhuma identidade do autor da mensagem e armazenada.
    """

    def __init__(
        self,
        caminho_arquivo: str | Path = ("database/social_scout.sqlite3"),
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

    @contextmanager
    def _abrir_conexao(
        self,
    ):
        conexao = self._conectar()

        try:
            with conexao:
                yield conexao

        finally:
            conexao.close()

    def _criar_estrutura(
        self,
    ) -> None:
        with self._abrir_conexao() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS
                processamentos_social_scout (
                    fonte TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    message_id INTEGER NOT NULL,

                    versao_processador TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,

                    status TEXT NOT NULL,
                    motivo TEXT NOT NULL DEFAULT '',

                    criado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    atualizado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    PRIMARY KEY (
                        fonte,
                        chat_id,
                        message_id,
                        versao_processador
                    )
                );
                """)

    def obter(
        self,
        mensagem: MensagemSocialScout,
        versao_processador: str,
    ) -> dict | None:
        with self._abrir_conexao() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    fingerprint,
                    status,
                    motivo,
                    atualizado_em
                FROM processamentos_social_scout
                WHERE fonte = ?
                  AND chat_id = ?
                  AND message_id = ?
                  AND versao_processador = ?
                """,
                (
                    mensagem.fonte,
                    mensagem.chat_id,
                    mensagem.message_id,
                    str(versao_processador),
                ),
            ).fetchone()

        if linha is None:
            return None

        return {
            "fingerprint": str(linha["fingerprint"]),
            "status": str(linha["status"]),
            "motivo": str(linha["motivo"]),
            "atualizado_em": str(linha["atualizado_em"]),
        }

    def esta_processada(
        self,
        mensagem: MensagemSocialScout,
        versao_processador: str,
        fingerprint: str,
    ) -> bool:
        estado = self.obter(
            mensagem,
            versao_processador,
        )

        if estado is None:
            return False

        return estado["fingerprint"] == str(fingerprint)

    def salvar(
        self,
        mensagem: MensagemSocialScout,
        versao_processador: str,
        fingerprint: str,
        status: str,
        motivo: str = "",
    ) -> None:
        with self._abrir_conexao() as conexao:
            conexao.execute(
                """
                INSERT INTO processamentos_social_scout (
                    fonte,
                    chat_id,
                    message_id,
                    versao_processador,
                    fingerprint,
                    status,
                    motivo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT (
                    fonte,
                    chat_id,
                    message_id,
                    versao_processador
                )
                DO UPDATE SET
                    fingerprint = excluded.fingerprint,
                    status = excluded.status,
                    motivo = excluded.motivo,
                    atualizado_em = CURRENT_TIMESTAMP
                """,
                (
                    mensagem.fonte,
                    mensagem.chat_id,
                    mensagem.message_id,
                    str(versao_processador),
                    str(fingerprint),
                    str(status),
                    str(motivo),
                ),
            )

    def quantidade(
        self,
    ) -> int:
        with self._abrir_conexao() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(*) AS total
                FROM processamentos_social_scout
                """).fetchone()

        return int(linha["total"])
