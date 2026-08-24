# 63.8738, -149.7525

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class ControleAdministrativoRepository:
    def __init__(
        self,
        caminho_arquivo: str = "database/controle_administrativo.sqlite3",
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)
        self.caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS estado_operacional (
                    chave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS auditoria_administrativa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    acao TEXT NOT NULL,
                    alvo TEXT,
                    detalhes_json TEXT,
                    dispositivo TEXT,
                    resultado TEXT NOT NULL,
                    executado_em TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_auditoria_executado_em
                ON auditoria_administrativa(executado_em DESC);
                """)

    def definir_estado(
        self,
        chave: str,
        valor: str,
    ) -> None:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO estado_operacional (
                    chave,
                    valor,
                    atualizado_em
                )
                VALUES (?, ?, ?)
                ON CONFLICT(chave) DO UPDATE SET
                    valor = excluded.valor,
                    atualizado_em = excluded.atualizado_em
                """,
                (chave, valor, agora),
            )

    def obter_estado(
        self,
        chave: str,
        padrao: str | None = None,
    ) -> str | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT valor
                FROM estado_operacional
                WHERE chave = ?
                LIMIT 1
                """,
                (chave,),
            ).fetchone()

        if linha is None:
            return padrao

        return str(linha["valor"])

    def definir_booleano(
        self,
        chave: str,
        valor: bool,
    ) -> None:
        self.definir_estado(
            chave=chave,
            valor="1" if valor else "0",
        )

    def obter_booleano(
        self,
        chave: str,
        padrao: bool = False,
    ) -> bool:
        valor = self.obter_estado(chave)

        if valor is None:
            return padrao

        return valor.strip().casefold() in {
            "1",
            "true",
            "sim",
            "on",
            "yes",
        }

    def registrar_auditoria(
        self,
        acao: str,
        alvo: str | None,
        detalhes: dict[str, Any] | None,
        dispositivo: str | None,
        resultado: str,
    ) -> int:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")
        detalhes_json = (
            json.dumps(
                detalhes,
                ensure_ascii=False,
                sort_keys=True,
            )
            if detalhes is not None
            else None
        )

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO auditoria_administrativa (
                    acao,
                    alvo,
                    detalhes_json,
                    dispositivo,
                    resultado,
                    executado_em
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    acao,
                    alvo,
                    detalhes_json,
                    dispositivo,
                    resultado,
                    agora,
                ),
            )

        return int(cursor.lastrowid)

    def listar_auditoria(
        self,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        limite = max(1, min(limite, 200))

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    acao,
                    alvo,
                    detalhes_json,
                    dispositivo,
                    resultado,
                    executado_em
                FROM auditoria_administrativa
                ORDER BY id DESC
                LIMIT ?
                """,
                (limite,),
            ).fetchall()

        itens: list[dict[str, Any]] = []

        for linha in linhas:
            detalhes = None

            if linha["detalhes_json"]:
                try:
                    detalhes = json.loads(linha["detalhes_json"])
                except json.JSONDecodeError:
                    detalhes = {
                        "raw": str(linha["detalhes_json"]),
                    }

            itens.append(
                {
                    "id": int(linha["id"]),
                    "acao": str(linha["acao"]),
                    "alvo": linha["alvo"],
                    "detalhes": detalhes,
                    "dispositivo": linha["dispositivo"],
                    "resultado": str(linha["resultado"]),
                    "executado_em": str(linha["executado_em"]),
                }
            )

        return itens
