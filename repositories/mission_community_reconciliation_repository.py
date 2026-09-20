from __future__ import annotations

import sqlite3
from pathlib import Path

from models.mission_community import (
    DescobertaAprovadaParaMissao,
)


class EstadoDescobertaAprovadaInvalido(ValueError):
    pass


class MissionCommunityReconciliationRepository:
    def __init__(
        self,
        caminho_banco: str | Path,
    ) -> None:
        self.caminho_banco = Path(caminho_banco)

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

    @staticmethod
    def _da_linha(
        linha: sqlite3.Row,
    ) -> DescobertaAprovadaParaMissao:
        descoberta_id = str(linha["id"] or "").strip()

        conta_id = str(linha["conta_id"] or "").strip()

        status = str(linha["status"] or "").strip()

        ocorrido_em = str(linha["atualizado_em"] or "").strip()

        if not descoberta_id:
            raise EstadoDescobertaAprovadaInvalido("Approved sem id.")

        if not conta_id:
            raise EstadoDescobertaAprovadaInvalido("Approved sem conta_id.")

        if status != "approved":
            raise EstadoDescobertaAprovadaInvalido("Linha de reconciliacao " "nao esta approved.")

        if not ocorrido_em:
            raise EstadoDescobertaAprovadaInvalido("Approved sem atualizado_em.")

        return DescobertaAprovadaParaMissao(
            id=descoberta_id,
            conta_id=conta_id,
            status=status,
            ocorrido_em=ocorrido_em,
        )

    def listar_aprovadas(
        self,
        *,
        limite: int = 500,
        offset: int = 0,
    ) -> list[DescobertaAprovadaParaMissao]:
        limite_seguro = max(
            1,
            min(
                int(limite),
                1000,
            ),
        )

        offset_seguro = max(
            0,
            int(offset),
        )

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    conta_id,
                    status,
                    atualizado_em
                FROM community_discoveries
                WHERE status = 'approved'
                ORDER BY criado_em ASC, id ASC
                LIMIT ?
                OFFSET ?
                """,
                (
                    limite_seguro,
                    offset_seguro,
                ),
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]
