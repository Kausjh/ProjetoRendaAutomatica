from scrapers.aliexpress_scraper import AliExpressScraper
from scrapers.base_scraper import BaseScraper
from scrapers.mercado_livre_scraper import MercadoLivreScraper
from scrapers.shopee_scraper import ShopeeScraper


def criar_scrapers() -> list[BaseScraper]:
    """Cria as fontes ativas usando a pol?tica pr?pria de busca de cada uma."""
    return [
        MercadoLivreScraper(),
        ShopeeScraper(),
        AliExpressScraper(),
    ]
