from __future__ import annotations

import sqlite3
from pathlib import Path


class CommunityModerationReadService:
    MAX_LIMITE = 100
    MAX_DECISOES_DETALHE = 500

    def __init__(
        self,
        caminho_banco: str | Path,
    ) -> None:
        self.caminho_banco = Path(caminho_banco)

        if not self.caminho_banco.is_file():
            raise FileNotFoundError(
                "Banco de Community Moderation " f"ausente: {self.caminho_banco}"
            )

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        uri = self.caminho_banco.resolve().as_uri() + "?mode=ro"

        conexao = sqlite3.connect(
            uri,
            uri=True,
            timeout=30,
        )

        conexao.row_factory = sqlite3.Row

        conexao.execute("PRAGMA query_only = ON")

        conexao.execute("PRAGMA foreign_keys = ON")

        return conexao

    @classmethod
    def _limite(
        cls,
        valor: object,
    ) -> int:
        try:
            limite = int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError("limite precisa ser inteiro.") from erro

        if limite < 1:
            raise ValueError("limite precisa ser positivo.")

        return min(
            limite,
            cls.MAX_LIMITE,
        )

    @staticmethod
    def _offset(
        valor: object,
    ) -> int:
        try:
            offset = int(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError("offset precisa ser inteiro.") from erro

        if offset < 0:
            raise ValueError("offset nao pode ser negativo.")

        return offset

    @staticmethod
    def _denuncia(
        linha: sqlite3.Row,
    ) -> dict[str, object]:
        return {
            "id": str(linha["id"]),
            "reporter_conta_id": str(linha["reporter_conta_id"]),
            "target_type": str(linha["target_type"]),
            "target_id": str(linha["target_id"]),
            "motivo": str(linha["motivo"]),
            "detalhes": (str(linha["detalhes"]) if linha["detalhes"] is not None else None),
            "estado": str(linha["estado"]),
            "criado_em": str(linha["criado_em"]),
            "atualizado_em": str(linha["atualizado_em"]),
        }

    @staticmethod
    def _decisao(
        linha: sqlite3.Row,
    ) -> dict[str, object]:
        return {
            "id": str(linha["id"]),
            "denuncia_id": str(linha["denuncia_id"]),
            "moderator_actor_id": str(linha["moderator_actor_id"]),
            "resultado": str(linha["resultado"]),
            "familia_abuso_confirmado": (
                str(linha["familia_abuso_confirmado"])
                if (linha["familia_abuso_confirmado"] is not None)
                else None
            ),
            "justificativa": (
                str(linha["justificativa"]) if linha["justificativa"] is not None else None
            ),
            "ocorrido_em": str(linha["ocorrido_em"]),
        }

    def listar_pendentes(
        self,
        *,
        limite: object = 50,
        offset: object = 0,
    ) -> dict[str, object]:
        limite_normalizado = self._limite(limite)

        offset_normalizado = self._offset(offset)

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    reporter_conta_id,
                    target_type,
                    target_id,
                    motivo,
                    detalhes,
                    estado,
                    criado_em,
                    atualizado_em
                FROM community_moderation_reports
                WHERE estado IN (
                    'received',
                    'under_review'
                )
                ORDER BY
                    criado_em ASC,
                    id ASC
                LIMIT ? OFFSET ?
                """,
                (
                    limite_normalizado,
                    offset_normalizado,
                ),
            ).fetchall()

        itens = [self._denuncia(linha) for linha in linhas]

        return {
            "api_version": "v1",
            "recurso": ("moderation_reports_pending"),
            "limite": limite_normalizado,
            "offset": offset_normalizado,
            "quantidade": len(itens),
            "itens": itens,
        }

    def obter_denuncia(
        self,
        denuncia_id: object,
    ) -> dict[str, object] | None:
        identificador = str(denuncia_id if denuncia_id is not None else "").strip()

        if not identificador:
            raise ValueError("denuncia_id e obrigatorio.")

        with self._conectar() as conexao:
            denuncia = conexao.execute(
                """
                SELECT
                    id,
                    reporter_conta_id,
                    target_type,
                    target_id,
                    motivo,
                    detalhes,
                    estado,
                    criado_em,
                    atualizado_em
                FROM community_moderation_reports
                WHERE id = ?
                """,
                (identificador,),
            ).fetchone()

            if denuncia is None:
                return None

            decisoes = conexao.execute(
                """
                SELECT
                    id,
                    denuncia_id,
                    moderator_actor_id,
                    resultado,
                    familia_abuso_confirmado,
                    justificativa,
                    ocorrido_em
                FROM community_moderation_decisions
                WHERE denuncia_id = ?
                ORDER BY
                    ocorrido_em ASC,
                    id ASC
                LIMIT ?
                """,
                (
                    identificador,
                    self.MAX_DECISOES_DETALHE,
                ),
            ).fetchall()

        return {
            "api_version": "v1",
            "recurso": "moderation_report",
            "denuncia": self._denuncia(denuncia),
            "decisoes": [self._decisao(linha) for linha in decisoes],
        }
