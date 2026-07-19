from scrapers.base_scraper import BaseScraper
from scrapers.exemplo_scraper import ExemploScraper
from scrapers.segundo_exemplo_scraper import SegundoExemploScraper


def criar_scrapers() -> list[BaseScraper]:
    scrapers: list[BaseScraper] = [
        ExemploScraper(),
        SegundoExemploScraper()
    ]

    return scrapers