from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError

import scrapers.mercado_livre_scraper as modulo_ml
from models.oferta import Oferta
from scrapers.mercado_livre_scraper import MercadoLivreScraper
from services.hunter_v2 import HunterV2


class FonteSaudavel:
    def buscar_ofertas(
        self,
        limite=5,
    ):
        del limite

        return [
            Oferta(
                nome="Produto saudavel",
                loja="Teste",
                preco=100.0,
                preco_antigo=None,
                link="https://teste/produto",
                imagem=None,
            )
        ]


def _falha_playwright():
    raise PlaywrightError("falha controlada de CDP")


def test_mercado_livre_propaga_playwright_error(
    monkeypatch,
):
    monkeypatch.setattr(
        modulo_ml,
        "sync_playwright",
        _falha_playwright,
    )

    scraper = MercadoLivreScraper(
        termos_busca=[
            "Ryzen 7",
        ]
    )

    try:
        scraper.buscar_ofertas(limite=1)

    except PlaywrightError as erro:
        assert "falha controlada de CDP" in str(erro)

    else:
        raise AssertionError("PlaywrightError deveria ser propagado.")


def test_hunter_marca_ml_com_erro_e_preserva_outra_fonte(
    monkeypatch,
):
    monkeypatch.setattr(
        modulo_ml,
        "sync_playwright",
        _falha_playwright,
    )

    ml = MercadoLivreScraper(
        termos_busca=[
            "Ryzen 7",
        ]
    )

    resultado = HunterV2(
        [
            ml,
            FonteSaudavel(),
        ]
    ).descobrir(limite_base=1)

    assert resultado.quantidade_bruta == 1
    assert resultado.quantidade_unica == 1

    assert resultado.fontes_com_erro == ("MercadoLivreScraper",)

    ml_resultado = resultado.fontes[0]

    fonte_saudavel = resultado.fontes[1]

    assert ml_resultado.sucesso is False
    assert ml_resultado.quantidade_coletada == 0

    assert ml_resultado.erro is not None
    assert "falha controlada de CDP" in ml_resultado.erro

    assert fonte_saudavel.sucesso is True
    assert fonte_saudavel.quantidade_coletada == 1

    assert resultado.ofertas[0].nome == "Produto saudavel"
