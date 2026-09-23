from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from models.community_trust import (
    PerfilCommunityTrust,
)


class CommunityTrustReadOnlyRepository:
    """Strict read-only projection repository for User-Facing Trust."""

    def __init__(
        self,
        caminho_banco: str | Path,
    ) -> None:
        self.caminho_banco = Path(caminho_banco)

    @staticmethod
    def _obrigatorio(
        valor: object,
        campo: str,
    ) -> str:
        normalizado = str(valor or "").strip()

        if not normalizado:
            raise ValueError(campo + " nao pode ser vazio.")

        return normalizado

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        caminho = self.caminho_banco.resolve()

        conexao = sqlite3.connect(
            caminho.as_uri() + "?mode=ro",
            uri=True,
            timeout=30,
        )

        conexao.row_factory = sqlite3.Row

        conexao.execute("PRAGMA query_only = ON")

        conexao.execute("PRAGMA foreign_keys = ON")

        if int(conexao.execute("PRAGMA query_only").fetchone()[0]) != 1:
            conexao.close()

            raise sqlite3.OperationalError("SQLite query_only nao foi ativado.")

        return conexao

    def obter_perfil(
        self,
        conta_id: str,
    ) -> PerfilCommunityTrust:
        conta = self._obrigatorio(
            conta_id,
            "conta_id",
        )

        with closing(self._conectar()) as conexao:
            linha = conexao.execute(
                """
                SELECT
                    conta_id,
                    evidencias_total,
                    positivas_total,
                    negativas_total,
                    neutras_total,
                    atualizado_em
                FROM community_trust_profiles
                WHERE conta_id = ?
                """,
                (conta,),
            ).fetchone()

        if linha is None:
            return PerfilCommunityTrust(
                conta_id=conta,
                evidencias_total=0,
                positivas_total=0,
                negativas_total=0,
                neutras_total=0,
                atualizado_em=None,
            )

        return PerfilCommunityTrust(
            conta_id=str(linha["conta_id"]),
            evidencias_total=int(linha["evidencias_total"]),
            positivas_total=int(linha["positivas_total"]),
            negativas_total=int(linha["negativas_total"]),
            neutras_total=int(linha["neutras_total"]),
            atualizado_em=(
                str(linha["atualizado_em"]) if linha["atualizado_em"] is not None else None
            ),
        )
