from scrapers.shopee_scraper import ShopeeScraper


class ShopeeApiServiceFake:
    def __init__(self, produtos: list[dict]) -> None:
        self.produtos = produtos
        self.chamadas: list[str] = []

    def buscar_produtos(
        self,
        termo: str,
        limite: int = 20,
        pagina: int = 1,
        tipo_ordenacao: int = 1,
    ) -> list[dict]:
        del limite
        del pagina
        del tipo_ordenacao

        self.chamadas.append(termo)

        return self.produtos


def test_converte_produto_da_api_em_oferta() -> None:
    service = ShopeeApiServiceFake(
        [
            {
                "itemId": 123,
                "productName": "SSD NVMe 1TB",
                "productLink": ("https://shopee.com.br/product/10/123"),
                "imageUrl": "http://example.com/ssd.jpg",
                "priceMin": "299.90",
                "priceMax": "299.90",
                "priceDiscountRate": 15,
                "shopName": "Loja Teste",
            }
        ]
    )

    scraper = ShopeeScraper(
        termos_busca=["SSD NVMe"],
        service=service,
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert len(ofertas) == 1

    oferta = ofertas[0]

    assert oferta.nome == "SSD NVMe 1TB"
    assert oferta.loja == "Shopee"
    assert oferta.preco == 299.90
    assert oferta.preco_antigo is None
    assert oferta.desconto_anunciado == 15.0
    assert oferta.marketplace == "shopee"
    assert oferta.id_produto == "123"
    assert oferta.id_anuncio == "123"
    assert oferta.imagem == "https://example.com/ssd.jpg"


def test_remove_mesmo_produto_entre_termos() -> None:
    service = ShopeeApiServiceFake(
        [
            {
                "itemId": 123,
                "productName": "SSD NVMe 1TB",
                "productLink": ("https://shopee.com.br/product/10/123"),
                "imageUrl": None,
                "priceMin": "299.90",
                "priceMax": "299.90",
                "priceDiscountRate": 0,
            }
        ]
    )

    scraper = ShopeeScraper(
        termos_busca=[
            "SSD NVMe",
            "SSD 1TB",
        ],
        service=service,
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert len(ofertas) == 1
    assert service.chamadas == [
        "SSD NVMe",
        "SSD 1TB",
    ]


def test_ignora_produto_sem_preco_valido() -> None:
    service = ShopeeApiServiceFake(
        [
            {
                "itemId": 123,
                "productName": "Produto inv?lido",
                "productLink": ("https://shopee.com.br/product/10/123"),
                "priceMin": "0",
            }
        ]
    )

    scraper = ShopeeScraper(
        termos_busca=["teste"],
        service=service,
    )

    assert scraper.buscar_ofertas(limite=5) == []


def test_limite_invalido_nao_consulta_api() -> None:
    service = ShopeeApiServiceFake([])

    scraper = ShopeeScraper(
        termos_busca=["SSD NVMe"],
        service=service,
    )

    assert scraper.buscar_ofertas(limite=0) == []
    assert service.chamadas == []
