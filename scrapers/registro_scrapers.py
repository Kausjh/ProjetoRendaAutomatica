from scrapers.base_scraper import BaseScraper
from scrapers.mercado_livre_scraper import MercadoLivreScraper
from scrapers.shopee_scraper import ShopeeScraper

TERMOS_MERCADO_LIVRE = [
    # Processadores
    "Ryzen 5",
    "Ryzen 7",
    "Intel Core i5",
    "Intel Core i7",
    # Placas de v?deo
    "RTX placa de v?deo",
    "RX placa de v?deo",
    # Armazenamento e mem?ria
    "SSD NVMe",
    "Mem?ria RAM DDR4",
    "Mem?ria RAM DDR5",
    # Monitores
    "Monitor gamer",
    # Fontes
    "Fonte Corsair",
    "Fonte MSI",
    # Placas-m?e
    "Placa m?e B550",
    "Placa m?e B650",
    # Gabinetes
    "Gabinete gamer",
    # Perif?ricos
    "Mouse Logitech",
    "Teclado Redragon",
    "Headset HyperX",
]

TERMOS_SHOPEE = list(TERMOS_MERCADO_LIVRE)


def criar_scrapers() -> list[BaseScraper]:
    return [
        MercadoLivreScraper(
            termos_busca=TERMOS_MERCADO_LIVRE,
        ),
        ShopeeScraper(
            termos_busca=TERMOS_SHOPEE,
        ),
    ]
