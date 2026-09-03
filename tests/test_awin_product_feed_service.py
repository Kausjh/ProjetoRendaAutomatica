import csv
import gzip
import io

from services.awin_product_feed_service import (
    AwinProductFeedService,
)


def criar_csv(
    cabecalho: list[str],
    linhas: list[list[str]],
) -> bytes:
    arquivo = io.StringIO(newline="")

    writer = csv.writer(arquivo)

    writer.writerow(cabecalho)

    writer.writerows(linhas)

    return arquivo.getvalue().encode("utf-8")


class UrlOpenFake:
    def __init__(
        self,
        respostas: dict[str, bytes],
    ) -> None:
        self.respostas = respostas

    def __call__(
        self,
        requisicao,
        timeout,
    ):
        del timeout

        url = requisicao.full_url

        if url not in self.respostas:
            raise AssertionError(f"URL inesperada: {url}")

        return io.BytesIO(self.respostas[url])


def criar_service():
    lista_url = "https://productdata.awin.com/" "datafeed/list/apikey/teste"

    feed_url = (
        "https://productdata.awin.com/"
        "datafeed/download/apikey/teste/"
        "fid/47215/format/csv/"
        "compression/gzip/"
    )

    lista = criar_csv(
        [
            "Advertiser ID",
            "Advertiser Name",
            "Primary Region",
            "Membership Status",
            "Feed ID",
            "Feed Name",
            "Language",
            "Vertical",
            "Last Imported",
            "URL",
        ],
        [
            [
                "18879",
                "Aliexpress BR & LATAM",
                "BU",
                "active",
                "47215",
                "Computer_Office",
                "English",
                "",
                "2026-09-03 16:13:04",
                feed_url,
            ],
            [
                "12044",
                "AliExpress PL",
                "PL",
                "Not Joined",
                "21661",
                "Mobile Accessories",
                "English",
                "",
                "2026-09-03 14:49:10",
                "https://example.com/pl",
            ],
        ],
    )

    produto = criar_csv(
        [
            "aw_product_id",
            "merchant_product_id",
            "product_name",
            "currency",
            "search_price",
            "base_price",
            "savings_percent",
            "stock_quantity",
            "merchant_category",
            "category_name",
            "brand_name",
            "merchant_deep_link",
            "aw_deep_link",
            "aw_image_url",
            "alternate_image",
            "alternate_image_two",
            "alternate_image_three",
            "alternate_image_four",
        ],
        [
            [
                "45623289451",
                "1005012950076014",
                "Mini PC Intel N150",
                "CNY",
                "192.10",
                "2918.36",
                "56%",
                "26",
                "Computer & Office",
                "Office Supplies",
                "Intel",
                "https://s.click.aliexpress.com/teste",
                "https://www.awin1.com/pclick.php?teste=1",
                "https://images2.productserve.com/noimage.gif",
                "https://ae-pic-a1.aliexpress-media.com/kf/produto.jpg",
                "",
                "",
                "",
            ]
        ],
    )

    respostas = {
        lista_url: lista,
        feed_url: gzip.compress(produto),
    }

    return AwinProductFeedService(
        api_key="teste",
        urlopen=UrlOpenFake(respostas),
    )


def test_lista_somente_feed_ativo_do_aliexpress():
    service = criar_service()

    feeds = service.listar_feeds(
        advertiser_id="18879",
        somente_ativos=True,
    )

    assert len(feeds) == 1
    assert feeds[0].feed_id == "47215"
    assert feeds[0].ativo is True


def test_le_produto_do_feed_sem_converter_moeda():
    service = criar_service()

    produtos = list(
        service.iterar_produtos(
            "47215",
            limite=1,
        )
    )

    assert len(produtos) == 1

    produto = produtos[0]

    assert produto.nome == ("Mini PC Intel N150")

    assert produto.moeda == "CNY"
    assert produto.preco_feed == 192.10
    assert produto.preco_base_feed == 2918.36
    assert produto.desconto_percentual_feed == 56.0

    # Critico: esta camada nao inventa BRL.
    assert produto.moeda != "BRL"


def test_usa_imagem_alternativa_quando_aw_image_e_placeholder():
    service = criar_service()

    produto = next(
        service.iterar_produtos(
            "47215",
            limite=1,
        )
    )

    assert produto.imagem == ("https://ae-pic-a1.aliexpress-media.com/" "kf/produto.jpg")


def test_preserva_links_do_merchant_e_da_awin():
    service = criar_service()

    produto = next(
        service.iterar_produtos(
            "47215",
            limite=1,
        )
    )

    assert produto.link_merchant.startswith("https://s.click.aliexpress.com/")

    assert produto.link_awin.startswith("https://www.awin1.com/")
