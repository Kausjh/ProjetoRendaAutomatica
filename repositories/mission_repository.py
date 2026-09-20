from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.missions import (
    ConcessaoRecompensaMissao,
    EventoProgressoMissao,
    ProgressoMissao,
    ResultadoProgressoMissao,
)


class ConflitoIdempotenciaMissao(ValueError):
    pass


class ConflitoEstadoMissao(ValueError):
    pass


class ConflitoConcessaoRecompensa(ValueError):
    pass


class MissionRepository:
    def __init__(
        self,
        caminho_banco: str | Path,
    ) -> None:
        self.caminho_banco = Path(caminho_banco)

        self._inicializar()

    @staticmethod
    def _agora() -> str:
        return datetime.now(UTC).isoformat()

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_banco,
            timeout=30,
        )

        conexao.row_factory = sqlite3.Row

        conexao.execute("PRAGMA foreign_keys = ON")

        return conexao

    def _inicializar(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS mission_progress_events (
                    id TEXT PRIMARY KEY,
                    conta_id TEXT NOT NULL,
                    missao_codigo TEXT NOT NULL,
                    regra_versao TEXT NOT NULL,
                    instancia_chave TEXT NOT NULL,
                    chave_idempotencia TEXT NOT NULL,
                    tipo_evento TEXT NOT NULL,
                    origem TEXT NOT NULL,
                    origem_id TEXT NOT NULL,
                    delta INTEGER NOT NULL
                        CHECK (delta > 0),
                    metadados_json TEXT NOT NULL,
                    ocorrido_em TEXT NOT NULL,
                    criado_em TEXT NOT NULL,

                    FOREIGN KEY (conta_id)
                        REFERENCES contas_usuario(id),

                    UNIQUE (
                        conta_id,
                        missao_codigo,
                        regra_versao,
                        instancia_chave,
                        chave_idempotencia
                    )
                );

                CREATE INDEX IF NOT EXISTS
                    idx_mission_events_account
                ON mission_progress_events(
                    conta_id,
                    criado_em DESC
                );

                CREATE INDEX IF NOT EXISTS
                    idx_mission_events_source
                ON mission_progress_events(
                    origem,
                    origem_id
                );

                CREATE TABLE IF NOT EXISTS mission_progress (
                    conta_id TEXT NOT NULL,
                    missao_codigo TEXT NOT NULL,
                    regra_versao TEXT NOT NULL,
                    instancia_chave TEXT NOT NULL,
                    progresso_total INTEGER NOT NULL
                        CHECK (progresso_total >= 0),
                    alvo_total INTEGER NOT NULL
                        CHECK (alvo_total > 0),
                    concluida_em TEXT,
                    atualizado_em TEXT NOT NULL,

                    PRIMARY KEY (
                        conta_id,
                        missao_codigo,
                        regra_versao,
                        instancia_chave
                    ),

                    FOREIGN KEY (conta_id)
                        REFERENCES contas_usuario(id)
                );

                CREATE INDEX IF NOT EXISTS
                    idx_mission_progress_account
                ON mission_progress(
                    conta_id,
                    atualizado_em DESC
                );

                CREATE TABLE IF NOT EXISTS mission_reward_grants (
                    id TEXT PRIMARY KEY,
                    conta_id TEXT NOT NULL,
                    missao_codigo TEXT NOT NULL,
                    regra_versao TEXT NOT NULL,
                    instancia_chave TEXT NOT NULL,
                    tipo_recompensa TEXT NOT NULL
                        CHECK (tipo_recompensa = 'xp'),
                    quantidade INTEGER NOT NULL
                        CHECK (quantidade > 0),
                    status TEXT NOT NULL
                        CHECK (
                            status IN (
                                'pending',
                                'granted'
                            )
                        ),
                    referencia_concessao TEXT,
                    criado_em TEXT NOT NULL,
                    concedida_em TEXT,

                    FOREIGN KEY (conta_id)
                        REFERENCES contas_usuario(id),

                    UNIQUE (
                        conta_id,
                        missao_codigo,
                        regra_versao,
                        instancia_chave
                    )
                );

                CREATE INDEX IF NOT EXISTS
                    idx_mission_reward_status
                ON mission_reward_grants(
                    status,
                    criado_em
                );
                """)

    @staticmethod
    def _evento_da_linha(
        linha: sqlite3.Row,
    ) -> EventoProgressoMissao:
        return EventoProgressoMissao(
            id=str(linha["id"]),
            conta_id=str(linha["conta_id"]),
            missao_codigo=str(linha["missao_codigo"]),
            regra_versao=str(linha["regra_versao"]),
            instancia_chave=str(linha["instancia_chave"]),
            chave_idempotencia=str(linha["chave_idempotencia"]),
            tipo_evento=str(linha["tipo_evento"]),
            origem=str(linha["origem"]),
            origem_id=str(linha["origem_id"]),
            delta=int(linha["delta"]),
            metadados=json.loads(str(linha["metadados_json"])),
            ocorrido_em=str(linha["ocorrido_em"]),
            criado_em=str(linha["criado_em"]),
        )

    @staticmethod
    def _progresso_da_linha(
        linha: sqlite3.Row,
    ) -> ProgressoMissao:
        return ProgressoMissao(
            conta_id=str(linha["conta_id"]),
            missao_codigo=str(linha["missao_codigo"]),
            regra_versao=str(linha["regra_versao"]),
            instancia_chave=str(linha["instancia_chave"]),
            progresso_total=int(linha["progresso_total"]),
            alvo_total=int(linha["alvo_total"]),
            concluida_em=(
                str(linha["concluida_em"]) if linha["concluida_em"] is not None else None
            ),
            atualizado_em=str(linha["atualizado_em"]),
        )

    @staticmethod
    def _recompensa_da_linha(
        linha: sqlite3.Row,
    ) -> ConcessaoRecompensaMissao:
        return ConcessaoRecompensaMissao(
            id=str(linha["id"]),
            conta_id=str(linha["conta_id"]),
            missao_codigo=str(linha["missao_codigo"]),
            regra_versao=str(linha["regra_versao"]),
            instancia_chave=str(linha["instancia_chave"]),
            tipo_recompensa=str(linha["tipo_recompensa"]),
            quantidade=int(linha["quantidade"]),
            status=str(linha["status"]),
            referencia_concessao=(
                str(linha["referencia_concessao"])
                if linha["referencia_concessao"] is not None
                else None
            ),
            criado_em=str(linha["criado_em"]),
            concedida_em=(
                str(linha["concedida_em"]) if linha["concedida_em"] is not None else None
            ),
        )

    def _obter_progresso_conexao(
        self,
        conexao: sqlite3.Connection,
        *,
        conta_id: str,
        missao_codigo: str,
        regra_versao: str,
        instancia_chave: str,
    ) -> ProgressoMissao | None:
        linha = conexao.execute(
            """
            SELECT *
            FROM mission_progress
            WHERE conta_id = ?
              AND missao_codigo = ?
              AND regra_versao = ?
              AND instancia_chave = ?
            """,
            (
                conta_id,
                missao_codigo,
                regra_versao,
                instancia_chave,
            ),
        ).fetchone()

        if linha is None:
            return None

        return self._progresso_da_linha(linha)

    def _obter_recompensa_conexao(
        self,
        conexao: sqlite3.Connection,
        *,
        conta_id: str,
        missao_codigo: str,
        regra_versao: str,
        instancia_chave: str,
    ) -> ConcessaoRecompensaMissao | None:
        linha = conexao.execute(
            """
            SELECT *
            FROM mission_reward_grants
            WHERE conta_id = ?
              AND missao_codigo = ?
              AND regra_versao = ?
              AND instancia_chave = ?
            """,
            (
                conta_id,
                missao_codigo,
                regra_versao,
                instancia_chave,
            ),
        ).fetchone()

        if linha is None:
            return None

        return self._recompensa_da_linha(linha)

    def obter_progresso(
        self,
        *,
        conta_id: str,
        missao_codigo: str,
        regra_versao: str,
        instancia_chave: str = "lifetime",
    ) -> ProgressoMissao | None:
        with self._conectar() as conexao:
            return self._obter_progresso_conexao(
                conexao,
                conta_id=conta_id,
                missao_codigo=missao_codigo,
                regra_versao=regra_versao,
                instancia_chave=instancia_chave,
            )

    def listar_progressos(
        self,
        *,
        conta_id: str,
    ) -> list[ProgressoMissao]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM mission_progress
                WHERE conta_id = ?
                ORDER BY
                    concluida_em IS NULL DESC,
                    atualizado_em DESC,
                    missao_codigo ASC
                """,
                (conta_id,),
            ).fetchall()

        return [self._progresso_da_linha(linha) for linha in linhas]

    def listar_eventos(
        self,
        *,
        conta_id: str,
        missao_codigo: str | None = None,
        limite: int = 100,
    ) -> list[EventoProgressoMissao]:
        limite_seguro = max(
            1,
            min(
                int(limite),
                1000,
            ),
        )

        with self._conectar() as conexao:
            if missao_codigo is None:
                linhas = conexao.execute(
                    """
                    SELECT *
                    FROM mission_progress_events
                    WHERE conta_id = ?
                    ORDER BY criado_em ASC, id ASC
                    LIMIT ?
                    """,
                    (
                        conta_id,
                        limite_seguro,
                    ),
                ).fetchall()
            else:
                linhas = conexao.execute(
                    """
                    SELECT *
                    FROM mission_progress_events
                    WHERE conta_id = ?
                      AND missao_codigo = ?
                    ORDER BY criado_em ASC, id ASC
                    LIMIT ?
                    """,
                    (
                        conta_id,
                        missao_codigo,
                        limite_seguro,
                    ),
                ).fetchall()

        return [self._evento_da_linha(linha) for linha in linhas]

    def listar_recompensas_pendentes(
        self,
        *,
        limite: int = 100,
    ) -> list[ConcessaoRecompensaMissao]:
        limite_seguro = max(
            1,
            min(
                int(limite),
                1000,
            ),
        )

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM mission_reward_grants
                WHERE status = 'pending'
                ORDER BY criado_em ASC, id ASC
                LIMIT ?
                """,
                (limite_seguro,),
            ).fetchall()

        return [self._recompensa_da_linha(linha) for linha in linhas]

    def registrar_progresso(
        self,
        *,
        conta_id: str,
        missao_codigo: str,
        regra_versao: str,
        instancia_chave: str,
        chave_idempotencia: str,
        tipo_evento: str,
        origem: str,
        origem_id: str,
        delta: int,
        alvo_total: int,
        recompensa_xp: int,
        metadados: dict[str, Any],
        ocorrido_em: str,
    ) -> ResultadoProgressoMissao:
        if delta < 1:
            raise ValueError("delta precisa ser positivo.")

        if alvo_total < 1:
            raise ValueError("alvo_total precisa ser positivo.")

        if recompensa_xp < 1:
            raise ValueError("recompensa_xp precisa ser positiva.")

        metadados_json = json.dumps(
            metadados,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

        agora = self._agora()

        conexao = self._conectar()

        try:
            conexao.execute("BEGIN IMMEDIATE")

            existente_linha = conexao.execute(
                """
                SELECT *
                FROM mission_progress_events
                WHERE conta_id = ?
                  AND missao_codigo = ?
                  AND regra_versao = ?
                  AND instancia_chave = ?
                  AND chave_idempotencia = ?
                """,
                (
                    conta_id,
                    missao_codigo,
                    regra_versao,
                    instancia_chave,
                    chave_idempotencia,
                ),
            ).fetchone()

            if existente_linha is not None:
                esperado = (
                    tipo_evento,
                    origem,
                    origem_id,
                    int(delta),
                    metadados_json,
                )

                encontrado = (
                    str(existente_linha["tipo_evento"]),
                    str(existente_linha["origem"]),
                    str(existente_linha["origem_id"]),
                    int(existente_linha["delta"]),
                    str(existente_linha["metadados_json"]),
                )

                if encontrado != esperado:
                    raise (
                        ConflitoIdempotenciaMissao(
                            "Chave de idempotencia " "reutilizada com semantica " "diferente."
                        )
                    )

                progresso = self._obter_progresso_conexao(
                    conexao,
                    conta_id=conta_id,
                    missao_codigo=(missao_codigo),
                    regra_versao=(regra_versao),
                    instancia_chave=(instancia_chave),
                )

                if progresso is None:
                    raise ConflitoEstadoMissao(
                        "Evento idempotente existe " "sem snapshot de progresso."
                    )

                if progresso.alvo_total != alvo_total:
                    raise ConflitoEstadoMissao("Alvo mudou sem troca de " "versao de regra.")

                recompensa = self._obter_recompensa_conexao(
                    conexao,
                    conta_id=conta_id,
                    missao_codigo=(missao_codigo),
                    regra_versao=(regra_versao),
                    instancia_chave=(instancia_chave),
                )

                if recompensa is not None and recompensa.quantidade != recompensa_xp:
                    raise ConflitoEstadoMissao("Recompensa mudou sem troca " "de versao de regra.")

                conexao.commit()

                return ResultadoProgressoMissao(
                    status="idempotent",
                    evento=(self._evento_da_linha(existente_linha)),
                    progresso=progresso,
                    recompensa=recompensa,
                    concluida_agora=False,
                    recompensa_criada=False,
                )

            progresso_anterior = self._obter_progresso_conexao(
                conexao,
                conta_id=conta_id,
                missao_codigo=missao_codigo,
                regra_versao=regra_versao,
                instancia_chave=(instancia_chave),
            )

            if progresso_anterior is not None:
                if progresso_anterior.alvo_total != alvo_total:
                    raise ConflitoEstadoMissao("Alvo mudou sem troca de " "versao de regra.")

                if progresso_anterior.concluida:
                    recompensa = self._obter_recompensa_conexao(
                        conexao,
                        conta_id=conta_id,
                        missao_codigo=(missao_codigo),
                        regra_versao=(regra_versao),
                        instancia_chave=(instancia_chave),
                    )

                    if recompensa is None:
                        raise ConflitoEstadoMissao(
                            "Missao concluida sem " "concessao de recompensa."
                        )

                    if recompensa.quantidade != recompensa_xp:
                        raise ConflitoEstadoMissao("Recompensa mudou sem " "troca de versao.")

                    conexao.commit()

                    return ResultadoProgressoMissao(
                        status="completed",
                        evento=None,
                        progresso=(progresso_anterior),
                        recompensa=recompensa,
                        concluida_agora=False,
                        recompensa_criada=False,
                    )

            evento_id = "mpe_" + uuid.uuid4().hex

            conexao.execute(
                """
                INSERT INTO mission_progress_events (
                    id,
                    conta_id,
                    missao_codigo,
                    regra_versao,
                    instancia_chave,
                    chave_idempotencia,
                    tipo_evento,
                    origem,
                    origem_id,
                    delta,
                    metadados_json,
                    ocorrido_em,
                    criado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evento_id,
                    conta_id,
                    missao_codigo,
                    regra_versao,
                    instancia_chave,
                    chave_idempotencia,
                    tipo_evento,
                    origem,
                    origem_id,
                    int(delta),
                    metadados_json,
                    ocorrido_em,
                    agora,
                ),
            )

            anterior_total = (
                progresso_anterior.progresso_total if progresso_anterior is not None else 0
            )

            novo_total = min(
                alvo_total,
                anterior_total + int(delta),
            )

            concluida_agora = novo_total >= alvo_total and (
                progresso_anterior is None or not (progresso_anterior.concluida)
            )

            concluida_em = (
                agora
                if concluida_agora
                else (progresso_anterior.concluida_em if progresso_anterior is not None else None)
            )

            conexao.execute(
                """
                INSERT INTO mission_progress (
                    conta_id,
                    missao_codigo,
                    regra_versao,
                    instancia_chave,
                    progresso_total,
                    alvo_total,
                    concluida_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (
                    conta_id,
                    missao_codigo,
                    regra_versao,
                    instancia_chave
                )
                DO UPDATE SET
                    progresso_total =
                        excluded.progresso_total,
                    alvo_total =
                        excluded.alvo_total,
                    concluida_em =
                        excluded.concluida_em,
                    atualizado_em =
                        excluded.atualizado_em
                """,
                (
                    conta_id,
                    missao_codigo,
                    regra_versao,
                    instancia_chave,
                    novo_total,
                    alvo_total,
                    concluida_em,
                    agora,
                ),
            )

            recompensa_criada = False

            if concluida_agora:
                recompensa_id = "mrg_" + uuid.uuid4().hex

                cursor = conexao.execute(
                    """
                    INSERT OR IGNORE INTO
                        mission_reward_grants (
                            id,
                            conta_id,
                            missao_codigo,
                            regra_versao,
                            instancia_chave,
                            tipo_recompensa,
                            quantidade,
                            status,
                            referencia_concessao,
                            criado_em,
                            concedida_em
                        )
                    VALUES (
                        ?, ?, ?, ?, ?,
                        'xp', ?, 'pending',
                        NULL, ?, NULL
                    )
                    """,
                    (
                        recompensa_id,
                        conta_id,
                        missao_codigo,
                        regra_versao,
                        instancia_chave,
                        recompensa_xp,
                        agora,
                    ),
                )

                recompensa_criada = cursor.rowcount == 1

            progresso = self._obter_progresso_conexao(
                conexao,
                conta_id=conta_id,
                missao_codigo=missao_codigo,
                regra_versao=regra_versao,
                instancia_chave=(instancia_chave),
            )

            if progresso is None:
                raise ConflitoEstadoMissao("Snapshot nao foi criado.")

            recompensa = self._obter_recompensa_conexao(
                conexao,
                conta_id=conta_id,
                missao_codigo=missao_codigo,
                regra_versao=regra_versao,
                instancia_chave=(instancia_chave),
            )

            evento_linha = conexao.execute(
                """
                SELECT *
                FROM mission_progress_events
                WHERE id = ?
                """,
                (evento_id,),
            ).fetchone()

            if evento_linha is None:
                raise ConflitoEstadoMissao("Evento criado nao encontrado.")

            conexao.commit()

            return ResultadoProgressoMissao(
                status="created",
                evento=self._evento_da_linha(evento_linha),
                progresso=progresso,
                recompensa=recompensa,
                concluida_agora=(concluida_agora),
                recompensa_criada=(recompensa_criada),
            )

        except Exception:
            conexao.rollback()
            raise

        finally:
            conexao.close()

    def marcar_recompensa_concedida(
        self,
        *,
        recompensa_id: str,
        referencia_concessao: str,
    ) -> tuple[
        ConcessaoRecompensaMissao,
        bool,
    ]:
        referencia = str(referencia_concessao or "").strip()

        if not referencia:
            raise ValueError("referencia_concessao " "nao pode ser vazia.")

        conexao = self._conectar()

        try:
            conexao.execute("BEGIN IMMEDIATE")

            linha = conexao.execute(
                """
                SELECT *
                FROM mission_reward_grants
                WHERE id = ?
                """,
                (recompensa_id,),
            ).fetchone()

            if linha is None:
                raise ValueError("Recompensa nao encontrada.")

            atual = self._recompensa_da_linha(linha)

            if atual.status == "granted":
                if atual.referencia_concessao != referencia:
                    raise (
                        ConflitoConcessaoRecompensa(
                            "Recompensa ja concedida " "com outra referencia."
                        )
                    )

                conexao.commit()

                return atual, False

            agora = self._agora()

            conexao.execute(
                """
                UPDATE mission_reward_grants
                SET
                    status = 'granted',
                    referencia_concessao = ?,
                    concedida_em = ?
                WHERE id = ?
                  AND status = 'pending'
                """,
                (
                    referencia,
                    agora,
                    recompensa_id,
                ),
            )

            atualizada_linha = conexao.execute(
                """
                    SELECT *
                    FROM mission_reward_grants
                    WHERE id = ?
                    """,
                (recompensa_id,),
            ).fetchone()

            if atualizada_linha is None:
                raise ConflitoEstadoMissao("Recompensa desapareceu.")

            atualizada = self._recompensa_da_linha(atualizada_linha)

            conexao.commit()

            return atualizada, True

        except Exception:
            conexao.rollback()
            raise

        finally:
            conexao.close()
