from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from models.alert_engine import (
    TIPO_MUDANCA_PRECO,
    TIPO_NOVO_MENOR_PRECO_HISTORICO,
)

_EPSILON = 0.000001


class AlertEngineRepository:
    def __init__(
        self,
        caminho_arquivo: str | Path = "database/alert_engine.sqlite3",
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)
        self.caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar()

    @contextmanager
    def _conectar(self) -> Iterator[sqlite3.Connection]:
        conexao = sqlite3.connect(self.caminho_arquivo)
        conexao.row_factory = sqlite3.Row
        try:
            yield conexao
        finally:
            conexao.close()

    def _inicializar(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS alert_engine_estado_listing (
                    marketplace TEXT NOT NULL,
                    identificador TEXT NOT NULL,
                    chave_canonica TEXT NOT NULL,
                    nome_canonico TEXT NOT NULL,
                    preco_atual REAL NOT NULL,
                    versao INTEGER NOT NULL DEFAULT 0,
                    atualizado_em TEXT NOT NULL,
                    PRIMARY KEY (marketplace, identificador)
                );

                CREATE INDEX IF NOT EXISTS idx_alert_listing_canonico
                ON alert_engine_estado_listing (
                    chave_canonica,
                    marketplace,
                    identificador
                );

                CREATE TABLE IF NOT EXISTS alert_engine_estado_canonico (
                    chave_canonica TEXT PRIMARY KEY,
                    nome_canonico TEXT NOT NULL,
                    menor_preco_historico REAL NOT NULL,
                    versao INTEGER NOT NULL DEFAULT 0,
                    atualizado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS alert_engine_eventos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL UNIQUE,
                    tipo TEXT NOT NULL,
                    chave_canonica TEXT NOT NULL,
                    nome_canonico TEXT NOT NULL,
                    marketplace TEXT NOT NULL,
                    identificador TEXT NOT NULL,
                    preco_atual REAL NOT NULL,
                    preco_anterior REAL,
                    referencia_anterior REAL,
                    direcao TEXT,
                    variacao_percentual REAL,
                    versao INTEGER NOT NULL,
                    criado_em TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_alert_eventos_canonico
                ON alert_engine_eventos (chave_canonica, id DESC);

                CREATE INDEX IF NOT EXISTS idx_alert_eventos_tipo
                ON alert_engine_eventos (tipo, id DESC);
                """)
            conexao.commit()

    def processar_observacao(
        self,
        *,
        chave_canonica: str,
        nome_canonico: str,
        marketplace: str,
        identificador: str,
        preco_atual: float,
        menor_preco_historico: float,
        observado_em: str | None = None,
    ) -> dict[str, object]:
        agora = observado_em or datetime.now(UTC).isoformat()

        with self._conectar() as conexao:
            conexao.execute("BEGIN IMMEDIATE")

            listing = conexao.execute(
                """
                SELECT chave_canonica, preco_atual, versao
                FROM alert_engine_estado_listing
                WHERE marketplace = ? AND identificador = ?
                """,
                (marketplace, identificador),
            ).fetchone()
            canonico = conexao.execute(
                """
                SELECT menor_preco_historico, versao
                FROM alert_engine_estado_canonico
                WHERE chave_canonica = ?
                """,
                (chave_canonica,),
            ).fetchone()

            if listing is not None and str(listing["chave_canonica"]) != chave_canonica:
                conexao.rollback()
                return {
                    "status": "conflito_identidade",
                    "baseline_inicializada": False,
                    "alertas_gerados": 0,
                    "tipos_gerados": (),
                }

            baseline_listing = listing is None
            baseline_canonico = canonico is None

            preco_anterior = None if listing is None else float(listing["preco_atual"])
            versao_listing = 0 if listing is None else int(listing["versao"])
            menor_anterior = None if canonico is None else float(canonico["menor_preco_historico"])
            versao_canonica = 0 if canonico is None else int(canonico["versao"])

            eventos: list[dict[str, object]] = []

            mudou_listing = (
                preco_anterior is not None and abs(preco_anterior - preco_atual) > _EPSILON
            )
            novo_menor = (
                menor_anterior is not None
                and preco_atual < menor_anterior - _EPSILON
                and menor_preco_historico < menor_anterior - _EPSILON
            )

            if mudou_listing:
                versao_listing += 1
                direcao = "queda" if preco_atual < preco_anterior else "alta"
                variacao = (
                    ((preco_atual - preco_anterior) / preco_anterior) * 100
                    if abs(preco_anterior) > _EPSILON
                    else None
                )
                eventos.append(
                    self._evento(
                        tipo=TIPO_MUDANCA_PRECO,
                        chave_canonica=chave_canonica,
                        nome_canonico=nome_canonico,
                        marketplace=marketplace,
                        identificador=identificador,
                        preco_atual=preco_atual,
                        preco_anterior=preco_anterior,
                        referencia_anterior=preco_anterior,
                        direcao=direcao,
                        variacao_percentual=variacao,
                        versao=versao_listing,
                        criado_em=agora,
                    )
                )

            if novo_menor:
                versao_canonica += 1
                variacao = (
                    ((preco_atual - menor_anterior) / menor_anterior) * 100
                    if abs(menor_anterior) > _EPSILON
                    else None
                )
                eventos.append(
                    self._evento(
                        tipo=TIPO_NOVO_MENOR_PRECO_HISTORICO,
                        chave_canonica=chave_canonica,
                        nome_canonico=nome_canonico,
                        marketplace=marketplace,
                        identificador=identificador,
                        preco_atual=preco_atual,
                        preco_anterior=preco_anterior,
                        referencia_anterior=menor_anterior,
                        direcao="queda",
                        variacao_percentual=variacao,
                        versao=versao_canonica,
                        criado_em=agora,
                    )
                )

            for evento in eventos:
                conexao.execute(
                    """
                    INSERT OR IGNORE INTO alert_engine_eventos (
                        fingerprint, tipo, chave_canonica, nome_canonico,
                        marketplace, identificador, preco_atual,
                        preco_anterior, referencia_anterior, direcao,
                        variacao_percentual, versao, criado_em
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evento["fingerprint"],
                        evento["tipo"],
                        chave_canonica,
                        nome_canonico,
                        marketplace,
                        identificador,
                        preco_atual,
                        evento["preco_anterior"],
                        evento["referencia_anterior"],
                        evento["direcao"],
                        evento["variacao_percentual"],
                        evento["versao"],
                        agora,
                    ),
                )

            conexao.execute(
                """
                INSERT INTO alert_engine_estado_listing (
                    marketplace, identificador, chave_canonica,
                    nome_canonico, preco_atual, versao, atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(marketplace, identificador)
                DO UPDATE SET
                    nome_canonico = excluded.nome_canonico,
                    preco_atual = excluded.preco_atual,
                    versao = excluded.versao,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    marketplace,
                    identificador,
                    chave_canonica,
                    nome_canonico,
                    preco_atual,
                    versao_listing,
                    agora,
                ),
            )

            menor_persistido = menor_preco_historico
            if menor_anterior is not None:
                menor_persistido = min(
                    menor_anterior,
                    menor_preco_historico,
                    preco_atual,
                )

            conexao.execute(
                """
                INSERT INTO alert_engine_estado_canonico (
                    chave_canonica, nome_canonico,
                    menor_preco_historico, versao, atualizado_em
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chave_canonica)
                DO UPDATE SET
                    nome_canonico = excluded.nome_canonico,
                    menor_preco_historico = excluded.menor_preco_historico,
                    versao = excluded.versao,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    chave_canonica,
                    nome_canonico,
                    menor_persistido,
                    versao_canonica,
                    agora,
                ),
            )
            conexao.commit()

        return {
            "status": (
                "baseline_inicializada"
                if (baseline_listing or baseline_canonico) and not eventos
                else "processado"
            ),
            "baseline_inicializada": (baseline_listing or baseline_canonico),
            "alertas_gerados": len(eventos),
            "tipos_gerados": tuple(str(evento["tipo"]) for evento in eventos),
        }

    @staticmethod
    def _evento(
        *,
        tipo: str,
        chave_canonica: str,
        nome_canonico: str,
        marketplace: str,
        identificador: str,
        preco_atual: float,
        preco_anterior: float | None,
        referencia_anterior: float | None,
        direcao: str | None,
        variacao_percentual: float | None,
        versao: int,
        criado_em: str,
    ) -> dict[str, object]:
        material = "|".join(
            (
                tipo,
                chave_canonica,
                marketplace,
                identificador,
                str(versao),
                f"{preco_atual:.8f}",
                (f"{preco_anterior:.8f}" if preco_anterior is not None else ""),
                (f"{referencia_anterior:.8f}" if referencia_anterior is not None else ""),
            )
        )
        return {
            "fingerprint": sha256(material.encode("utf-8")).hexdigest(),
            "tipo": tipo,
            "preco_anterior": preco_anterior,
            "referencia_anterior": referencia_anterior,
            "direcao": direcao,
            "variacao_percentual": variacao_percentual,
            "versao": versao,
            "criado_em": criado_em,
        }

    def inicializar_baseline(
        self,
        *,
        chave_canonica: str,
        nome_canonico: str,
        menor_preco_historico: float,
        listings: list[tuple[str, str, float]],
        atualizado_em: str | None = None,
    ) -> dict[str, int]:
        """Inicializa apenas estado ausente, sem criar eventos retroativos."""
        agora = atualizado_em or datetime.now(UTC).isoformat()
        produtos_inseridos = 0
        listings_inseridos = 0
        conflitos_identidade = 0

        with self._conectar() as conexao:
            conexao.execute("BEGIN IMMEDIATE")

            cursor_produto = conexao.execute(
                """
                INSERT OR IGNORE INTO alert_engine_estado_canonico (
                    chave_canonica,
                    nome_canonico,
                    menor_preco_historico,
                    versao,
                    atualizado_em
                )
                VALUES (?, ?, ?, 0, ?)
                """,
                (
                    chave_canonica,
                    nome_canonico,
                    menor_preco_historico,
                    agora,
                ),
            )
            produtos_inseridos += max(0, int(cursor_produto.rowcount))

            for marketplace, identificador, preco_atual in listings:
                existente = conexao.execute(
                    """
                    SELECT chave_canonica
                    FROM alert_engine_estado_listing
                    WHERE marketplace = ?
                      AND identificador = ?
                    """,
                    (marketplace, identificador),
                ).fetchone()

                if existente is not None and str(existente["chave_canonica"]) != chave_canonica:
                    conflitos_identidade += 1
                    continue

                cursor_listing = conexao.execute(
                    """
                    INSERT OR IGNORE INTO alert_engine_estado_listing (
                        marketplace,
                        identificador,
                        chave_canonica,
                        nome_canonico,
                        preco_atual,
                        versao,
                        atualizado_em
                    )
                    VALUES (?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        marketplace,
                        identificador,
                        chave_canonica,
                        nome_canonico,
                        preco_atual,
                        agora,
                    ),
                )
                listings_inseridos += max(
                    0,
                    int(cursor_listing.rowcount),
                )

            conexao.commit()

        return {
            "produtos_inseridos": produtos_inseridos,
            "listings_inseridos": listings_inseridos,
            "conflitos_identidade": conflitos_identidade,
        }

    def listar_eventos(
        self,
        *,
        limite: int = 100,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        limite = max(1, min(int(limite), 500))
        offset = max(0, int(offset))
        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM alert_engine_eventos
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limite, offset),
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def obter_metricas(self) -> dict[str, object]:
        with self._conectar() as conexao:
            eventos = int(
                conexao.execute("SELECT COUNT(*) FROM alert_engine_eventos").fetchone()[0]
            )
            listings = int(
                conexao.execute("SELECT COUNT(*) FROM alert_engine_estado_listing").fetchone()[0]
            )
            produtos = int(
                conexao.execute("SELECT COUNT(*) FROM alert_engine_estado_canonico").fetchone()[0]
            )
            por_tipo = {str(linha["tipo"]): int(linha["total"]) for linha in conexao.execute("""
                    SELECT tipo, COUNT(*) AS total
                    FROM alert_engine_eventos
                    GROUP BY tipo
                    ORDER BY tipo
                    """).fetchall()}

        return {
            "eventos": eventos,
            "listings_monitorados": listings,
            "produtos_monitorados": produtos,
            "por_tipo": por_tipo,
        }
