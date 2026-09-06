# 63.8738, -149.7525

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from models.mensagem_social_scout import MensagemSocialScout


class MensagensSocialScoutRepository:
    def __init__(
        self,
        caminho_arquivo: str | Path = "database/social_scout.sqlite3",
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

        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA journal_mode=WAL")
        conexao.execute("PRAGMA synchronous=NORMAL")

        return conexao

    def _criar_estrutura(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS mensagens_social_scout (
                    fonte TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    message_id INTEGER NOT NULL,

                    payload_json TEXT NOT NULL,

                    criado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    atualizado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    PRIMARY KEY (
                        fonte,
                        chat_id,
                        message_id
                    )
                );
            """)

    def salvar(
        self,
        mensagem: MensagemSocialScout,
    ) -> str:
        dados = asdict(mensagem)
        dados["links"] = list(mensagem.links)

        payload = json.dumps(
            dados,
            ensure_ascii=False,
            sort_keys=True,
        )

        with self._conectar() as conexao:
            existente = conexao.execute(
                """
                SELECT payload_json
                FROM mensagens_social_scout
                WHERE fonte = ?
                  AND chat_id = ?
                  AND message_id = ?
                """,
                (
                    mensagem.fonte,
                    mensagem.chat_id,
                    mensagem.message_id,
                ),
            ).fetchone()

            if existente is None:
                conexao.execute(
                    """
                    INSERT INTO mensagens_social_scout (
                        fonte,
                        chat_id,
                        message_id,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        mensagem.fonte,
                        mensagem.chat_id,
                        mensagem.message_id,
                        payload,
                    ),
                )

                return "novo"

            if str(existente["payload_json"]) == payload:
                return "inalterado"

            conexao.execute(
                """
                UPDATE mensagens_social_scout
                SET payload_json = ?,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE fonte = ?
                  AND chat_id = ?
                  AND message_id = ?
                """,
                (
                    payload,
                    mensagem.fonte,
                    mensagem.chat_id,
                    mensagem.message_id,
                ),
            )

        return "atualizado"

    def listar(
        self,
        limite: int | None = None,
    ) -> list[MensagemSocialScout]:
        consulta = """
            SELECT payload_json
            FROM mensagens_social_scout
            ORDER BY
                criado_em ASC,
                fonte ASC,
                chat_id ASC,
                message_id ASC
        """

        parametros: tuple = ()

        if limite is not None:
            limite = int(limite)

            if limite <= 0:
                return []

            consulta += " LIMIT ?"
            parametros = (limite,)

        with self._conectar() as conexao:
            linhas = conexao.execute(
                consulta,
                parametros,
            ).fetchall()

        mensagens: list[MensagemSocialScout] = []

        for linha in linhas:
            dados = json.loads(str(linha["payload_json"]))

            if not isinstance(dados, dict):
                raise ValueError("Payload de mensagem do Social Scout invalido.")

            links = dados.get(
                "links",
                [],
            )

            if isinstance(links, list):
                dados["links"] = tuple(links)

            elif not isinstance(links, tuple):
                dados["links"] = ()

            mensagens.append(MensagemSocialScout(**dados))

        return mensagens

    def quantidade(self) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(*) AS total
                FROM mensagens_social_scout
                """).fetchone()

        return int(linha["total"])
