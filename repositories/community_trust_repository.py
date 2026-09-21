from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from models.community_trust import (
    EvidenciaCommunityTrust,
    PerfilCommunityTrust,
    ResultadoRegistroCommunityTrust,
)

CLASSIFICACOES_VALIDAS = frozenset(
    {
        "positive",
        "negative",
        "neutral",
    }
)


class ConflitoIdempotenciaCommunityTrust(ValueError):
    pass


class CommunityTrustRepository:
    def __init__(self, caminho_banco: str | Path) -> None:
        self.caminho_banco = Path(caminho_banco)
        self.caminho_banco.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._garantir_schema()

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self.caminho_banco)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        return conexao

    def _garantir_schema(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS
                    community_trust_profiles (
                        conta_id TEXT PRIMARY KEY,

                        evidencias_total INTEGER NOT NULL
                            DEFAULT 0
                            CHECK (evidencias_total >= 0),

                        positivas_total INTEGER NOT NULL
                            DEFAULT 0
                            CHECK (positivas_total >= 0),

                        negativas_total INTEGER NOT NULL
                            DEFAULT 0
                            CHECK (negativas_total >= 0),

                        neutras_total INTEGER NOT NULL
                            DEFAULT 0
                            CHECK (neutras_total >= 0),

                        atualizado_em TEXT NOT NULL,

                        CHECK (
                            evidencias_total =
                                positivas_total
                                + negativas_total
                                + neutras_total
                        ),

                        FOREIGN KEY (conta_id)
                            REFERENCES contas_usuario(id)
                            ON DELETE CASCADE
                    );

                CREATE TABLE IF NOT EXISTS
                    community_trust_evidence (
                        id TEXT PRIMARY KEY,

                        conta_id TEXT NOT NULL,

                        chave_idempotencia TEXT NOT NULL,

                        tipo_evidencia TEXT NOT NULL,

                        classificacao TEXT NOT NULL
                            CHECK (
                                classificacao IN (
                                    'positive',
                                    'negative',
                                    'neutral'
                                )
                            ),

                        origem TEXT NOT NULL,

                        origem_id TEXT NOT NULL,

                        motivo TEXT,

                        politica_versao TEXT,

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
                    idx_community_trust_evidence_account_time
                    ON community_trust_evidence(
                        conta_id,
                        ocorrido_em DESC,
                        id DESC
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_community_trust_evidence_origin
                    ON community_trust_evidence(
                        conta_id,
                        origem,
                        origem_id
                    );

                CREATE INDEX IF NOT EXISTS
                    idx_community_trust_evidence_classification
                    ON community_trust_evidence(
                        conta_id,
                        classificacao,
                        ocorrido_em DESC
                    );
                """)

    @staticmethod
    def _obrigatorio(
        valor: object,
        campo: str,
    ) -> str:
        normalizado = str(valor or "").strip()

        if not normalizado:
            raise ValueError(campo + " nao pode ser vazio.")

        return normalizado

    @staticmethod
    def _opcional(
        valor: object | None,
    ) -> str | None:
        if valor is None:
            return None

        normalizado = str(valor).strip()
        return normalizado or None

    @staticmethod
    def _evidencia_da_linha(
        linha: sqlite3.Row,
    ) -> EvidenciaCommunityTrust:
        metadados = json.loads(str(linha["metadados_json"]))

        if not isinstance(metadados, dict):
            raise ValueError("metadados_json precisa representar objeto.")

        return EvidenciaCommunityTrust(
            id=str(linha["id"]),
            conta_id=str(linha["conta_id"]),
            chave_idempotencia=str(linha["chave_idempotencia"]),
            tipo_evidencia=str(linha["tipo_evidencia"]),
            classificacao=str(linha["classificacao"]),
            origem=str(linha["origem"]),
            origem_id=str(linha["origem_id"]),
            motivo=(str(linha["motivo"]) if linha["motivo"] is not None else None),
            politica_versao=(
                str(linha["politica_versao"]) if linha["politica_versao"] is not None else None
            ),
            metadados=dict(metadados),
            ocorrido_em=str(linha["ocorrido_em"]),
            criado_em=str(linha["criado_em"]),
        )

    @staticmethod
    def _perfil_da_linha(
        linha: sqlite3.Row,
    ) -> PerfilCommunityTrust:
        return PerfilCommunityTrust(
            conta_id=str(linha["conta_id"]),
            evidencias_total=int(linha["evidencias_total"]),
            positivas_total=int(linha["positivas_total"]),
            negativas_total=int(linha["negativas_total"]),
            neutras_total=int(linha["neutras_total"]),
            atualizado_em=str(linha["atualizado_em"]),
        )

    @staticmethod
    def _buscar_evidencia(
        conexao: sqlite3.Connection,
        *,
        conta_id: str,
        chave_idempotencia: str,
    ) -> sqlite3.Row | None:
        return conexao.execute(
            """
            SELECT *
            FROM community_trust_evidence
            WHERE conta_id = ?
              AND chave_idempotencia = ?
            """,
            (
                conta_id,
                chave_idempotencia,
            ),
        ).fetchone()

    @staticmethod
    def _buscar_perfil(
        conexao: sqlite3.Connection,
        conta_id: str,
    ) -> sqlite3.Row | None:
        return conexao.execute(
            """
            SELECT *
            FROM community_trust_profiles
            WHERE conta_id = ?
            """,
            (conta_id,),
        ).fetchone()

    def obter_evidencia_por_chave(
        self,
        *,
        conta_id: str,
        chave_idempotencia: str,
    ) -> EvidenciaCommunityTrust | None:
        conta = self._obrigatorio(
            conta_id,
            "conta_id",
        )
        chave = self._obrigatorio(
            chave_idempotencia,
            "chave_idempotencia",
        )

        with self._conectar() as conexao:
            linha = self._buscar_evidencia(
                conexao,
                conta_id=conta,
                chave_idempotencia=chave,
            )

        if linha is None:
            return None

        return self._evidencia_da_linha(linha)

    def obter_perfil(
        self,
        conta_id: str,
    ) -> PerfilCommunityTrust:
        conta = self._obrigatorio(
            conta_id,
            "conta_id",
        )

        with self._conectar() as conexao:
            linha = self._buscar_perfil(
                conexao,
                conta,
            )

        if linha is None:
            return PerfilCommunityTrust(
                conta_id=conta,
                evidencias_total=0,
                positivas_total=0,
                negativas_total=0,
                neutras_total=0,
                atualizado_em=None,
            )

        return self._perfil_da_linha(linha)

    def registrar_evidencia(
        self,
        *,
        conta_id: str,
        chave_idempotencia: str,
        tipo_evidencia: str,
        classificacao: str,
        origem: str,
        origem_id: str,
        motivo: str | None = None,
        politica_versao: str | None = None,
        metadados: dict[str, Any] | None = None,
        ocorrido_em: str,
    ) -> ResultadoRegistroCommunityTrust:
        conta = self._obrigatorio(
            conta_id,
            "conta_id",
        )
        chave = self._obrigatorio(
            chave_idempotencia,
            "chave_idempotencia",
        )
        tipo = self._obrigatorio(
            tipo_evidencia,
            "tipo_evidencia",
        )
        classe = self._obrigatorio(
            classificacao,
            "classificacao",
        )
        origem_normalizada = self._obrigatorio(
            origem,
            "origem",
        )
        origem_id_normalizada = self._obrigatorio(
            origem_id,
            "origem_id",
        )
        ocorrido = self._obrigatorio(
            ocorrido_em,
            "ocorrido_em",
        )

        if classe not in CLASSIFICACOES_VALIDAS:
            raise ValueError("classificacao invalida.")

        motivo_normalizado = self._opcional(motivo)
        politica_normalizada = self._opcional(politica_versao)

        metadados_normalizados = dict(metadados or {})

        metadados_json = json.dumps(
            metadados_normalizados,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

        evento_id = str(uuid4())

        agora = datetime.now(UTC).isoformat(timespec="seconds")

        conexao = self._conectar()

        try:
            conexao.execute("BEGIN IMMEDIATE")

            existente = self._buscar_evidencia(
                conexao,
                conta_id=conta,
                chave_idempotencia=chave,
            )

            if existente is not None:
                esperado = (
                    tipo,
                    classe,
                    origem_normalizada,
                    origem_id_normalizada,
                    motivo_normalizado,
                    politica_normalizada,
                    metadados_json,
                    ocorrido,
                )

                encontrado = (
                    str(existente["tipo_evidencia"]),
                    str(existente["classificacao"]),
                    str(existente["origem"]),
                    str(existente["origem_id"]),
                    (str(existente["motivo"]) if existente["motivo"] is not None else None),
                    (
                        str(existente["politica_versao"])
                        if existente["politica_versao"] is not None
                        else None
                    ),
                    str(existente["metadados_json"]),
                    str(existente["ocorrido_em"]),
                )

                if encontrado != esperado:
                    raise (
                        ConflitoIdempotenciaCommunityTrust(
                            "Chave de idempotencia " "reutilizada com semantica " "diferente."
                        )
                    )

                perfil_linha = self._buscar_perfil(
                    conexao,
                    conta,
                )

                if perfil_linha is None:
                    raise RuntimeError("Evidencia idempotente existe " "sem perfil materializado.")

                conexao.commit()

                return ResultadoRegistroCommunityTrust(
                    evidencia=(self._evidencia_da_linha(existente)),
                    perfil=(self._perfil_da_linha(perfil_linha)),
                    criado=False,
                )

            conexao.execute(
                """
                INSERT INTO
                    community_trust_evidence (
                        id,
                        conta_id,
                        chave_idempotencia,
                        tipo_evidencia,
                        classificacao,
                        origem,
                        origem_id,
                        motivo,
                        politica_versao,
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
                    conta,
                    chave,
                    tipo,
                    classe,
                    origem_normalizada,
                    origem_id_normalizada,
                    motivo_normalizado,
                    politica_normalizada,
                    metadados_json,
                    ocorrido,
                    agora,
                ),
            )

            positiva = int(classe == "positive")
            negativa = int(classe == "negative")
            neutra = int(classe == "neutral")

            conexao.execute(
                """
                INSERT INTO
                    community_trust_profiles (
                        conta_id,
                        evidencias_total,
                        positivas_total,
                        negativas_total,
                        neutras_total,
                        atualizado_em
                    )
                VALUES (?, 1, ?, ?, ?, ?)

                ON CONFLICT(conta_id)
                DO UPDATE SET
                    evidencias_total =
                        community_trust_profiles
                        .evidencias_total + 1,

                    positivas_total =
                        community_trust_profiles
                        .positivas_total
                        + excluded.positivas_total,

                    negativas_total =
                        community_trust_profiles
                        .negativas_total
                        + excluded.negativas_total,

                    neutras_total =
                        community_trust_profiles
                        .neutras_total
                        + excluded.neutras_total,

                    atualizado_em =
                        excluded.atualizado_em
                """,
                (
                    conta,
                    positiva,
                    negativa,
                    neutra,
                    agora,
                ),
            )

            evidencia_linha = self._buscar_evidencia(
                conexao,
                conta_id=conta,
                chave_idempotencia=chave,
            )

            perfil_linha = self._buscar_perfil(
                conexao,
                conta,
            )

            if evidencia_linha is None:
                raise RuntimeError("Evidencia desapareceu " "apos persistencia.")

            if perfil_linha is None:
                raise RuntimeError("Perfil nao foi materializado.")

            conexao.commit()

            return ResultadoRegistroCommunityTrust(
                evidencia=(self._evidencia_da_linha(evidencia_linha)),
                perfil=(self._perfil_da_linha(perfil_linha)),
                criado=True,
            )

        except Exception:
            conexao.rollback()
            raise

        finally:
            conexao.close()

    def reconstruir_perfil(
        self,
        conta_id: str,
    ) -> PerfilCommunityTrust:
        conta = self._obrigatorio(
            conta_id,
            "conta_id",
        )

        conexao = self._conectar()

        try:
            conexao.execute("BEGIN IMMEDIATE")

            linha = conexao.execute(
                """
                SELECT
                    COUNT(*) AS evidencias_total,

                    SUM(
                        CASE
                            WHEN classificacao = 'positive'
                            THEN 1
                            ELSE 0
                        END
                    ) AS positivas_total,

                    SUM(
                        CASE
                            WHEN classificacao = 'negative'
                            THEN 1
                            ELSE 0
                        END
                    ) AS negativas_total,

                    SUM(
                        CASE
                            WHEN classificacao = 'neutral'
                            THEN 1
                            ELSE 0
                        END
                    ) AS neutras_total,

                    MAX(criado_em) AS atualizado_em

                FROM community_trust_evidence
                WHERE conta_id = ?
                """,
                (conta,),
            ).fetchone()

            if linha is None:
                raise RuntimeError("Falha ao agregar ledger de Trust.")

            total = int(linha["evidencias_total"] or 0)
            positivas = int(linha["positivas_total"] or 0)
            negativas = int(linha["negativas_total"] or 0)
            neutras = int(linha["neutras_total"] or 0)

            if total == 0:
                conexao.execute(
                    """
                    DELETE FROM community_trust_profiles
                    WHERE conta_id = ?
                    """,
                    (conta,),
                )

                conexao.commit()

                return PerfilCommunityTrust(
                    conta_id=conta,
                    evidencias_total=0,
                    positivas_total=0,
                    negativas_total=0,
                    neutras_total=0,
                    atualizado_em=None,
                )

            atualizado = str(linha["atualizado_em"])

            conexao.execute(
                """
                INSERT INTO community_trust_profiles (
                    conta_id,
                    evidencias_total,
                    positivas_total,
                    negativas_total,
                    neutras_total,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?)

                ON CONFLICT(conta_id)
                DO UPDATE SET
                    evidencias_total =
                        excluded.evidencias_total,

                    positivas_total =
                        excluded.positivas_total,

                    negativas_total =
                        excluded.negativas_total,

                    neutras_total =
                        excluded.neutras_total,

                    atualizado_em =
                        excluded.atualizado_em
                """,
                (
                    conta,
                    total,
                    positivas,
                    negativas,
                    neutras,
                    atualizado,
                ),
            )

            perfil_linha = self._buscar_perfil(
                conexao,
                conta,
            )

            if perfil_linha is None:
                raise RuntimeError("Perfil nao existe apos reconstrucao.")

            conexao.commit()

            return self._perfil_da_linha(perfil_linha)

        except Exception:
            conexao.rollback()
            raise

        finally:
            conexao.close()

    def listar_evidencias(
        self,
        *,
        conta_id: str,
        limite: int = 50,
        offset: int = 0,
    ) -> list[EvidenciaCommunityTrust]:
        conta = self._obrigatorio(
            conta_id,
            "conta_id",
        )

        limite_normalizado = max(
            1,
            min(int(limite), 500),
        )
        offset_normalizado = max(
            int(offset),
            0,
        )

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM community_trust_evidence
                WHERE conta_id = ?
                ORDER BY
                    ocorrido_em DESC,
                    id DESC
                LIMIT ? OFFSET ?
                """,
                (
                    conta,
                    limite_normalizado,
                    offset_normalizado,
                ),
            ).fetchall()

        return [self._evidencia_da_linha(linha) for linha in linhas]
