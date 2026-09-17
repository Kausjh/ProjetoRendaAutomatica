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
from services.scout.mercado_livre_web_discovery import (
    ErroDiscoveryMercadoLivre,
    ResultadoDiscoveryMercadoLivre,
)

LINK_WEB = "https://www.mercadolivre.com.br/" "ssd-nvme/p/MLB54058619"


def _snapshot(
    product_id="MLB54058619",
    item_id="MLB6660104822",
    *,
    permalink=None,
):
    return SnapshotCatalogoMercadoLivre(
        product_id=product_id,
        item_id=item_id,
        titulo="SSD NVMe teste",
        preco=354.05,
        currency_id="BRL",
        seller_id=132204345,
        permalink=permalink,
    )


class DiscoverySucesso:
    def __init__(self, resultados):
        self.resultados = tuple(resultados)
        self.chamadas = []

    def descobrir(
        self,
        consulta,
        *,
        limite=5,
    ):
        self.chamadas.append((consulta, limite))

        return self.resultados[:limite]


class DiscoveryFalha:
    def descobrir(
        self,
        consulta,
        *,
        limite=5,
    ):
        raise ErroDiscoveryMercadoLivre("mercado_livre_web_indisponivel")


class ClienteSomenteSnapshot:
    def __init__(self, snapshots):
        self.snapshots = dict(snapshots)
        self.consultados = []

    def consultar_snapshot(
        self,
        product_id,
    ):
        self.consultados.append(product_id)

        valor = self.snapshots[product_id]

        if isinstance(
            valor,
            Exception,
        ):
            raise valor

        return valor

    def descobrir_dominios(
        self,
        consulta,
        limite=3,
    ):
        raise AssertionError("Catalog fallback nao deveria " "ser usado.")

    def buscar_produtos(
        self,
        consulta,
        *,
        domain_id=None,
        limite=5,
    ):
        raise AssertionError("products/search nao deveria " "ser usado.")


class ClienteFallbackCatalogo:
    def __init__(self):
        self.dominios = 0
        self.buscas = 0
        self.snapshots = []

    def descobrir_dominios(
        self,
        consulta,
        limite=3,
    ):
        self.dominios += 1

        return (
            DominioCatalogoMercadoLivre(
                domain_id=("MLB-HARD_DRIVES_AND_SSDS"),
                domain_name="Armazenamento",
                category_id="MLB1672",
                category_name="Armazenamento",
            ),
        )

    def buscar_produtos(
        self,
        consulta,
        *,
        domain_id=None,
        limite=5,
    ):
        self.buscas += 1

        return (
            ProdutoCatalogoMercadoLivre(
                product_id="MLB70000001",
                titulo="SSD fallback",
                domain_id=domain_id,
                status="active",
            ),
        )

    def consultar_snapshot(
        self,
        product_id,
    ):
        self.snapshots.append(product_id)

        return SnapshotCatalogoMercadoLivre(
            product_id=product_id,
            item_id="MLB7000000101",
            titulo="SSD fallback",
            preco=299.90,
            currency_id="BRL",
            seller_id=123,
            permalink=("https://www.mercadolivre.com.br/" "ssd-fallback/p/MLB70000001"),
        )


def test_web_pdp_vivo_vira_oferta_sem_products_search():
    discovery = DiscoverySucesso(
        [
            ResultadoDiscoveryMercadoLivre(
                identificador_ml="MLB54058619",
                titulo="SSD NVMe teste",
                link=LINK_WEB,
            )
        ]
    )

    cliente = ClienteSomenteSnapshot(
        {
            "MLB54058619": _snapshot(),
        }
    )

    scraper = MercadoLivreScraper(
        termos_busca=["SSD NVMe"],
        cliente_catalogo=cliente,
        web_discovery=discovery,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert len(ofertas) == 1
    assert ofertas[0].preco == 354.05
    assert ofertas[0].link == LINK_WEB

    assert cliente.consultados == ["MLB54058619"]


def test_web_snapshot_404_tenta_proximo_pdp():
    discovery = DiscoverySucesso(
        [
            ResultadoDiscoveryMercadoLivre(
                identificador_ml="MLB11111111",
                titulo="SSD antigo",
                link=("https://www.mercadolivre.com.br/" "ssd-antigo/p/MLB11111111"),
            ),
            ResultadoDiscoveryMercadoLivre(
                identificador_ml="MLB54058619",
                titulo="SSD atual",
                link=LINK_WEB,
            ),
        ]
    )

    cliente = ClienteSomenteSnapshot(
        {
            "MLB11111111": ErroApiMercadoLivre(
                "api_mercado_livre_nao_encontrado",
                status_code=404,
                transitorio=False,
            ),
            "MLB54058619": _snapshot(),
        }
    )

    scraper = MercadoLivreScraper(
        termos_busca=["SSD NVMe"],
        cliente_catalogo=cliente,
        web_discovery=discovery,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert len(ofertas) == 1

    assert cliente.consultados == [
        "MLB11111111",
        "MLB54058619",
    ]


def test_falha_web_cai_no_catalogo_existente():
    cliente = ClienteFallbackCatalogo()

    scraper = MercadoLivreScraper(
        termos_busca=["SSD NVMe"],
        cliente_catalogo=cliente,
        web_discovery=DiscoveryFalha(),
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert len(ofertas) == 1
    assert ofertas[0].nome == "SSD fallback"

    assert cliente.dominios == 1
    assert cliente.buscas == 1


def test_cliente_injetado_nao_ativa_web_implicitamente():
    cliente = ClienteFallbackCatalogo()

    scraper = MercadoLivreScraper(
        termos_busca=["SSD NVMe"],
        cliente_catalogo=cliente,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    assert scraper.web_discovery is None

    ofertas = scraper.buscar_ofertas(limite=1)

    assert len(ofertas) == 1
    assert cliente.dominios == 1


def test_web_deduplica_product_id():
    discovery = DiscoverySucesso(
        [
            ResultadoDiscoveryMercadoLivre(
                identificador_ml="MLB54058619",
                titulo="SSD A",
                link=LINK_WEB,
            ),
            ResultadoDiscoveryMercadoLivre(
                identificador_ml="mlb54058619",
                titulo="SSD duplicado",
                link=LINK_WEB,
            ),
        ]
    )

    cliente = ClienteSomenteSnapshot(
        {
            "MLB54058619": _snapshot(),
        }
    )

    scraper = MercadoLivreScraper(
        termos_busca=["SSD NVMe"],
        cliente_catalogo=cliente,
        web_discovery=discovery,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    ofertas = scraper.buscar_ofertas(limite=2)

    assert len(ofertas) == 1

    assert cliente.consultados == ["MLB54058619"]
