# 63.8738, -149.7525

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from models.sinal_discovery_comercial_hunter import (
    ResultadoDiscoveryComercialHunter,
)
from models.tendencia_comercial_scout import (
    ObservacaoComercialScout,
)
from services.scout.agregador_tendencias_comerciais_scout import (
    AgregadorTendenciasComerciaisScout,
)
from services.scout.inteligencia_discovery_comercial_hunter import (
    InteligenciaDiscoveryComercialHunter,
)

logger = logging.getLogger(__name__)


CAMINHO_HISTORICO_PADRAO = Path("database/" "historico_comercial_scout.sqlite3")


def aplicar_discovery_comercial_hunter(
    limites_base: Mapping[
        str,
        int,
    ],
    *,
    caminho_historico: str | Path = (CAMINHO_HISTORICO_PADRAO),
    agora: datetime | None = None,
    janela_horas: int = 72,
) -> ResultadoDiscoveryComercialHunter:
    """
    Aplica somente inteligencia de discovery.

    O historico comercial e aberto em modo read-only.
    Qualquer falha de leitura/agregacao resulta em
    fail-open para os budgets base.

    Nenhum preco, score, Verifier ou mecanismo de
    publicacao pertence a esta camada.
    """

    inteligencia = InteligenciaDiscoveryComercialHunter()

    fallback = inteligencia.calcular(
        limites_base,
        (),
    )

    janela = _validar_janela(janela_horas)

    referencia = _normalizar_referencia(agora)

    caminho = Path(caminho_historico)

    if not caminho.exists():

        logger.info(
            "Commercial Discovery Hunter: "
            "historico comercial ainda ausente; "
            "budgets base preservados."
        )

        return fallback

    inicio = referencia - timedelta(hours=janela)

    try:

        observacoes = _carregar_observacoes(
            caminho,
            inicio=inicio,
        )

        tendencias = AgregadorTendenciasComerciaisScout().agregar(
            observacoes,
            agora=referencia,
            janela_horas=janela,
        )

        resultado = inteligencia.calcular(
            limites_base,
            tendencias,
        )

    except Exception as erro:

        logger.warning(
            "Commercial Discovery Hunter: "
            "falha ao ler/analisar historico; "
            "budgets base preservados. tipo=%s",
            type(erro).__name__,
        )

        return fallback

    logger.info(
        "Commercial Discovery Hunter: " "observacoes=%s | tendencias=%s | " "sinais_budget=%s.",
        len(observacoes),
        len(tendencias),
        len(resultado.sinais),
    )

    for sinal in resultado.sinais:

        logger.info(
            "Commercial Discovery Hunter: " "fonte=%s | budget=%s->%s | " "sinais=%s.",
            sinal.fonte_hunter,
            sinal.limite_base,
            sinal.limite_sugerido,
            sinal.sinais_distintos,
        )

    return resultado


def _carregar_observacoes(
    caminho: Path,
    *,
    inicio: datetime,
) -> list[ObservacaoComercialScout]:
    uri = caminho.resolve().as_uri() + "?mode=ro"

    inicio_iso = inicio.astimezone(UTC).isoformat()

    with sqlite3.connect(
        uri,
        uri=True,
        timeout=15,
    ) as conexao:

        conexao.row_factory = sqlite3.Row

        conexao.execute("PRAGMA query_only = ON")

        linhas = conexao.execute(
            """
            SELECT
                perfil_json,
                observado_em
            FROM historico_comercial_scout
            WHERE observado_em >= ?
            ORDER BY observado_em, id
            """,
            (inicio_iso,),
        ).fetchall()

    observacoes: list[ObservacaoComercialScout] = []

    for linha in linhas:

        dados = json.loads(str(linha["perfil_json"]))

        if not isinstance(
            dados,
            dict,
        ):
            raise ValueError("perfil_json precisa " "representar objeto.")

        perfil = SimpleNamespace(**dados)

        observado_em = datetime.fromisoformat(str(linha["observado_em"]))

        observacoes.append(
            ObservacaoComercialScout(
                perfil=perfil,
                observado_em=(observado_em),
            )
        )

    return observacoes


def _normalizar_referencia(
    valor: datetime | None,
) -> datetime:
    if valor is None:
        return datetime.now(UTC)

    if not isinstance(
        valor,
        datetime,
    ):
        raise TypeError("agora precisa ser datetime.")

    if valor.tzinfo is None or valor.utcoffset() is None:
        raise ValueError("agora precisa possuir timezone.")

    return valor.astimezone(UTC)


def _validar_janela(
    valor: int,
) -> int:
    if (
        isinstance(
            valor,
            bool,
        )
        or not isinstance(
            valor,
            int,
        )
        or valor <= 0
    ):
        raise ValueError("janela_horas precisa ser " "inteiro positivo.")

    return valor
