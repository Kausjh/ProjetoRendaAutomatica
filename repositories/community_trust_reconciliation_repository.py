from __future__ import annotations

import sqlite3
from pathlib import Path

from models.community_discovery import (
    DescobertaComunitaria,
)


class EstadoDescobertaTerminalInvalido(ValueError):
    pass


class CommunityTrustReconciliationRepository:
    IDEMPOTENCY_PREFIX = "v1:community-discovery:"

    def __init__(
        self,
        caminho_banco: str | Path,
    ) -> None:
        self.caminho_banco = Path(caminho_banco)

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        conexao = sqlite3.connect(self.caminho_banco)

        conexao.row_factory = sqlite3.Row

        conexao.execute("PRAGMA foreign_keys = ON")

        return conexao

    @staticmethod
    def _da_linha(
        linha: sqlite3.Row,
    ) -> DescobertaComunitaria:
        discovery_id = str(linha["id"] or "").strip()

        conta_id = str(linha["conta_id"] or "").strip()

        status = str(linha["status"] or "").strip()

        atualizado_em = str(linha["atualizado_em"] or "").strip()

        if not discovery_id:
            raise EstadoDescobertaTerminalInvalido("Terminal sem id.")

        if not conta_id:
            raise EstadoDescobertaTerminalInvalido("Terminal sem conta_id.")

        if status not in {
            "approved",
            "rejected",
        }:
            raise EstadoDescobertaTerminalInvalido("Linha de reconciliacao " "nao esta terminal.")

        if not atualizado_em:
            raise EstadoDescobertaTerminalInvalido("Terminal sem atualizado_em.")

        return DescobertaComunitaria(
            id=discovery_id,
            conta_id=conta_id,
            url=str(linha["url"]),
            url_normalizada=str(linha["url_normalizada"]),
            marketplace=(str(linha["marketplace"]) if linha["marketplace"] is not None else None),
            status=status,
            tentativas=int(linha["tentativas"]),
            disponivel_em=str(linha["disponivel_em"]),
            processando_desde=(
                str(linha["processando_desde"]) if linha["processando_desde"] is not None else None
            ),
            motivo_status=(
                str(linha["motivo_status"]) if linha["motivo_status"] is not None else None
            ),
            canonical_key=(
                str(linha["canonical_key"]) if linha["canonical_key"] is not None else None
            ),
            criado_em=str(linha["criado_em"]),
            atualizado_em=atualizado_em,
        )

    @staticmethod
    def _limite(
        limite: int,
    ) -> int:
        valor = int(limite)

        if valor < 1:
            raise ValueError("limite precisa ser positivo.")

        return min(
            valor,
            5000,
        )

    def contar_terminais_sem_evidencia(
        self,
    ) -> int:
        with self._conectar() as conexao:
            return int(
                conexao.execute(
                    """
                    SELECT COUNT(*)
                    FROM community_discoveries
                        AS discovery
                    WHERE discovery.status
                        IN (
                            'approved',
                            'rejected'
                        )
                      AND NOT EXISTS (
                            SELECT 1
                            FROM community_trust_evidence
                                AS evidence
                            WHERE
                                evidence.conta_id
                                    = discovery.conta_id
                              AND
                                evidence.chave_idempotencia
                                    = (
                                        ?
                                        || discovery.id
                                    )
                        )
                    """,
                    (self.IDEMPOTENCY_PREFIX,),
                ).fetchone()[0]
            )

    def listar_terminais_sem_evidencia(
        self,
        *,
        limite: int = 500,
    ) -> list[DescobertaComunitaria]:
        limite_seguro = self._limite(limite)

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT discovery.*
                FROM community_discoveries
                    AS discovery
                WHERE discovery.status
                    IN (
                        'approved',
                        'rejected'
                    )
                  AND NOT EXISTS (
                        SELECT 1
                        FROM community_trust_evidence
                            AS evidence
                        WHERE
                            evidence.conta_id
                                = discovery.conta_id
                          AND
                            evidence.chave_idempotencia
                                = (
                                    ?
                                    || discovery.id
                                )
                    )
                ORDER BY
                    discovery.atualizado_em ASC,
                    discovery.id ASC
                LIMIT ?
                """,
                (
                    self.IDEMPOTENCY_PREFIX,
                    limite_seguro,
                ),
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]
