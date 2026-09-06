# 63.8738, -149.7525

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from models.sinal_scout import SinalScout


class SinaisScoutRepository:

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
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS sinais_scout (
                    fonte TEXT NOT NULL,
                    id_externo TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (
                        fonte,
                        id_externo
                    )
                );

                CREATE TABLE IF NOT EXISTS estado_scout (
                    chave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );
                """)

    def salvar(
        self,
        sinal: SinalScout,
    ) -> str:
        dados = asdict(sinal)

        dados["regioes"] = list(sinal.regioes)

        payload = json.dumps(
            dados,
            ensure_ascii=False,
            sort_keys=True,
        )

        with self._conectar() as conexao:
            existente = conexao.execute(
                """
                SELECT payload_json
                FROM sinais_scout
                WHERE fonte = ?
                  AND id_externo = ?
                """,
                (
                    sinal.fonte,
                    sinal.id_externo,
                ),
            ).fetchone()

            if existente is None:
                conexao.execute(
                    """
                    INSERT INTO sinais_scout (
                        fonte,
                        id_externo,
                        payload_json
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        sinal.fonte,
                        sinal.id_externo,
                        payload,
                    ),
                )

                return "novo"

            if str(existente["payload_json"]) == payload:
                return "inalterado"

            conexao.execute(
                """
                UPDATE sinais_scout
                SET payload_json = ?,
                    atualizado_em =
                        CURRENT_TIMESTAMP
                WHERE fonte = ?
                  AND id_externo = ?
                """,
                (
                    payload,
                    sinal.fonte,
                    sinal.id_externo,
                ),
            )

        return "atualizado"

    def quantidade(
        self,
    ) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(*) AS total
                FROM sinais_scout
                """).fetchone()

        return int(linha["total"])

    def obter_estado(
        self,
        chave: str,
    ) -> str | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT valor
                FROM estado_scout
                WHERE chave = ?
                """,
                (chave,),
            ).fetchone()

        if linha is None:
            return None

        return str(linha["valor"])

    def salvar_estado(
        self,
        chave: str,
        valor: str,
    ) -> None:
        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO estado_scout (
                    chave,
                    valor
                )
                VALUES (?, ?)
                ON CONFLICT(chave) DO UPDATE SET
                    valor = excluded.valor,
                    atualizado_em =
                        CURRENT_TIMESTAMP
                """,
                (
                    chave,
                    valor,
                ),
            )
