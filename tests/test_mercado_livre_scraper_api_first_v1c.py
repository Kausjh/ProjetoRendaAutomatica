# 63.8738, -149.7525

from __future__ import annotations

from scrapers.mercado_livre_scraper import (
    MercadoLivreScraper,
)
from services.scout.mercado_livre_catalog_api import (
    DominioCatalogoMercadoLivre,
    ErroApiMercadoLivre,
    ProdutoCatalogoMercadoLivre,
    SnapshotCatalogoMercadoLivre,
)


def _dominio_processador():
    return DominioCatalogoMercadoLivre(
        domain_id="MLB-COMPUTER_PROCESSORS",
        domain_name="Processadores",
        category_id="MLB1693",
        category_name="Processadores",
    )


def _produto(
    product_id,
    titulo,
):
    return ProdutoCatalogoMercadoLivre(
        product_id=product_id,
        titulo=titulo,
        domain_id="MLB-COMPUTER_PROCESSORS",
        status="active",
    )


def _snapshot(
    product_id,
    item_id,
    titulo,
    preco,
):
    return SnapshotCatalogoMercadoLivre(
        product_id=product_id,
        item_id=item_id,
        titulo=titulo,
        preco=preco,
        currency_id="BRL",
        seller_id=123,
        permalink=("https://www.mercadolivre.com.br/" f"produto-{product_id.lower()}"),
    )


class ClienteFake:
    def __init__(self):
        self.dominios = []
        self.buscas = []
        self.snapshots = []

    def descobrir_dominios(
        self,
        consulta,
        limite=3,
    ):
        self.dominios.append((consulta, limite))

        return (_dominio_processador(),)

    def buscar_produtos(
        self,
        consulta,
        *,
        domain_id=None,
        limite=5,
    ):
        self.buscas.append(
            (
                consulta,
                domain_id,
                limite,
            )
        )

        if "Ryzen 7" in consulta:
            produtos = (
                _produto(
                    "MLB70000001",
                    "Ryzen 7",
                ),
            )
        else:
            produtos = (
                _produto(
                    "MLB50000001",
                    "Ryzen 5",
                ),
            )

        return produtos[:limite]

    def consultar_snapshot(
        self,
        product_id,
    ):
        self.snapshots.append(product_id)

        if product_id == "MLB70000001":
            return _snapshot(
                product_id,
                "MLB111",
                "AMD Ryzen 7",
                999.90,
            )

        return _snapshot(
            product_id,
            "MLB222",
            "AMD Ryzen 5",
            599.90,
        )


def test_buscar_ofertas_usa_api_e_nao_playwright():
    cliente = ClienteFake()

    scraper = MercadoLivreScraper(
        termos_busca=[
            "Ryzen 7",
            "Ryzen 5",
        ],
        cliente_catalogo=cliente,
        sleep_fn=lambda _: None,
    )

    ofertas = scraper.buscar_ofertas(limite=2)

    assert len(ofertas) == 2

    assert [oferta.nome for oferta in ofertas] == [
        "AMD Ryzen 7",
        "AMD Ryzen 5",
    ]

    assert ofertas[0].loja == "Mercado Livre"
    assert ofertas[0].preco == 999.90

    assert ofertas[0].link.startswith("https://www.mercadolivre.com.br/")

    # Os dois termos pertencem a Processadores AMD.
    # O cache de dominio deve evitar nova descoberta.
    assert len(cliente.dominios) == 1

    assert cliente.dominios[0][0] == ("Processadores AMD Ryzen 7")

    assert len(cliente.buscas) == 2

    assert all(chamada[1] == "MLB-COMPUTER_PROCESSORS" for chamada in cliente.buscas)

    assert cliente.snapshots == [
        "MLB70000001",
        "MLB50000001",
    ]


def test_limite_e_global_e_interrompe_buscas():
    cliente = ClienteFake()

    scraper = MercadoLivreScraper(
        termos_busca=[
            "Ryzen 7",
            "Ryzen 5",
        ],
        cliente_catalogo=cliente,
        sleep_fn=lambda _: None,
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert len(ofertas) == 1
    assert len(cliente.buscas) == 1
    assert len(cliente.snapshots) == 1


class ClienteRateLimit(ClienteFake):
    def __init__(self):
        super().__init__()
        self.tentativas_busca = 0

    def buscar_produtos(
        self,
        consulta,
        *,
        domain_id=None,
        limite=5,
    ):
        self.tentativas_busca += 1

        if self.tentativas_busca == 1:
            raise ErroApiMercadoLivre(
                "api_mercado_livre_rate_limit",
                status_code=429,
                transitorio=True,
            )

        return super().buscar_produtos(
            consulta,
            domain_id=domain_id,
            limite=limite,
        )


def test_429_faz_backoff_e_repete():
    cliente = ClienteRateLimit()

    esperas = []

    scraper = MercadoLivreScraper(
        termos_busca=[
            "Ryzen 7",
        ],
        cliente_catalogo=cliente,
        sleep_fn=esperas.append,
        jitter_fn=lambda: 0.0,
        tentativas_rate_limit=2,
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert len(ofertas) == 1

    assert cliente.tentativas_busca == 2

    assert esperas == [
        2.0,
    ]


def test_limite_invalido_nao_chama_api():
    cliente = ClienteFake()

    scraper = MercadoLivreScraper(
        termos_busca=[
            "Ryzen 7",
        ],
        cliente_catalogo=cliente,
        sleep_fn=lambda _: None,
    )

    assert scraper.buscar_ofertas(limite=0) == []

    assert cliente.dominios == []
    assert cliente.buscas == []
    assert cliente.snapshots == []
