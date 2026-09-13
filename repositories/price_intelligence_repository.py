from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from statistics import median

from models.price_intelligence import (
    PrecoAtualCanonico,
    SnapshotPriceIntelligence,
)


class PriceIntelligenceRepository:
    def __init__(
        self,
        caminho_banco: str | Path = "database/price_intelligence.sqlite3",
    ) -> None:
        self.caminho_banco = Path(caminho_banco)
        self.caminho_banco.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar()

    @contextmanager
    def _conectar(
        self,
    ) -> Iterator[sqlite3.Connection]:
        conexao = sqlite3.connect(
            self.caminho_banco,
            timeout=10,
        )
        conexao.row_factory = sqlite3.Row

        try:
            yield conexao
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        finally:
            conexao.close()

    def _inicializar(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS price_intelligence_estado (
                    chave_canonica TEXT NOT NULL,
                    marketplace TEXT NOT NULL,
                    identificador TEXT NOT NULL,
                    nome_canonico TEXT NOT NULL,
                    preco_atual REAL NOT NULL,
                    link TEXT NOT NULL,
                    primeiro_observado_em TEXT NOT NULL,
                    ultimo_observado_em TEXT NOT NULL,
                    PRIMARY KEY (
                        chave_canonica,
                        marketplace,
                        identificador
                    ),
                    UNIQUE (
                        marketplace,
                        identificador
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_price_estado_canonico
                ON price_intelligence_estado (
                    chave_canonica,
                    marketplace,
                    preco_atual
                );

                CREATE TABLE IF NOT EXISTS price_intelligence_historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chave_canonica TEXT NOT NULL,
                    marketplace TEXT NOT NULL,
                    identificador TEXT NOT NULL,
                    nome_canonico TEXT NOT NULL,
                    preco REAL NOT NULL,
                    observado_em TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_price_historico_canonico
                ON price_intelligence_historico (
                    chave_canonica,
                    observado_em DESC,
                    id DESC
                );

                CREATE INDEX IF NOT EXISTS idx_price_historico_listing
                ON price_intelligence_historico (
                    marketplace,
                    identificador,
                    observado_em DESC,
                    id DESC
                );
                """)

    def registrar_observacao(
        self,
        *,
        chave_canonica: str,
        nome_canonico: str,
        marketplace: str,
        identificador: str,
        preco: float,
        link: str,
        observado_em: str,
    ) -> tuple[str, bool]:
        with self._conectar() as conexao:
            conflito = conexao.execute(
                """
                SELECT chave_canonica
                FROM price_intelligence_estado
                WHERE marketplace = ?
                  AND identificador = ?
                LIMIT 1
                """,
                (
                    marketplace,
                    identificador,
                ),
            ).fetchone()

            if conflito is not None and str(conflito["chave_canonica"]) != chave_canonica:
                return (
                    "conflito_identidade",
                    False,
                )

            existente = conexao.execute(
                """
                SELECT preco_atual
                FROM price_intelligence_estado
                WHERE chave_canonica = ?
                  AND marketplace = ?
                  AND identificador = ?
                LIMIT 1
                """,
                (
                    chave_canonica,
                    marketplace,
                    identificador,
                ),
            ).fetchone()

            if existente is None:
                conexao.execute(
                    """
                    INSERT INTO price_intelligence_estado (
                        chave_canonica,
                        marketplace,
                        identificador,
                        nome_canonico,
                        preco_atual,
                        link,
                        primeiro_observado_em,
                        ultimo_observado_em
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chave_canonica,
                        marketplace,
                        identificador,
                        nome_canonico,
                        float(preco),
                        link,
                        observado_em,
                        observado_em,
                    ),
                )

                self._registrar_evento(
                    conexao=conexao,
                    chave_canonica=chave_canonica,
                    nome_canonico=nome_canonico,
                    marketplace=marketplace,
                    identificador=identificador,
                    preco=preco,
                    observado_em=observado_em,
                )

                return (
                    "preco_inicial_registrado",
                    True,
                )

            preco_anterior = float(existente["preco_atual"])
            mudou = abs(preco_anterior - float(preco)) > 0.000001

            conexao.execute(
                """
                UPDATE price_intelligence_estado
                SET
                    nome_canonico = ?,
                    preco_atual = ?,
                    link = ?,
                    ultimo_observado_em = ?
                WHERE chave_canonica = ?
                  AND marketplace = ?
                  AND identificador = ?
                """,
                (
                    nome_canonico,
                    float(preco),
                    link,
                    observado_em,
                    chave_canonica,
                    marketplace,
                    identificador,
                ),
            )

            if not mudou:
                return (
                    "preco_confirmado_sem_mudanca",
                    False,
                )

            self._registrar_evento(
                conexao=conexao,
                chave_canonica=chave_canonica,
                nome_canonico=nome_canonico,
                marketplace=marketplace,
                identificador=identificador,
                preco=preco,
                observado_em=observado_em,
            )

            return (
                "preco_alterado",
                True,
            )

    def _registrar_evento(
        self,
        *,
        conexao: sqlite3.Connection,
        chave_canonica: str,
        nome_canonico: str,
        marketplace: str,
        identificador: str,
        preco: float,
        observado_em: str,
    ) -> None:
        conexao.execute(
            """
            INSERT INTO price_intelligence_historico (
                chave_canonica,
                marketplace,
                identificador,
                nome_canonico,
                preco,
                observado_em
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chave_canonica,
                marketplace,
                identificador,
                nome_canonico,
                float(preco),
                observado_em,
            ),
        )

    def listar_precos_atuais(
        self,
        chave_canonica: str,
    ) -> list[PrecoAtualCanonico]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    chave_canonica,
                    marketplace,
                    identificador,
                    nome_canonico,
                    preco_atual,
                    link,
                    primeiro_observado_em,
                    ultimo_observado_em
                FROM price_intelligence_estado
                WHERE chave_canonica = ?
                ORDER BY preco_atual ASC, marketplace, identificador
                """,
                (chave_canonica,),
            ).fetchall()

        return [
            PrecoAtualCanonico(
                chave_canonica=str(linha["chave_canonica"]),
                marketplace=str(linha["marketplace"]),
                identificador=str(linha["identificador"]),
                nome_canonico=str(linha["nome_canonico"]),
                preco_atual=float(linha["preco_atual"]),
                link=str(linha["link"]),
                primeiro_observado_em=str(linha["primeiro_observado_em"]),
                ultimo_observado_em=str(linha["ultimo_observado_em"]),
            )
            for linha in linhas
        ]

    def listar_historico(
        self,
        chave_canonica: str,
        *,
        limite: int = 500,
    ) -> list[dict[str, object]]:
        limite_norm = max(
            1,
            min(
                int(limite),
                5000,
            ),
        )

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    id,
                    chave_canonica,
                    marketplace,
                    identificador,
                    nome_canonico,
                    preco,
                    observado_em
                FROM price_intelligence_historico
                WHERE chave_canonica = ?
                ORDER BY observado_em DESC, id DESC
                LIMIT ?
                """,
                (
                    chave_canonica,
                    limite_norm,
                ),
            ).fetchall()

        return [dict(linha) for linha in linhas]

    def obter_snapshot(
        self,
        chave_canonica: str,
    ) -> SnapshotPriceIntelligence | None:
        atuais = self.listar_precos_atuais(chave_canonica)

        if not atuais:
            return None

        historico = self.listar_historico(
            chave_canonica,
            limite=5000,
        )

        precos_atuais = [item.preco_atual for item in atuais]
        precos_historicos = [float(item["preco"]) for item in historico]

        melhor = min(
            atuais,
            key=lambda item: (
                item.preco_atual,
                item.marketplace,
                item.identificador,
            ),
        )

        atualizado_em = max(item.ultimo_observado_em for item in atuais)

        return SnapshotPriceIntelligence(
            chave_canonica=chave_canonica,
            nome_canonico=melhor.nome_canonico,
            preco_minimo_atual=min(precos_atuais),
            preco_maximo_atual=max(precos_atuais),
            mediana_atual=float(median(precos_atuais)),
            marketplace_melhor_preco=melhor.marketplace,
            identificador_melhor_preco=melhor.identificador,
            anuncios_observados=len(atuais),
            marketplaces_observados=tuple(sorted({item.marketplace for item in atuais})),
            menor_preco_historico=min(precos_historicos),
            mediana_historica=float(median(precos_historicos)),
            observacoes_historicas=len(precos_historicos),
            atualizado_em=atualizado_em,
        )

    def quantidade_produtos(self) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(
                    DISTINCT chave_canonica
                ) AS total
                FROM price_intelligence_estado
                """).fetchone()

        return int(linha["total"])

    def quantidade_anuncios(self) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(*) AS total
                FROM price_intelligence_estado
                """).fetchone()

        return int(linha["total"])

    def quantidade_observacoes(self) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(*) AS total
                FROM price_intelligence_historico
                """).fetchone()

        return int(linha["total"])

    def obter_metricas(self) -> dict[str, object]:
        with self._conectar() as conexao:
            distribuicao = conexao.execute("""
                SELECT
                    marketplace,
                    COUNT(*) AS total
                FROM price_intelligence_estado
                GROUP BY marketplace
                ORDER BY total DESC, marketplace
                """).fetchall()

            multi = conexao.execute("""
                SELECT COUNT(*) AS total
                FROM (
                    SELECT chave_canonica
                    FROM price_intelligence_estado
                    GROUP BY chave_canonica
                    HAVING COUNT(
                        DISTINCT marketplace
                    ) >= 2
                )
                """).fetchone()

        return {
            "produtos": self.quantidade_produtos(),
            "anuncios": self.quantidade_anuncios(),
            "observacoes": self.quantidade_observacoes(),
            "produtos_multi_marketplace": int(multi["total"]),
            "marketplaces": {
                str(linha["marketplace"]): int(linha["total"]) for linha in distribuicao
            },
        }
