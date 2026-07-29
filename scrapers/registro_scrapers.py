from scrapers.base_scraper import BaseScraper
from scrapers.mercado_livre_scraper import MercadoLivreScraper

TERMOS_MERCADO_LIVRE = [
    # Processadores
    "Ryzen 5",
    "Ryzen 7",
    "Intel Core i5",
    "Intel Core i7",
    # Placas de vídeo
    "RTX placa de vídeo",
    "RX placa de vídeo",
    # Armazenamento e memória
    "SSD NVMe",
    "Memória RAM DDR4",
    "Memória RAM DDR5",
    # Monitores
    "Monitor gamer",
    # Fontes
    "Fonte Corsair",
    "Fonte MSI",
    # Placas-mãe
    "Placa mãe B550",
    "Placa mãe B650",
    # Gabinetes
    "Gabinete gamer",
    # Periféricos
    "Mouse Logitech",
    "Teclado Redragon",
    "Headset HyperX",
]


def criar_scrapers() -> list[BaseScraper]:
    return [MercadoLivreScraper(termos_busca=TERMOS_MERCADO_LIVRE)]
