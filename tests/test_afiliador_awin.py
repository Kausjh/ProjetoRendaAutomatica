from urllib.parse import parse_qs, urlparse

from affiliates.afiliador_awin import AfiliadorAwin


def criar_afiliador() -> AfiliadorAwin:
    return AfiliadorAwin(
        nome="AliExpress",
        dominios=["aliexpress.com"],
        advertiser_id="18879",
        publisher_id="123456",
    )


def test_suporta_aliexpress():
    afiliador = criar_afiliador()

    assert afiliador.suporta("https://www.aliexpress.com/item/1005001234567890.html")


def test_nao_suporta_outro_marketplace():
    afiliador = criar_afiliador()

    assert not afiliador.suporta("https://shopee.com.br/produto")


def test_gera_deeplink_awin():
    afiliador = criar_afiliador()

    destino = "https://www.aliexpress.com/" "item/1005001234567890.html"

    link = afiliador.gerar_link(destino)

    url = urlparse(link)
    parametros = parse_qs(url.query)

    assert url.scheme == "https"
    assert url.netloc == "www.awin1.com"
    assert url.path == "/cread.php"

    assert parametros["awinmid"] == ["18879"]

    assert parametros["awinaffid"] == ["123456"]

    assert parametros["ued"] == [destino]


def test_subdominio_do_aliexpress_e_aceito():
    afiliador = criar_afiliador()

    assert afiliador.suporta("https://pt.aliexpress.com/item/123.html")
