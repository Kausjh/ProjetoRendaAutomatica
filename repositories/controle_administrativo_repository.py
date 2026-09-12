# 63.8738, -149.7525

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

MODOS_OPERACAO_PUBLICACAO = frozenset(
    {
        "automatico",
        "manual",
        "hibrido",
    }
)
MODO_OPERACAO_PADRAO = "automatico"
PONTUACAO_MINIMA_AUTOMATICA_HIBRIDO = 80.0


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

                CREATE TABLE IF NOT EXISTS enforcement_monetizacao_consumido (
                    recomendacao_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    reservado_em TEXT NOT NULL,
                    concluido_em TEXT
                );
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

    def salvar_snapshot_operacional_ai(
        self,
        snapshot: dict[str, Any],
    ) -> None:
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot precisa ser dict")

        payload = {
            "schema_version": 1,
            "capturado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
            "snapshot": snapshot,
        }

        self.definir_estado(
            chave="snapshot_operacional_ai_v1",
            valor=json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
            ),
        )

    def obter_snapshot_operacional_ai(
        self,
    ) -> dict[str, Any] | None:
        bruto = self.obter_estado("snapshot_operacional_ai_v1")

        if bruto is None:
            return None

        try:
            payload = json.loads(bruto)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        if payload.get("schema_version") != 1:
            return None

        snapshot = payload.get("snapshot")
        capturado_em = payload.get("capturado_em")

        if not isinstance(snapshot, dict):
            return None

        if not isinstance(capturado_em, str) or not capturado_em:
            return None

        return {
            "schema_version": 1,
            "capturado_em": capturado_em,
            "snapshot": snapshot,
        }

    def obter_snapshot_monetizacao(
        self,
    ) -> dict[str, Any] | None:
        """Le o snapshot persistido da observabilidade de monetizacao.

        A camada administrativa trata o payload como snapshot opaco:
        valida apenas JSON, objeto e schema_version. A semantica dos
        contadores continua pertencendo ao ObservadorMonetizacao.
        """
        bruto = self.obter_estado("observabilidade_monetizacao_v1")

        if bruto is None:
            return None

        try:
            snapshot = json.loads(bruto)
        except json.JSONDecodeError:
            return None

        if not isinstance(snapshot, dict):
            return None

        if snapshot.get("schema_version") != 1:
            return None

        return snapshot

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

    def remover_estado(
        self,
        chave: str,
    ) -> None:
        with self._conectar() as conexao:
            conexao.execute(
                """
                DELETE FROM estado_operacional
                WHERE chave = ?
                """,
                (chave,),
            )

    def obter_modo_operacao(self) -> str:
        modo = self.obter_estado(
            "modo_operacao",
            MODO_OPERACAO_PADRAO,
        )

        if modo not in MODOS_OPERACAO_PUBLICACAO:
            return MODO_OPERACAO_PADRAO

        return modo

    def definir_modo_operacao(
        self,
        modo: str,
    ) -> None:
        modo_normalizado = modo.strip().casefold()

        if modo_normalizado not in MODOS_OPERACAO_PUBLICACAO:
            raise ValueError("Modo de operacao invalido.")

        self.definir_estado(
            "modo_operacao",
            modo_normalizado,
        )

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

    def reservar_enforcement_monetizacao(
        self,
        recomendacao_id: str,
    ) -> bool:
        recomendacao_id = recomendacao_id.strip()

        if not recomendacao_id:
            raise ValueError("recomendacao_id nao pode ser vazio.")

        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT OR IGNORE INTO enforcement_monetizacao_consumido (
                    recomendacao_id,
                    status,
                    reservado_em,
                    concluido_em
                )
                VALUES (?, 'reservado', ?, NULL)
                """,
                (
                    recomendacao_id,
                    agora,
                ),
            )

        return cursor.rowcount == 1

    def concluir_enforcement_monetizacao(
        self,
        recomendacao_id: str,
    ) -> bool:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE enforcement_monetizacao_consumido
                SET
                    status = 'concluido',
                    concluido_em = ?
                WHERE recomendacao_id = ?
                  AND status = 'reservado'
                """,
                (
                    agora,
                    recomendacao_id,
                ),
            )

        return cursor.rowcount == 1

    def liberar_enforcement_monetizacao(
        self,
        recomendacao_id: str,
    ) -> bool:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                DELETE FROM enforcement_monetizacao_consumido
                WHERE recomendacao_id = ?
                  AND status = 'reservado'
                """,
                (recomendacao_id,),
            )

        return cursor.rowcount == 1

    def obter_enforcement_monetizacao_consumido(
        self,
        recomendacao_id: str,
    ) -> dict[str, str | None] | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    recomendacao_id,
                    status,
                    reservado_em,
                    concluido_em
                FROM enforcement_monetizacao_consumido
                WHERE recomendacao_id = ?
                LIMIT 1
                """,
                (recomendacao_id,),
            ).fetchone()

        if linha is None:
            return None

        return {
            "recomendacao_id": str(linha["recomendacao_id"]),
            "status": str(linha["status"]),
            "reservado_em": str(linha["reservado_em"]),
            "concluido_em": (
                str(linha["concluido_em"]) if linha["concluido_em"] is not None else None
            ),
        }
