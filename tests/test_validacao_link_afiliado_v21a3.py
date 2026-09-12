from __future__ import annotations

from affiliates.afiliador_amazon import AfiliadorAmazon
from affiliates.afiliador_awin import AfiliadorAwin
from affiliates.afiliador_mercado_livre import AfiliadorMercadoLivre
from affiliates.afiliador_shopee import AfiliadorShopee
from affiliates.base_afiliador import BaseAfiliador
from affiliates.gerador_link_afiliado import GeradorLinkAfiliado


class RepositoryFake:
    def __init__(self, link: str) -> None:
        self.link = link

    def obter_link_afiliado(self, _link_original: str) -> str:
        return self.link


class ShopeeServiceFake:
    def __init__(self, link: str) -> None:
        self.link = link

    def gerar_shortlink(self, _link_original: str) -> str:
        return self.link


class AfiliadorEstruturalFake(BaseAfiliador):
    def __init__(self, saida: str) -> None:
        self.saida = saida

    @property
    def nome(self) -> str:
        return "EstruturalFake"

    def suporta(self, _link: str) -> bool:
        return True

    def gerar_link(self, _link_original: str) -> str:
        return self.saida


class AwinSaidaFake(AfiliadorAwin):
    def __init__(self, saida: str) -> None:
        super().__init__(
            nome="Awin Fake",
            dominios=["aliexpress.com"],
            advertiser_id="18879",
            publisher_id="123456",
            api_token="",
        )
        self.saida = saida

    def gerar_link(self, _link_original: str) -> str:
        return self.saida


def gerar(afiliador, original: str):
    gerador = GeradorLinkAfiliado()
    gerador.registrar(afiliador)
    return gerador.gerar(original)


def test_base_rejeita_url_nao_https_mesmo_quando_diferente():
    original = "https://example.com/produto"
    resultado = gerar(
        AfiliadorEstruturalFake("javascript:alert(1)"),
        original,
    )
    assert not resultado.foi_transformado
    assert resultado.link_publicacao == original


def test_mercado_livre_aceita_meli_valido():
    original = "https://www.mercadolivre.com.br/produto/p/MLB123"
    afiliador = AfiliadorMercadoLivre(
        nome="Mercado Livre",
        dominios=["mercadolivre.com.br"],
        repository=RepositoryFake("https://meli.la/abc123"),
    )
    resultado = gerar(afiliador, original)
    assert resultado.foi_transformado
    assert resultado.link_publicacao == "https://meli.la/abc123"


def test_mercado_livre_rejeita_url_diferente_de_dominio_errado():
    original = "https://www.mercadolivre.com.br/produto/p/MLB123"
    afiliador = AfiliadorMercadoLivre(
        nome="Mercado Livre",
        dominios=["mercadolivre.com.br"],
        repository=RepositoryFake("https://evil.example/abc123"),
    )
    resultado = gerar(afiliador, original)
    assert not resultado.foi_transformado
    assert resultado.link_publicacao == original


def test_shopee_aceita_shortlink_oficial():
    original = "https://shopee.com.br/product/701693560/22797310651"
    afiliador = AfiliadorShopee(
        nome="Shopee",
        dominios=["shopee.com.br"],
        service=ShopeeServiceFake("https://s.shopee.com.br/6L40LOAkOW"),
    )
    resultado = gerar(afiliador, original)
    assert resultado.foi_transformado
    assert resultado.link_publicacao == "https://s.shopee.com.br/6L40LOAkOW"


def test_shopee_rejeita_shortlink_de_dominio_errado():
    original = "https://shopee.com.br/product/701693560/22797310651"
    afiliador = AfiliadorShopee(
        nome="Shopee",
        dominios=["shopee.com.br"],
        service=ShopeeServiceFake("https://evil.example/6L40LOAkOW"),
    )
    resultado = gerar(afiliador, original)
    assert not resultado.foi_transformado
    assert resultado.link_publicacao == original


def test_amazon_aceita_link_amazon_validado():
    original = "https://www.amazon.com.br/dp/B0ABCDEF12"
    afiliador = AfiliadorAmazon(
        nome="Amazon",
        dominios=["amazon.com.br"],
        repository=RepositoryFake("https://link.amazon/abc123"),
    )
    resultado = gerar(afiliador, original)
    assert resultado.foi_transformado
    assert resultado.link_publicacao == "https://link.amazon/abc123"


def test_amazon_aceita_link_longo_com_tag():
    original = "https://www.amazon.com.br/dp/B0ABCDEF12"
    afiliado = "https://www.amazon.com.br/dp/B0ABCDEF12?tag=exemplo-20"
    afiliador = AfiliadorAmazon(
        nome="Amazon",
        dominios=["amazon.com.br"],
        repository=RepositoryFake(afiliado),
    )
    resultado = gerar(afiliador, original)
    assert resultado.foi_transformado
    assert resultado.link_publicacao == afiliado


def test_amazon_rejeita_url_diferente_sem_prova_de_afiliacao():
    original = "https://www.amazon.com.br/dp/B0ABCDEF12"
    afiliador = AfiliadorAmazon(
        nome="Amazon",
        dominios=["amazon.com.br"],
        repository=RepositoryFake("https://evil.example/abc123"),
    )
    resultado = gerar(afiliador, original)
    assert not resultado.foi_transformado
    assert resultado.link_publicacao == original


def test_awin_aceita_tracking_link_longo_com_ids_esperados():
    original = "https://www.aliexpress.com/item/1005001234567890.html"
    afiliador = AfiliadorAwin(
        nome="AliExpress",
        dominios=["aliexpress.com"],
        advertiser_id="18879",
        publisher_id="123456",
        api_token="",
    )
    resultado = gerar(afiliador, original)
    assert resultado.foi_transformado
    assert "awinmid=18879" in resultado.link_publicacao
    assert "awinaffid=123456" in resultado.link_publicacao


def test_awin_aceita_tiddly_gerado_pelo_proprio_fluxo():
    afiliador = AwinSaidaFake("https://tidd.ly/abc123")
    original = "https://www.aliexpress.com/item/1005001234567890.html"
    resultado = gerar(afiliador, original)
    assert resultado.foi_transformado
    assert resultado.link_publicacao == "https://tidd.ly/abc123"


def test_awin_rejeita_url_diferente_de_dominio_errado():
    afiliador = AwinSaidaFake("https://evil.example/abc123")
    original = "https://www.aliexpress.com/item/1005001234567890.html"
    resultado = gerar(afiliador, original)
    assert not resultado.foi_transformado
    assert resultado.link_publicacao == original
