# 63.8738, -149.7525

import inspect

import scrapers.mercado_livre_scraper as modulo_ml
from scrapers.mercado_livre_scraper import (
    MercadoLivreScraper,
)


def test_modulo_ml_nao_possui_legado_browser():
    fonte = inspect.getsource(modulo_ml)

    proibidos = (
        "playwright",
        "connect_over_cdp",
        "ENDPOINT_CDP",
        "endpoint_cdp",
        "URL_BUSCA",
        "SELETORES_CARTAO",
        "_obter_contexto",
        "_buscar_termo",
        "_aguardar_produtos",
        "_obter_cartoes",
        "_extrair_oferta",
        "_pagina_possui_bloqueio",
        "quote_plus",
    )

    for trecho in proibidos:
        assert trecho not in fonte


def test_buscar_ofertas_usa_motor_api_first():
    fonte = inspect.getsource(MercadoLivreScraper.buscar_ofertas)

    assert "_obter_domain_id" in fonte
    assert "buscar_produtos" in fonte
    assert "consultar_snapshot" in fonte


def test_scraper_preserva_contratos_publicos():
    assert hasattr(
        MercadoLivreScraper,
        "TERMOS_POR_CATEGORIA",
    )

    assert hasattr(
        MercadoLivreScraper,
        "CATEGORIAS_PRIORITARIAS",
    )

    assert hasattr(
        MercadoLivreScraper,
        "CATEGORIAS_SECUNDARIAS",
    )

    assert callable(MercadoLivreScraper.buscar_ofertas)
