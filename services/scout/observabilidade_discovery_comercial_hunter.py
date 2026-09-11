# 63.8738, -149.7525

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from models.alvo_discovery_comercial_hunter import (
    AlvoDiscoveryComercialHunter,
    ResultadoAlvosDiscoveryComercialHunter,
)
from scrapers.base_scraper import BaseScraper

MAXIMO_TERMOS_PRIORIZADOS_KABUM = 5


def criar_observabilidade_discovery_comercial_hunter(
    *,
    resultado: ResultadoAlvosDiscoveryComercialHunter,
    scrapers: Iterable[BaseScraper],
) -> dict[str, Any]:
    """Resume alvos comerciais e confirma o que entrou no runtime."""

    scrapers_por_fonte: dict[str, BaseScraper] = {}

    for scraper in scrapers:
        nome = type(scraper).__name__
        scrapers_por_fonte.setdefault(nome, scraper)

    prioridades_kabum = _prioridades_kabum(resultado.alvos)
    alvos_observados = [
        _observar_alvo(
            alvo,
            scrapers_por_fonte=scrapers_por_fonte,
            prioridades_kabum=prioridades_kabum,
        )
        for alvo in resultado.alvos
    ]

    aplicados = sum(1 for alvo in alvos_observados if alvo["aplicado"])

    if not alvos_observados:
        status = "sem_alvos_maduros"
        motivo_status = "nenhum_alvo_comercial_maduro"

    elif aplicados == len(alvos_observados):
        status = "aplicado"
        motivo_status = "todos_alvos_confirmados_no_runtime"

    elif aplicados > 0:
        status = "aplicado_parcialmente"
        motivo_status = "parte_dos_alvos_confirmada_no_runtime"

    else:
        status = "nao_aplicado"
        motivo_status = "nenhum_alvo_confirmado_no_runtime"

    return {
        "schema_version": 1,
        "status": status,
        "motivo_status": motivo_status,
        "alvos_total": len(alvos_observados),
        "alvos_aplicados": aplicados,
        "fontes_hunter": list(resultado.fontes_hunter),
        "alvos": alvos_observados,
    }


def _prioridades_kabum(
    alvos: Iterable[AlvoDiscoveryComercialHunter],
) -> tuple[str, ...]:
    prioridades: list[str] = []
    vistos: set[str] = set()

    for alvo in alvos:
        if (
            alvo.fonte_hunter != "KabumScraper"
            or alvo.estrategia != "buscar_termos_kabum"
            or not alvo.termo_busca
        ):
            continue

        termo = alvo.termo_busca.strip()

        if not termo:
            continue

        chave = termo.casefold()

        if chave in vistos:
            continue

        vistos.add(chave)
        prioridades.append(termo)

        if len(prioridades) >= MAXIMO_TERMOS_PRIORIZADOS_KABUM:
            break

    return tuple(prioridades)


def _observar_alvo(
    alvo: AlvoDiscoveryComercialHunter,
    *,
    scrapers_por_fonte: dict[str, BaseScraper],
    prioridades_kabum: tuple[str, ...],
) -> dict[str, Any]:
    scraper = scrapers_por_fonte.get(alvo.fonte_hunter)

    aplicado = False
    motivo_aplicacao = "fonte_hunter_nao_configurada"
    posicao_runtime: int | None = None

    if scraper is not None:
        if alvo.fonte_hunter == "KabumScraper" and alvo.estrategia == "buscar_termos_kabum":
            (
                aplicado,
                motivo_aplicacao,
                posicao_runtime,
            ) = _observar_kabum(
                alvo,
                scraper=scraper,
                prioridades=prioridades_kabum,
            )

        elif (
            alvo.fonte_hunter == "AliExpressScraper" and alvo.estrategia == "feed_curado_aliexpress"
        ):
            aplicado = True
            motivo_aplicacao = "rota_feed_curado_nativa_ativa"

        else:
            motivo_aplicacao = "rota_sem_confirmacao_operacional"

    return {
        "fonte_hunter": alvo.fonte_hunter,
        "marketplace": alvo.marketplace,
        "estrategia": alvo.estrategia,
        "termo_busca": alvo.termo_busca,
        "direcao": alvo.direcao,
        "sinais_distintos": alvo.sinais_distintos,
        "motivo": alvo.motivo,
        "evidencias": list(alvo.evidencias),
        "aplicado": aplicado,
        "motivo_aplicacao": motivo_aplicacao,
        "posicao_runtime": posicao_runtime,
    }


def _observar_kabum(
    alvo: AlvoDiscoveryComercialHunter,
    *,
    scraper: BaseScraper,
    prioridades: tuple[str, ...],
) -> tuple[bool, str, int | None]:
    termo = str(alvo.termo_busca or "").strip()

    if not termo:
        return (
            False,
            "termo_busca_ausente",
            None,
        )

    chave = termo.casefold()
    prioridades_normalizadas = tuple(item.casefold() for item in prioridades)

    if chave not in prioridades_normalizadas:
        return (
            False,
            "fora_limite_priorizacao_kabum",
            None,
        )

    termos_runtime = tuple(
        str(item).strip()
        for item in getattr(
            scraper,
            "termos_busca",
            (),
        )
        if str(item).strip()
    )

    for indice, termo_runtime in enumerate(
        termos_runtime,
        start=1,
    ):
        if termo_runtime.casefold() != chave:
            continue

        if indice <= len(prioridades):
            return (
                True,
                "termo_priorizado_kabum",
                indice,
            )

        return (
            False,
            "priorizacao_nao_confirmada_no_runtime",
            indice,
        )

    return (
        False,
        "termo_nao_encontrado_no_runtime",
        None,
    )
