from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from models.community_moderation import (
    ESTADOS_DENUNCIA_VALIDOS,
    FAMILIAS_ABUSO_CONFIRMADO,
    MOTIVOS_DENUNCIA_VALIDOS,
    RESULTADOS_MODERACAO_VALIDOS,
    TARGET_TYPES_VALIDOS,
    DecisaoCommunityModeration,
    DenunciaCommunityModeration,
    ResultadoRegistroDecisaoCommunityModeration,
    ResultadoRegistroDenunciaCommunityModeration,
)


class ConflitoIdempotenciaCommunityModeration(ValueError):
    pass


class ConflitoEstadoCommunityModeration(ValueError):
    pass


class ReporterCommunityModerationNaoEncontrado(ValueError):
    pass


class TargetCommunityModerationNaoEncontrado(ValueError):
    pass


class CommunityModerationRepository:
    REPORT_IDEMPOTENCY_PREFIX = "v1:community-report"

    DECISION_IDEMPOTENCY_PREFIX = "v1:community-moderation-decision"

    MAX_DETALHES = 1000
    MAX_JUSTIFICATIVA = 2000

    def __init__(
        self,
        caminho_banco: str | Path,
    ) -> None:
        self.caminho_banco = Path(caminho_banco)

        self.caminho_banco.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._inicializar()

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        conexao = sqlite3.connect(self.caminho_banco)

        conexao.row_factory = sqlite3.Row

        conexao.execute("PRAGMA foreign_keys = ON")

        return conexao

    def _inicializar(
        self,
    ) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS
                    community_moderation_reports (
                        id TEXT PRIMARY KEY,

                        chave_idempotencia TEXT
                            NOT NULL UNIQUE,

                        reporter_conta_id TEXT
                            NOT NULL,

                        target_type TEXT
                            NOT NULL
                            CHECK (
                                target_type
                                = 'community_discovery'
                            ),

                        target_id TEXT
                            NOT NULL,

                        motivo TEXT
                            NOT NULL
                            CHECK (
                                motivo IN (
                                    'spam',
                                    'fraud',
                                    'malicious_link',
                                    'abuse',
                                    'off_topic',
                                    'duplicate',
                                    'other'
                                )
                            ),

                        detalhes TEXT
                            CHECK (
                                detalhes IS NULL
                                OR length(detalhes) <= 1000
                            ),

                        estado TEXT
                            NOT NULL
                            CHECK (
                                estado IN (
                                    'received',
                                    'under_review',
                                    'resolved'
                                )
                            ),

                        criado_em TEXT
                            NOT NULL,

                        atualizado_em TEXT
                            NOT NULL,

                        FOREIGN KEY (
                            reporter_conta_id
                        )
                            REFERENCES contas_usuario(id)
                            ON DELETE RESTRICT,

                        FOREIGN KEY (
                            target_id
                        )
                            REFERENCES
                                community_discoveries(id)
                            ON DELETE RESTRICT,

                        UNIQUE (
                            reporter_conta_id,
                            target_type,
                            target_id,
                            motivo
                        )
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_community_moderation_reports_state
                    ON community_moderation_reports (
                        estado,
                        criado_em,
                        id
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_community_moderation_reports_target
                    ON community_moderation_reports (
                        target_type,
                        target_id,
                        criado_em
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_community_moderation_reports_reporter
                    ON community_moderation_reports (
                        reporter_conta_id,
                        criado_em
                    );

                CREATE TABLE IF NOT EXISTS
                    community_moderation_decisions (
                        id TEXT PRIMARY KEY,

                        chave_idempotencia TEXT
                            NOT NULL UNIQUE,

                        denuncia_id TEXT
                            NOT NULL,

                        moderator_actor_id TEXT
                            NOT NULL,

                        resultado TEXT
                            NOT NULL
                            CHECK (
                                resultado IN (
                                    'confirmed_abuse',
                                    'dismissed',
                                    'keep_under_review'
                                )
                            ),

                        familia_abuso_confirmado TEXT,

                        justificativa TEXT
                            CHECK (
                                justificativa IS NULL
                                OR length(justificativa) <= 2000
                            ),

                        ocorrido_em TEXT
                            NOT NULL,

                        criado_em TEXT
                            NOT NULL,

                        FOREIGN KEY (
                            denuncia_id
                        )
                            REFERENCES
                                community_moderation_reports(id)
                            ON DELETE RESTRICT,

                        CHECK (
                            (
                                resultado
                                    = 'confirmed_abuse'
                                AND
                                familia_abuso_confirmado
                                    IN (
                                        'abuso_confirmado',
                                        'spam_confirmado',
                                        'fraude_confirmada',
                                        'link_malicioso_confirmado'
                                    )
                            )
                            OR
                            (
                                resultado
                                    != 'confirmed_abuse'
                                AND
                                familia_abuso_confirmado
                                    IS NULL
                            )
                        )
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_community_moderation_decisions_report
                    ON community_moderation_decisions (
                        denuncia_id,
                        ocorrido_em,
                        id
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_community_moderation_decisions_result
                    ON community_moderation_decisions (
                        resultado,
                        ocorrido_em
                    );
                """)

    @staticmethod
    def _obrigatorio(
        valor: object,
        campo: str,
    ) -> str:
        texto = str(valor if valor is not None else "").strip()

        if not texto:
            raise ValueError(f"{campo} e obrigatorio.")

        return texto

    @classmethod
    def _opcional_limitado(
        cls,
        valor: object | None,
        *,
        campo: str,
        maximo: int,
    ) -> str | None:
        if valor is None:
            return None

        texto = str(valor).strip()

        if not texto:
            return None

        if len(texto) > maximo:
            raise ValueError(f"{campo} excede {maximo} caracteres.")

        return texto

    @classmethod
    def _timestamp(
        cls,
        valor: object,
        campo: str,
    ) -> str:
        texto = cls._obrigatorio(
            valor,
            campo,
        )

        try:
            dt = datetime.fromisoformat(
                texto.replace(
                    "Z",
                    "+00:00",
                )
            )
        except ValueError as erro:
            raise ValueError(f"{campo} invalido.") from erro

        if dt.tzinfo is None:
            raise ValueError(f"{campo} precisa conter timezone.")

        return dt.astimezone(UTC).isoformat()

    @staticmethod
    def _agora() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _limite(
        valor: int,
        *,
        maximo: int = 500,
    ) -> int:
        limite = int(valor)

        if limite < 1:
            raise ValueError("limite precisa ser positivo.")

        return min(
            limite,
            maximo,
        )

    @staticmethod
    def _offset(
        valor: int,
    ) -> int:
        offset = int(valor)

        if offset < 0:
            raise ValueError("offset nao pode ser negativo.")

        return offset

    @classmethod
    def _chave_denuncia(
        cls,
        *,
        reporter_conta_id: str,
        target_type: str,
        target_id: str,
        motivo: str,
    ) -> str:
        return (
            f"{cls.REPORT_IDEMPOTENCY_PREFIX}:"
            f"{reporter_conta_id}:"
            f"{target_type}:"
            f"{target_id}:"
            f"{motivo}"
        )

    @classmethod
    def _chave_decisao(
        cls,
        *,
        denuncia_id: str,
        acao_idempotencia: str,
    ) -> str:
        return f"{cls.DECISION_IDEMPOTENCY_PREFIX}:" f"{denuncia_id}:" f"{acao_idempotencia}"

    @staticmethod
    def _denuncia_da_linha(
        linha: sqlite3.Row,
    ) -> DenunciaCommunityModeration:
        return DenunciaCommunityModeration(
            id=str(linha["id"]),
            reporter_conta_id=str(linha["reporter_conta_id"]),
            target_type=str(linha["target_type"]),
            target_id=str(linha["target_id"]),
            motivo=str(linha["motivo"]),
            detalhes=(str(linha["detalhes"]) if linha["detalhes"] is not None else None),
            estado=str(linha["estado"]),
            criado_em=str(linha["criado_em"]),
            atualizado_em=str(linha["atualizado_em"]),
        )

    @staticmethod
    def _decisao_da_linha(
        linha: sqlite3.Row,
    ) -> DecisaoCommunityModeration:
        return DecisaoCommunityModeration(
            id=str(linha["id"]),
            denuncia_id=str(linha["denuncia_id"]),
            moderator_actor_id=str(linha["moderator_actor_id"]),
            resultado=str(linha["resultado"]),
            familia_abuso_confirmado=(
                str(linha["familia_abuso_confirmado"])
                if (linha["familia_abuso_confirmado"] is not None)
                else None
            ),
            justificativa=(
                str(linha["justificativa"]) if (linha["justificativa"] is not None) else None
            ),
            ocorrido_em=str(linha["ocorrido_em"]),
        )

    @staticmethod
    def _buscar_denuncia(
        conexao: sqlite3.Connection,
        *,
        denuncia_id: str,
    ) -> sqlite3.Row | None:
        return conexao.execute(
            """
            SELECT *
            FROM community_moderation_reports
            WHERE id = ?
            """,
            (denuncia_id,),
        ).fetchone()

    @staticmethod
    def _buscar_denuncia_por_chave(
        conexao: sqlite3.Connection,
        *,
        chave_idempotencia: str,
    ) -> sqlite3.Row | None:
        return conexao.execute(
            """
            SELECT *
            FROM community_moderation_reports
            WHERE chave_idempotencia = ?
            """,
            (chave_idempotencia,),
        ).fetchone()

    @staticmethod
    def _buscar_decisao_por_chave(
        conexao: sqlite3.Connection,
        *,
        chave_idempotencia: str,
    ) -> sqlite3.Row | None:
        return conexao.execute(
            """
            SELECT *
            FROM community_moderation_decisions
            WHERE chave_idempotencia = ?
            """,
            (chave_idempotencia,),
        ).fetchone()

    def registrar_denuncia(
        self,
        *,
        reporter_conta_id: str,
        target_type: str,
        target_id: str,
        motivo: str,
        detalhes: str | None,
        agora: str,
    ) -> ResultadoRegistroDenunciaCommunityModeration:
        reporter = self._obrigatorio(
            reporter_conta_id,
            "reporter_conta_id",
        )

        tipo_target = self._obrigatorio(
            target_type,
            "target_type",
        )

        target = self._obrigatorio(
            target_id,
            "target_id",
        )

        motivo_normalizado = self._obrigatorio(
            motivo,
            "motivo",
        )

        detalhes_normalizados = self._opcional_limitado(
            detalhes,
            campo="detalhes",
            maximo=self.MAX_DETALHES,
        )

        timestamp = self._timestamp(
            agora,
            "agora",
        )

        if tipo_target not in TARGET_TYPES_VALIDOS:
            raise ValueError("target_type invalido.")

        if motivo_normalizado not in MOTIVOS_DENUNCIA_VALIDOS:
            raise ValueError("motivo invalido.")

        chave = self._chave_denuncia(
            reporter_conta_id=reporter,
            target_type=tipo_target,
            target_id=target,
            motivo=motivo_normalizado,
        )

        conexao = self._conectar()

        try:
            conexao.execute("BEGIN IMMEDIATE")

            existente = self._buscar_denuncia_por_chave(
                conexao,
                chave_idempotencia=chave,
            )

            if existente is not None:
                esperado = (
                    reporter,
                    tipo_target,
                    target,
                    motivo_normalizado,
                    detalhes_normalizados,
                )

                encontrado = (
                    str(existente["reporter_conta_id"]),
                    str(existente["target_type"]),
                    str(existente["target_id"]),
                    str(existente["motivo"]),
                    (str(existente["detalhes"]) if (existente["detalhes"] is not None) else None),
                )

                if encontrado != esperado:
                    raise (
                        ConflitoIdempotenciaCommunityModeration(
                            "Chave de idempotencia de "
                            "denuncia reutilizada com "
                            "semantica diferente."
                        )
                    )

                conexao.commit()

                return ResultadoRegistroDenunciaCommunityModeration(
                    denuncia=(self._denuncia_da_linha(existente)),
                    criado=False,
                )

            reporter_existe = conexao.execute(
                """
                SELECT 1
                FROM contas_usuario
                WHERE id = ?
                """,
                (reporter,),
            ).fetchone()

            if reporter_existe is None:
                raise (
                    ReporterCommunityModerationNaoEncontrado("Conta do reporter " "nao encontrada.")
                )

            target_existe = conexao.execute(
                """
                SELECT 1
                FROM community_discoveries
                WHERE id = ?
                """,
                (target,),
            ).fetchone()

            if target_existe is None:
                raise (
                    TargetCommunityModerationNaoEncontrado("Target de moderacao " "nao encontrado.")
                )

            denuncia_id = "rpt_" + uuid4().hex

            conexao.execute(
                """
                INSERT INTO
                    community_moderation_reports (
                        id,
                        chave_idempotencia,
                        reporter_conta_id,
                        target_type,
                        target_id,
                        motivo,
                        detalhes,
                        estado,
                        criado_em,
                        atualizado_em
                    )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, 'received', ?, ?
                )
                """,
                (
                    denuncia_id,
                    chave,
                    reporter,
                    tipo_target,
                    target,
                    motivo_normalizado,
                    detalhes_normalizados,
                    timestamp,
                    timestamp,
                ),
            )

            linha = self._buscar_denuncia(
                conexao,
                denuncia_id=denuncia_id,
            )

            if linha is None:
                raise RuntimeError("Denuncia desapareceu " "apos persistencia.")

            conexao.commit()

            return ResultadoRegistroDenunciaCommunityModeration(
                denuncia=(self._denuncia_da_linha(linha)),
                criado=True,
            )

        except Exception:
            conexao.rollback()
            raise

        finally:
            conexao.close()

    def obter_denuncia(
        self,
        denuncia_id: str,
    ) -> DenunciaCommunityModeration | None:
        denuncia = self._obrigatorio(
            denuncia_id,
            "denuncia_id",
        )

        with self._conectar() as conexao:
            linha = self._buscar_denuncia(
                conexao,
                denuncia_id=denuncia,
            )

        if linha is None:
            return None

        return self._denuncia_da_linha(linha)

    def listar_denuncias_target(
        self,
        *,
        target_id: str,
        limite: int = 100,
        offset: int = 0,
    ) -> list[DenunciaCommunityModeration]:
        target = self._obrigatorio(
            target_id,
            "target_id",
        )

        limite_normalizado = self._limite(limite)

        offset_normalizado = self._offset(offset)

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM community_moderation_reports
                WHERE target_id = ?
                ORDER BY
                    criado_em DESC,
                    id DESC
                LIMIT ? OFFSET ?
                """,
                (
                    target,
                    limite_normalizado,
                    offset_normalizado,
                ),
            ).fetchall()

        return [self._denuncia_da_linha(linha) for linha in linhas]

    def listar_pendentes(
        self,
        *,
        limite: int = 100,
    ) -> list[DenunciaCommunityModeration]:
        limite_normalizado = self._limite(limite)

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM community_moderation_reports
                WHERE estado IN (
                    'received',
                    'under_review'
                )
                ORDER BY
                    criado_em ASC,
                    id ASC
                LIMIT ?
                """,
                (limite_normalizado,),
            ).fetchall()

        return [self._denuncia_da_linha(linha) for linha in linhas]

    def listar_decisoes(
        self,
        *,
        denuncia_id: str,
        limite: int = 100,
        offset: int = 0,
    ) -> list[DecisaoCommunityModeration]:
        denuncia = self._obrigatorio(
            denuncia_id,
            "denuncia_id",
        )

        limite_normalizado = self._limite(limite)

        offset_normalizado = self._offset(offset)

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM community_moderation_decisions
                WHERE denuncia_id = ?
                ORDER BY
                    ocorrido_em ASC,
                    id ASC
                LIMIT ? OFFSET ?
                """,
                (
                    denuncia,
                    limite_normalizado,
                    offset_normalizado,
                ),
            ).fetchall()

        return [self._decisao_da_linha(linha) for linha in linhas]

    def registrar_decisao(
        self,
        *,
        denuncia_id: str,
        acao_idempotencia: str,
        moderator_actor_id: str,
        resultado: str,
        familia_abuso_confirmado: str | None,
        justificativa: str | None,
        ocorrido_em: str,
    ) -> ResultadoRegistroDecisaoCommunityModeration:
        denuncia = self._obrigatorio(
            denuncia_id,
            "denuncia_id",
        )

        acao = self._obrigatorio(
            acao_idempotencia,
            "acao_idempotencia",
        )

        actor = self._obrigatorio(
            moderator_actor_id,
            "moderator_actor_id",
        )

        resultado_normalizado = self._obrigatorio(
            resultado,
            "resultado",
        )

        familia = (
            str(familia_abuso_confirmado).strip() if familia_abuso_confirmado is not None else None
        )

        if familia == "":
            familia = None

        justificativa_normalizada = self._opcional_limitado(
            justificativa,
            campo="justificativa",
            maximo=self.MAX_JUSTIFICATIVA,
        )

        ocorrido = self._timestamp(
            ocorrido_em,
            "ocorrido_em",
        )

        if resultado_normalizado not in RESULTADOS_MODERACAO_VALIDOS:
            raise ValueError("resultado invalido.")

        if resultado_normalizado == "confirmed_abuse":
            if familia not in FAMILIAS_ABUSO_CONFIRMADO:
                raise ValueError("confirmed_abuse exige " "familia de abuso valida.")
        elif familia is not None:
            raise ValueError("familia_abuso_confirmado " "so pode existir em " "confirmed_abuse.")

        chave = self._chave_decisao(
            denuncia_id=denuncia,
            acao_idempotencia=acao,
        )

        conexao = self._conectar()

        try:
            conexao.execute("BEGIN IMMEDIATE")

            existente = self._buscar_decisao_por_chave(
                conexao,
                chave_idempotencia=chave,
            )

            if existente is not None:
                esperado = (
                    denuncia,
                    actor,
                    resultado_normalizado,
                    familia,
                    justificativa_normalizada,
                    ocorrido,
                )

                encontrado = (
                    str(existente["denuncia_id"]),
                    str(existente["moderator_actor_id"]),
                    str(existente["resultado"]),
                    (
                        str(existente["familia_abuso_confirmado"])
                        if (existente["familia_abuso_confirmado"] is not None)
                        else None
                    ),
                    (
                        str(existente["justificativa"])
                        if (existente["justificativa"] is not None)
                        else None
                    ),
                    str(existente["ocorrido_em"]),
                )

                if encontrado != esperado:
                    raise (
                        ConflitoIdempotenciaCommunityModeration(
                            "Chave de idempotencia de "
                            "decisao reutilizada com "
                            "semantica diferente."
                        )
                    )

                denuncia_linha = self._buscar_denuncia(
                    conexao,
                    denuncia_id=denuncia,
                )

                if denuncia_linha is None:
                    raise RuntimeError("Decisao idempotente existe " "sem denuncia.")

                conexao.commit()

                return ResultadoRegistroDecisaoCommunityModeration(
                    decisao=(self._decisao_da_linha(existente)),
                    denuncia=(self._denuncia_da_linha(denuncia_linha)),
                    criado=False,
                )

            denuncia_linha = self._buscar_denuncia(
                conexao,
                denuncia_id=denuncia,
            )

            if denuncia_linha is None:
                raise ValueError("Denuncia nao encontrada.")

            estado_atual = str(denuncia_linha["estado"])

            if estado_atual not in ESTADOS_DENUNCIA_VALIDOS:
                raise RuntimeError("Estado persistido invalido.")

            if estado_atual == "resolved":
                raise (
                    ConflitoEstadoCommunityModeration(
                        "Denuncia resolvida nao aceita " "nova decisao."
                    )
                )

            atualizado_atual = self._timestamp(
                str(denuncia_linha["atualizado_em"]),
                "atualizado_em",
            )

            if datetime.fromisoformat(ocorrido) < datetime.fromisoformat(atualizado_atual):
                raise ValueError(
                    "ocorrido_em nao pode ser " "anterior ao estado atual " "da denuncia."
                )

            decisao_id = "mod_" + uuid4().hex

            criado_em = self._agora()

            conexao.execute(
                """
                INSERT INTO
                    community_moderation_decisions (
                        id,
                        chave_idempotencia,
                        denuncia_id,
                        moderator_actor_id,
                        resultado,
                        familia_abuso_confirmado,
                        justificativa,
                        ocorrido_em,
                        criado_em
                    )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                (
                    decisao_id,
                    chave,
                    denuncia,
                    actor,
                    resultado_normalizado,
                    familia,
                    justificativa_normalizada,
                    ocorrido,
                    criado_em,
                ),
            )

            novo_estado = (
                "under_review" if (resultado_normalizado == "keep_under_review") else "resolved"
            )

            conexao.execute(
                """
                UPDATE community_moderation_reports
                SET
                    estado = ?,
                    atualizado_em = ?
                WHERE id = ?
                """,
                (
                    novo_estado,
                    ocorrido,
                    denuncia,
                ),
            )

            decisao_linha = conexao.execute(
                """
                SELECT *
                FROM community_moderation_decisions
                WHERE id = ?
                """,
                (decisao_id,),
            ).fetchone()

            denuncia_atualizada = self._buscar_denuncia(
                conexao,
                denuncia_id=denuncia,
            )

            if decisao_linha is None or denuncia_atualizada is None:
                raise RuntimeError("Persistencia de decisao " "ficou inconsistente.")

            conexao.commit()

            return ResultadoRegistroDecisaoCommunityModeration(
                decisao=(self._decisao_da_linha(decisao_linha)),
                denuncia=(self._denuncia_da_linha(denuncia_atualizada)),
                criado=True,
            )

        except Exception:
            conexao.rollback()
            raise

        finally:
            conexao.close()
