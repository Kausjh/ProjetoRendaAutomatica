from affiliates.afiliador_shopee import AfiliadorShopee


class ShopeeApiServiceFake:
    def gerar_shortlink(self, link_original: str) -> str:
        assert link_original == ("https://shopee.com.br/product/701693560/22797310651")

        return "https://s.shopee.com.br/6L40LOAkOW"


def test_suporta_link_da_shopee() -> None:
    afiliador = AfiliadorShopee(
        nome="Shopee",
        dominios=["shopee.com.br"],
        service=ShopeeApiServiceFake(),
    )

    assert afiliador.suporta("https://shopee.com.br/product/701693560/22797310651")


def test_nao_suporta_outro_dominio() -> None:
    afiliador = AfiliadorShopee(
        nome="Shopee",
        dominios=["shopee.com.br"],
        service=ShopeeApiServiceFake(),
    )

    assert not afiliador.suporta("https://www.mercadolivre.com.br/produto")


def test_gera_link_afiliado_shopee() -> None:
    afiliador = AfiliadorShopee(
        nome="Shopee",
        dominios=["shopee.com.br"],
        service=ShopeeApiServiceFake(),
    )

    resultado = afiliador.gerar_link("https://shopee.com.br/product/701693560/22797310651")

    assert resultado == "https://s.shopee.com.br/6L40LOAkOW"
