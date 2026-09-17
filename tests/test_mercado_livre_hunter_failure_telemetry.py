# 63.8738, -149.7525

from __future__ import annotations

from models.oferta import Oferta
from scrapers.mercado_livre_scraper import (
    MercadoLivreScraper,
)
from services.hunter_v2 import HunterV2
from services.scout.mercado_livre_catalog_api import (
    ErroApiMercadoLivre,
)


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


class ClienteMercadoLivreComFalha:
    def descobrir_dominios(
        self,
        consulta,
        limite=3,
    ):
        del consulta
        del limite

        raise ErroApiMercadoLivre(
            "api_mercado_livre_rate_limit",
            status_code=429,
            transitorio=True,
        )


def _scraper_com_falha():
    return MercadoLivreScraper(
        termos_busca=[
            "Ryzen 7",
        ],
        cliente_catalogo=(ClienteMercadoLivreComFalha()),
        sleep_fn=lambda _: None,
        tentativas_rate_limit=0,
    )


def test_mercado_livre_propaga_erro_api():
    scraper = _scraper_com_falha()

    try:
        scraper.buscar_ofertas(limite=1)

    except ErroApiMercadoLivre as erro:
        assert erro.status_code == 429
        assert erro.transitorio is True

        assert erro.motivo == "api_mercado_livre_rate_limit"

    else:
        raise AssertionError("ErroApiMercadoLivre deveria " "ser propagado.")


def test_hunter_marca_ml_com_erro_e_preserva_outra_fonte():
    resultado = HunterV2(
        [
            _scraper_com_falha(),
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

    assert "api_mercado_livre_rate_limit" in ml_resultado.erro

    assert fonte_saudavel.sucesso is True
    assert fonte_saudavel.quantidade_coletada == 1

    assert resultado.ofertas[0].nome == "Produto saudavel"
