from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.gamification import (
    EventoGamificacao,
    SaldoGamificacao,
)


class LimiteEventosGamificacaoExcedido(RuntimeError):
    pass


class ConflitoIdempotenciaGamificacao(RuntimeError):
    pass


class GamificationRepository:
    def __init__(
        self,
        caminho_banco: str | Path,
    ) -> None:
        self.caminho_banco = Path(caminho_banco)

        self.caminho_banco.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._garantir_schema()

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_banco,
            timeout=30,
            isolation_level=None,
        )

        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")

        return conexao

    @staticmethod
    def _agora_iso() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def _garantir_schema(
        self,
    ) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS
                    gamification_profiles (
                        conta_id TEXT PRIMARY KEY,

                        xp_total INTEGER NOT NULL
                            DEFAULT 0
                            CHECK (xp_total >= 0),

                        reputacao_total INTEGER NOT NULL
                            DEFAULT 0,

                        eventos_total INTEGER NOT NULL
                            DEFAULT 0
                            CHECK (eventos_total >= 0),

                        atualizado_em TEXT NOT NULL,

                        FOREIGN KEY (conta_id)
                            REFERENCES contas_usuario(id)
                            ON DELETE CASCADE
                    );

                CREATE TABLE IF NOT EXISTS
                    gamification_events (
                        id TEXT PRIMARY KEY,

                        conta_id TEXT NOT NULL,

                        chave_idempotencia TEXT NOT NULL,

                        tipo_evento TEXT NOT NULL,

                        origem TEXT NOT NULL,

                        origem_id TEXT,

                        xp_delta INTEGER NOT NULL
                            CHECK (xp_delta >= 0),

                        reputacao_delta INTEGER NOT NULL,

                        regra_versao TEXT NOT NULL,

                        metadados_json TEXT NOT NULL
                            DEFAULT '{}',

                        ocorrido_em TEXT NOT NULL,

                        criado_em TEXT NOT NULL,

                        FOREIGN KEY (conta_id)
                            REFERENCES contas_usuario(id)
                            ON DELETE CASCADE,

                        UNIQUE (
                            conta_id,
                            chave_idempotencia
                        )
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_gamification_events_conta_tempo
                    ON gamification_events(
                        conta_id,
                        ocorrido_em DESC,
                        id DESC
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_gamification_events_tipo_tempo
                    ON gamification_events(
                        conta_id,
                        tipo_evento,
                        ocorrido_em DESC
                    );
                """)

    @staticmethod
    def _evento_da_linha(
        linha: sqlite3.Row,
    ) -> EventoGamificacao:
        try:
            metadados = json.loads(str(linha["metadados_json"]))
        except (
            TypeError,
            ValueError,
        ):
            metadados = {}

        if not isinstance(
            metadados,
            dict,
        ):
            metadados = {}

        return EventoGamificacao(
            id=str(linha["id"]),
            conta_id=str(linha["conta_id"]),
            chave_idempotencia=str(linha["chave_idempotencia"]),
            tipo_evento=str(linha["tipo_evento"]),
            origem=str(linha["origem"]),
            origem_id=(str(linha["origem_id"]) if linha["origem_id"] is not None else None),
            xp_delta=int(linha["xp_delta"]),
            reputacao_delta=int(linha["reputacao_delta"]),
            regra_versao=str(linha["regra_versao"]),
            metadados=dict(metadados),
            ocorrido_em=str(linha["ocorrido_em"]),
            criado_em=str(linha["criado_em"]),
        )

    @staticmethod
    def _saldo_da_linha(
        linha: sqlite3.Row,
    ) -> SaldoGamificacao:
        return SaldoGamificacao(
            conta_id=str(linha["conta_id"]),
            xp_total=int(linha["xp_total"]),
            reputacao_total=int(linha["reputacao_total"]),
            eventos_total=int(linha["eventos_total"]),
            atualizado_em=str(linha["atualizado_em"]),
        )

    @staticmethod
    def _buscar_evento(
        conexao: sqlite3.Connection,
        *,
        conta_id: str,
        chave_idempotencia: str,
    ) -> sqlite3.Row | None:
        return conexao.execute(
            """
            SELECT *
            FROM gamification_events
            WHERE conta_id = ?
              AND chave_idempotencia = ?
            """,
            (
                conta_id,
                chave_idempotencia,
            ),
        ).fetchone()

    def obter_evento_por_chave(
        self,
        *,
        conta_id: str,
        chave_idempotencia: str,
    ) -> EventoGamificacao | None:
        with self._conectar() as conexao:
            linha = self._buscar_evento(
                conexao,
                conta_id=conta_id,
                chave_idempotencia=(chave_idempotencia),
            )

        if linha is None:
            return None

        return self._evento_da_linha(linha)

    def obter_saldo(
        self,
        conta_id: str,
    ) -> SaldoGamificacao:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT *
                FROM gamification_profiles
                WHERE conta_id = ?
                """,
                (conta_id,),
            ).fetchone()

        if linha is None:
            return SaldoGamificacao(
                conta_id=conta_id,
                xp_total=0,
                reputacao_total=0,
                eventos_total=0,
                atualizado_em=None,
            )

        return self._saldo_da_linha(linha)

    def registrar_evento(
        self,
        *,
        conta_id: str,
        chave_idempotencia: str,
        tipo_evento: str,
        origem: str,
        origem_id: str | None,
        xp_delta: int,
        reputacao_delta: int,
        regra_versao: str,
        metadados: dict[str, Any] | None = None,
        ocorrido_em: str | None = None,
        limite_por_janela: int | None = None,
        desde_iso: str | None = None,
    ) -> tuple[
        EventoGamificacao,
        bool,
    ]:
        if (limite_por_janela is None) != (desde_iso is None):
            raise ValueError("limite_por_janela e " "desde_iso precisam ser " "usados juntos.")

        agora = self._agora_iso()
        ocorrido = ocorrido_em or agora

        evento_id = "gme_" + uuid.uuid4().hex

        metadados_json = json.dumps(
            metadados or {},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        with self._conectar() as conexao:
            conexao.execute("BEGIN IMMEDIATE")

            try:
                existente = self._buscar_evento(
                    conexao,
                    conta_id=conta_id,
                    chave_idempotencia=(chave_idempotencia),
                )

                if existente is not None:
                    existente_origem_id = (
                        str(existente["origem_id"]) if existente["origem_id"] is not None else None
                    )

                    conflito = any(
                        (
                            str(existente["tipo_evento"]) != tipo_evento,
                            str(existente["origem"]) != origem,
                            existente_origem_id != origem_id,
                            int(existente["xp_delta"]) != xp_delta,
                            int(existente["reputacao_delta"]) != reputacao_delta,
                            str(existente["regra_versao"]) != regra_versao,
                            str(existente["metadados_json"]) != metadados_json,
                        )
                    )

                    if conflito:
                        raise (
                            ConflitoIdempotenciaGamificacao(
                                "Chave de idempotencia ja existe " "com semantica diferente."
                            )
                        )

                    conexao.commit()

                    return (
                        self._evento_da_linha(existente),
                        False,
                    )

                if limite_por_janela is not None and desde_iso is not None:
                    linha_total = conexao.execute(
                        """
                            SELECT COUNT(*) AS total
                            FROM gamification_events
                            WHERE conta_id = ?
                              AND tipo_evento = ?
                              AND criado_em >= ?
                            """,
                        (
                            conta_id,
                            tipo_evento,
                            desde_iso,
                        ),
                    ).fetchone()

                    total = int(linha_total["total"]) if linha_total is not None else 0

                    if total >= limite_por_janela:
                        raise (
                            LimiteEventosGamificacaoExcedido(
                                "Limite atomico " "de eventos atingido."
                            )
                        )

                conexao.execute(
                    """
                    INSERT INTO gamification_events (
                        id,
                        conta_id,
                        chave_idempotencia,
                        tipo_evento,
                        origem,
                        origem_id,
                        xp_delta,
                        reputacao_delta,
                        regra_versao,
                        metadados_json,
                        ocorrido_em,
                        criado_em
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        evento_id,
                        conta_id,
                        chave_idempotencia,
                        tipo_evento,
                        origem,
                        origem_id,
                        xp_delta,
                        reputacao_delta,
                        regra_versao,
                        metadados_json,
                        ocorrido,
                        agora,
                    ),
                )

                conexao.execute(
                    """
                    INSERT INTO gamification_profiles (
                        conta_id,
                        xp_total,
                        reputacao_total,
                        eventos_total,
                        atualizado_em
                    )
                    VALUES (?, ?, ?, 1, ?)

                    ON CONFLICT(conta_id)
                    DO UPDATE SET
                        xp_total =
                            gamification_profiles.xp_total
                            + excluded.xp_total,

                        reputacao_total =
                            gamification_profiles.reputacao_total
                            + excluded.reputacao_total,

                        eventos_total =
                            gamification_profiles.eventos_total
                            + 1,

                        atualizado_em =
                            excluded.atualizado_em
                    """,
                    (
                        conta_id,
                        xp_delta,
                        reputacao_delta,
                        agora,
                    ),
                )

                linha_evento = self._buscar_evento(
                    conexao,
                    conta_id=conta_id,
                    chave_idempotencia=(chave_idempotencia),
                )

                if linha_evento is None:
                    raise RuntimeError("Evento desapareceu " "apos persistencia.")

                conexao.commit()

                return (
                    self._evento_da_linha(linha_evento),
                    True,
                )

            except Exception:
                conexao.rollback()
                raise

    def listar_eventos(
        self,
        *,
        conta_id: str,
        limite: int = 50,
        offset: int = 0,
    ) -> list[EventoGamificacao]:
        limite_normalizado = max(
            1,
            min(
                int(limite),
                100,
            ),
        )

        offset_normalizado = max(
            0,
            int(offset),
        )

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM gamification_events
                WHERE conta_id = ?
                ORDER BY
                    ocorrido_em DESC,
                    id DESC
                LIMIT ? OFFSET ?
                """,
                (
                    conta_id,
                    limite_normalizado,
                    offset_normalizado,
                ),
            ).fetchall()

        return [self._evento_da_linha(linha) for linha in linhas]
