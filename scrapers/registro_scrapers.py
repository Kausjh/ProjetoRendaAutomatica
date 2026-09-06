import os

from scrapers.aliexpress_scraper import AliExpressScraper
from scrapers.base_scraper import BaseScraper
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

    # Falha fechada:
    # valor desconhecido jamais ativa o Social Scout.
    return valor_padrao


def criar_scrapers() -> list[BaseScraper]:
    """Cria somente as fontes explicitamente habilitadas."""

    scrapers: list[BaseScraper] = [
        MercadoLivreScraper(),
        ShopeeScraper(),
        KabumScraper(),
        AliExpressScraper(),
    ]

    if _variavel_ativa(
        "SOCIAL_SCOUT_PIPELINE_ATIVO",
        valor_padrao=False,
    ):
        scrapers.append(SocialScoutScraper())

    return scrapers
