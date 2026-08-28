import json

from services.shopee_api_service import ShopeeApiService


class RespostaFake:
    def __init__(self, dados: dict) -> None:
        self.dados = dados

    def __enter__(self) -> "RespostaFake":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.dados).encode("utf-8")


def test_gera_shortlink(monkeypatch) -> None:
    requisicao_capturada = {}

    def urlopen_fake(requisicao, timeout):
        requisicao_capturada["requisicao"] = requisicao
        requisicao_capturada["timeout"] = timeout

        return RespostaFake(
            {"data": {"generateShortLink": {"shortLink": ("https://s.shopee.com.br/6L40LOAkOW")}}}
        )

    monkeypatch.setattr(
        "services.shopee_api_service.urllib.request.urlopen",
        urlopen_fake,
    )

    service = ShopeeApiService(
        app_id="app-teste",
        secret="segredo-teste",
    )

    resultado = service.gerar_shortlink("https://shopee.com.br/product/701693560/22797310651")

    assert resultado == "https://s.shopee.com.br/6L40LOAkOW"
    assert requisicao_capturada["timeout"] == 30.0

    requisicao = requisicao_capturada["requisicao"]

    authorization = requisicao.get_header("Authorization")

    assert authorization is not None
    assert authorization.startswith("SHA256 Credential=app-teste, ")

    corpo = json.loads(requisicao.data.decode("utf-8"))

    assert "generateShortLink" in corpo["query"]
    assert "shopee.com.br/product/701693560/22797310651" in (corpo["query"])


def test_busca_produtos(monkeypatch) -> None:
    requisicao_capturada = {}

    def urlopen_fake(requisicao, timeout):
        requisicao_capturada["requisicao"] = requisicao
        requisicao_capturada["timeout"] = timeout

        return RespostaFake(
            {
                "data": {
                    "productOfferV2": {
                        "nodes": [
                            {
                                "itemId": 123,
                                "productName": "SSD NVMe 1TB",
                                "productLink": ("https://shopee.com.br/product/10/123"),
                                "priceMin": "299.90",
                            }
                        ],
                        "pageInfo": {
                            "page": 1,
                            "limit": 5,
                            "hasNextPage": False,
                        },
                    }
                }
            }
        )

    monkeypatch.setattr(
        "services.shopee_api_service.urllib.request.urlopen",
        urlopen_fake,
    )

    service = ShopeeApiService(
        app_id="app-teste",
        secret="segredo-teste",
    )

    produtos = service.buscar_produtos(
        termo="SSD NVMe",
        limite=5,
    )

    assert len(produtos) == 1
    assert produtos[0]["itemId"] == 123

    requisicao = requisicao_capturada["requisicao"]

    corpo = json.loads(requisicao.data.decode("utf-8"))

    assert "productOfferV2" in corpo["query"]
    assert 'keyword: "SSD NVMe"' in corpo["query"]
    assert "limit: 5" in corpo["query"]
    assert requisicao_capturada["timeout"] == 30.0


def test_rejeita_limite_invalido_na_busca() -> None:
    service = ShopeeApiService(
        app_id="app-teste",
        secret="segredo-teste",
    )

    try:
        service.buscar_produtos(
            termo="SSD",
            limite=0,
        )
    except ValueError as erro:
        assert "entre 1 e 500" in str(erro)
    else:
        raise AssertionError("Era esperado ValueError para limite inv?lido.")


def test_rejeita_credenciais_ausentes() -> None:
    service = ShopeeApiService(
        app_id="",
        secret="",
    )

    try:
        service.gerar_shortlink("https://shopee.com.br/product/1/2")
    except ValueError as erro:
        assert "SHOPEE_APP_ID" in str(erro)
    else:
        raise AssertionError("Era esperado ValueError sem credenciais.")


def test_rejeita_erro_graphql(monkeypatch) -> None:
    def urlopen_fake(requisicao, timeout):
        del requisicao
        del timeout

        return RespostaFake({"errors": [{"message": ("error [11001]: Params Error")}]})

    monkeypatch.setattr(
        "services.shopee_api_service.urllib.request.urlopen",
        urlopen_fake,
    )

    service = ShopeeApiService(
        app_id="app-teste",
        secret="segredo-teste",
    )

    try:
        service.gerar_shortlink("https://shopee.com.br/product/1/2")
    except RuntimeError as erro:
        assert "11001" in str(erro)
    else:
        raise AssertionError("Era esperado RuntimeError para erro GraphQL.")
