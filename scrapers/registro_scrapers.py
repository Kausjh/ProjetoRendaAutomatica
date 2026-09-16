import os
from collections.abc import Iterable

from models.alvo_discovery_comercial_hunter import AlvoDiscoveryComercialHunter
from scrapers.aliexpress_scraper import AliExpressScraper
from scrapers.base_scraper import BaseScraper
from scrapers.community_discovery_scraper import CommunityDiscoveryScraper
from scrapers.kabum_scraper import KabumScraper
from scrapers.mercado_livre_scraper import MercadoLivreScraper
from scrapers.shopee_scraper import ShopeeScraper
from scrapers.social_scout_scraper import SocialScoutScraper


def _variavel_ativa(
    nome: str,
    valor_padrao: bool = False,
) -> bool:
    valor = os.getenv(nome)

    if valor is None:
        return valor_padrao

    normalizado = valor.strip().casefold()

    if normalizado in {
        "1",
        "true",
        "sim",
        "yes",
        "on",
    }:
        return True

    if normalizado in {
        "",
        "0",
        "false",
        "nao",
        "n?o",
        "no",
        "off",
    }:
        return False

    return valor_padrao


def _inteiro_positivo(
    nome: str,
    valor_padrao: int,
) -> int:
    valor = os.getenv(nome)

    if valor is None:
        return max(
            int(valor_padrao),
            1,
        )

    try:
        numero = int(str(valor).strip())

    except (
        TypeError,
        ValueError,
    ):
        return max(
            int(valor_padrao),
            1,
        )

    if numero <= 0:
        return max(
            int(valor_padrao),
            1,
        )

    return numero


def criar_scrapers(
    *,
    alvos_discovery_comercial: Iterable[AlvoDiscoveryComercialHunter] = (),
) -> list[BaseScraper]:
    """Cria somente as fontes explicitamente habilitadas."""

    alvos = tuple(alvos_discovery_comercial)

    kabum = KabumScraper()

    termos_kabum = [
        alvo.termo_busca
        for alvo in alvos
        if (
            alvo.fonte_hunter == "KabumScraper"
            and alvo.estrategia == "buscar_termos_kabum"
            and alvo.termo_busca
        )
    ]

    if termos_kabum:
        priorizar_termos = getattr(
            kabum,
            "priorizar_termos_discovery",
            None,
        )

        if not callable(priorizar_termos):
            raise TypeError("KabumScraper nao suporta priorizacao " "de termos discovery.")

        priorizar_termos(
            termos_kabum,
            maximo=5,
        )

    scrapers: list[BaseScraper] = [
        MercadoLivreScraper(),
        ShopeeScraper(),
        kabum,
        AliExpressScraper(),
    ]

    if _variavel_ativa(
        "SOCIAL_SCOUT_PIPELINE_ATIVO",
        valor_padrao=False,
    ):
        modo_sombra = _variavel_ativa(
            "SOCIAL_SCOUT_MODO_SOMBRA",
            valor_padrao=True,
        )

        max_mensagens_por_execucao = _inteiro_positivo(
            "SOCIAL_SCOUT_MAX_MENSAGENS_POR_EXECUCAO",
            valor_padrao=5,
        )

        scrapers.append(
            SocialScoutScraper(
                modo_sombra=modo_sombra,
                max_mensagens_por_execucao=(max_mensagens_por_execucao),
            )
        )

    if _variavel_ativa(
        "COMMUNITY_DISCOVERY_PIPELINE_ATIVO",
        valor_padrao=False,
    ):
        max_descobertas_por_execucao = _inteiro_positivo(
            "COMMUNITY_DISCOVERY_MAX_POR_EXECUCAO",
            valor_padrao=3,
        )

        scrapers.append(
            CommunityDiscoveryScraper(
                max_descobertas_por_execucao=(max_descobertas_por_execucao),
            )
        )

    return scrapers
