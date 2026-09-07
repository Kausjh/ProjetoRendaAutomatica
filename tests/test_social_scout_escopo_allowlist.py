# 63.8738, -149.7525

from scrapers.social_scout_scraper import (
    SocialScoutScraper,
)

PERMITIDAS = (
    "Armazenamento",
    "Computador e Mini PC",
    "Console",
    "Controle",
    "Fonte e energia",
    "Gabinete",
    "Ilumina\u00e7\u00e3o de setup",
    "Kit upgrade",
    "Mem\u00f3ria RAM",
    "Microfone",
    "Monitor",
    "Mouse e mousepad",
    "Notebook",
    "Placa de v\u00eddeo",
    "Placa-m\u00e3e",
    "Processador",
    "Realidade virtual",
    "Rede",
    "Refrigera\u00e7\u00e3o de PC",
    "Simula\u00e7\u00e3o",
    "Streaming e captura",
    "Suportes e conectividade",
    "Teclado",
    "\u00c1udio",
)


BLOQUEADAS = (
    "Automa\u00e7\u00e3o dom\u00e9stica",
    "Caf\u00e9",
    "Carregamento e mobilidade",
    "Casa inteligente",
    "Celular",
    "Chocolate e snacks",
    "Climatiza\u00e7\u00e3o e conforto",
    "C\u00e2meras e drones",
    "Energ\u00e9ticos",
    "Impress\u00e3o",
    "Maker e bancada",
    "Mobili\u00e1rio e ergonomia",
    "Projetor",
    "Suplementos",
    "Tablet e e-reader",
    "TV",
    "Wearables",
)


def test_allowlist_preserva_hardware_gamer():
    for categoria in PERMITIDAS:
        assert not (SocialScoutScraper._categoria_fora_escopo_social(categoria))


def test_allowlist_bloqueia_categorias_amplas():
    for categoria in BLOQUEADAS:
        assert SocialScoutScraper._categoria_fora_escopo_social(categoria)


def test_allowlist_falha_fechada():
    for categoria in (
        None,
        "",
        "   ",
        "Categoria futura desconhecida",
    ):
        assert SocialScoutScraper._categoria_fora_escopo_social(categoria)


def test_allowlist_normaliza_unicode_case_espaco():
    assert not (SocialScoutScraper._categoria_fora_escopo_social("  PLACA DE V\u00cdDEO  "))

    assert not (SocialScoutScraper._categoria_fora_escopo_social("A\u0301udio"))


def test_social_scout_usa_v6():
    assert SocialScoutScraper.VERSAO_PROCESSADOR == "6"
