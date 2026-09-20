from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ContaHistoricaGamificacao:
    conta_id: str
    criado_em: str


@dataclass(frozen=True, slots=True)
class ItemWatchlistHistoricoGamificacao:
    canonical_key: str
    criado_em: str
    atualizado_em: str
    possui_preco_alvo: bool


class GamificationReconciliationRepository:
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
        return conexao

    def listar_contas_ativas(
        self,
    ) -> tuple[
        ContaHistoricaGamificacao,
        ...,
    ]:
        with self._conectar() as conexao:
            linhas = conexao.execute("""
                SELECT
                    id,
                    criado_em
                FROM contas_usuario
                WHERE ativa = 1
                ORDER BY criado_em ASC, id ASC
                """).fetchall()

        return tuple(
            ContaHistoricaGamificacao(
                conta_id=str(linha["id"]),
                criado_em=str(linha["criado_em"]),
            )
            for linha in linhas
        )

    def obter_primeiro_dispositivo_em(
        self,
        conta_id: str,
    ) -> str | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT criado_em
                FROM dispositivos_usuario
                WHERE conta_id = ?
                ORDER BY criado_em ASC, id ASC
                LIMIT 1
                """,
                (conta_id,),
            ).fetchone()

        if linha is None:
            return None

        return str(linha["criado_em"])

    def obter_preferencias_em(
        self,
        conta_id: str,
    ) -> str | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT atualizado_em
                FROM preferencias_usuario
                WHERE conta_id = ?
                LIMIT 1
                """,
                (conta_id,),
            ).fetchone()

        if linha is None:
            return None

        return str(linha["atualizado_em"])

    def listar_watchlist(
        self,
        conta_id: str,
    ) -> tuple[
        ItemWatchlistHistoricoGamificacao,
        ...,
    ]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    canonical_key,
                    criado_em,
                    atualizado_em,
                    preco_alvo_centavos
                FROM watchlist_usuario
                WHERE conta_id = ?
                ORDER BY criado_em ASC, id ASC
                """,
                (conta_id,),
            ).fetchall()

        return tuple(
            ItemWatchlistHistoricoGamificacao(
                canonical_key=str(linha["canonical_key"]),
                criado_em=str(linha["criado_em"]),
                atualizado_em=str(linha["atualizado_em"]),
                possui_preco_alvo=(linha["preco_alvo_centavos"] is not None),
            )
            for linha in linhas
        )
