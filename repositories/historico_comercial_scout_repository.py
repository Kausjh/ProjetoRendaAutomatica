# 63.8738, -149.7525

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from models.perfil_comercial_scout import (
    PerfilComercialScout,
)
from models.tendencia_comercial_scout import (
    ObservacaoComercialScout,
)


class HistoricoComercialScoutRepository:
    """
    Historico append-only de eventos comerciais do Scout.

    O banco registra quando um sinal comercial foi efetivamente
    observado como novo ou atualizado.

    Este repository nao representa historico de preco.
    """

    def __init__(
        self,
        caminho_arquivo: str | Path = ("database/historico_comercial_scout.sqlite3"),
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)

        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._criar_estrutura()

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_arquivo,
            timeout=15,
        )

        conexao.row_factory = sqlite3.Row

        conexao.execute("PRAGMA journal_mode=WAL")

        conexao.execute("PRAGMA synchronous=NORMAL")

        return conexao

    def _criar_estrutura(
        self,
    ) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS
                historico_comercial_scout (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    fonte TEXT NOT NULL,
                    id_externo TEXT NOT NULL,

                    tipo_evento TEXT NOT NULL,

                    perfil_json TEXT NOT NULL,

                    observado_em TEXT NOT NULL,

                    criado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS
                idx_historico_comercial_scout_observado
                ON historico_comercial_scout (
                    observado_em
                );

                CREATE INDEX IF NOT EXISTS
                idx_historico_comercial_scout_sinal
                ON historico_comercial_scout (
                    fonte,
                    id_externo,
                    observado_em
                );
                """)

    def registrar(
        self,
        *,
        perfil: PerfilComercialScout,
        tipo_evento: str,
        observado_em: datetime,
    ) -> int:
        instante = self._normalizar_data(observado_em)

        dados = asdict(perfil)

        payload = json.dumps(
            dados,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                INSERT INTO historico_comercial_scout (
                    fonte,
                    id_externo,
                    tipo_evento,
                    perfil_json,
                    observado_em
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(perfil.fonte or "").strip(),
                    str(perfil.id_externo or "").strip(),
                    str(tipo_evento or "").strip(),
                    payload,
                    instante.isoformat(),
                ),
            )

            identificador = cursor.lastrowid

        if identificador is None:
            raise RuntimeError("Historico comercial nao retornou id.")

        return int(identificador)

    def listar_observacoes(
        self,
        *,
        inicio: datetime | None = None,
        fim: datetime | None = None,
    ) -> list[ObservacaoComercialScout]:
        parametros: list[str] = []

        filtros = []

        if inicio is not None:
            inicio_normalizado = self._normalizar_data(inicio)

            filtros.append("observado_em >= ?")

            parametros.append(inicio_normalizado.isoformat())

        if fim is not None:
            fim_normalizado = self._normalizar_data(fim)

            filtros.append("observado_em <= ?")

            parametros.append(fim_normalizado.isoformat())

        where = ""

        if filtros:
            where = " WHERE " + " AND ".join(filtros)

        consulta = (
            """
            SELECT
                perfil_json,
                observado_em
            FROM historico_comercial_scout
            """
            + where
            + """
            ORDER BY
                observado_em,
                id
            """
        )

        with self._conectar() as conexao:
            linhas = conexao.execute(
                consulta,
                tuple(parametros),
            ).fetchall()

        return [
            ObservacaoComercialScout(
                perfil=self._reconstruir_perfil(linha["perfil_json"]),
                observado_em=(self._ler_data(linha["observado_em"])),
            )
            for linha in linhas
        ]

    def quantidade(
        self,
    ) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(*) AS total
                FROM historico_comercial_scout
                """).fetchone()

        return int(linha["total"])

    @staticmethod
    def _reconstruir_perfil(
        payload: str,
    ) -> PerfilComercialScout:
        dados = json.loads(payload)

        if not isinstance(
            dados,
            dict,
        ):
            raise ValueError("Perfil comercial persistido invalido.")

        for campo in (
            "regioes",
            "termos_descoberta",
            "dimensoes",
            "evidencias",
        ):
            valor = dados.get(campo)

            if valor is None:
                dados[campo] = ()

            elif isinstance(
                valor,
                list,
            ):
                dados[campo] = tuple(valor)

        return PerfilComercialScout(**dados)

    @staticmethod
    def _normalizar_data(
        valor: datetime,
    ) -> datetime:
        if not isinstance(
            valor,
            datetime,
        ):
            raise TypeError("observado_em deve ser datetime.")

        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError("observado_em deve possuir timezone.")

        return valor.astimezone(UTC)

    @staticmethod
    def _ler_data(
        valor: str,
    ) -> datetime:
        instante = datetime.fromisoformat(str(valor))

        if instante.tzinfo is None or instante.utcoffset() is None:
            raise ValueError("Timestamp persistido sem timezone.")

        return instante.astimezone(UTC)
