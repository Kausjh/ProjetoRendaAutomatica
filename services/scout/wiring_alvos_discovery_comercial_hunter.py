# 63.8738, -149.7525

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from models.alvo_discovery_comercial_hunter import (
    ResultadoAlvosDiscoveryComercialHunter,
)
from services.scout.agregador_tendencias_comerciais_scout import (
    AgregadorTendenciasComerciaisScout,
)
from services.scout.inteligencia_alvos_discovery_comercial_hunter import (
    InteligenciaAlvosDiscoveryComercialHunter,
)
from services.scout.wiring_discovery_comercial_hunter import (
    CAMINHO_HISTORICO_PADRAO,
    _carregar_observacoes,
    _normalizar_referencia,
    _validar_janela,
)

logger = logging.getLogger(__name__)


def carregar_alvos_discovery_comercial_hunter(
    *,
    caminho_historico: str | Path = CAMINHO_HISTORICO_PADRAO,
    agora: datetime | None = None,
    janela_horas: int = 72,
) -> ResultadoAlvosDiscoveryComercialHunter:
    "Carrega alvos comerciais maduros para orientar discovery."

    inteligencia = InteligenciaAlvosDiscoveryComercialHunter()
    fallback = inteligencia.calcular(())

    janela = _validar_janela(janela_horas)
    referencia = _normalizar_referencia(agora)
    caminho = Path(caminho_historico)

    if not caminho.exists():
        logger.info(
            "Commercial Discovery Targets: "
            "historico comercial ainda ausente; "
            "nenhum alvo adicional."
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

        resultado = inteligencia.calcular(tendencias)

    except Exception as erro:
        logger.warning(
            "Commercial Discovery Targets: "
            "falha ao ler/analisar historico; "
            "nenhum alvo adicional. tipo=%s",
            type(erro).__name__,
        )
        return fallback

    logger.info(
        "Commercial Discovery Targets: " "observacoes=%s | tendencias=%s | alvos=%s.",
        len(observacoes),
        len(tendencias),
        len(resultado.alvos),
    )

    for alvo in resultado.alvos:
        logger.info(
            "Commercial Discovery Target: "
            "fonte=%s | marketplace=%s | estrategia=%s | "
            "termo=%s | direcao=%s | sinais=%s.",
            alvo.fonte_hunter,
            alvo.marketplace,
            alvo.estrategia,
            alvo.termo_busca,
            alvo.direcao,
            alvo.sinais_distintos,
        )

    return resultado
