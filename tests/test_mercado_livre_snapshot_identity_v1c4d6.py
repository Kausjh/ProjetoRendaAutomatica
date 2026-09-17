# 63.8738, -149.7525

from __future__ import annotations

from scrapers.mercado_livre_scraper import (
    MercadoLivreScraper,
)
from services.scout.mercado_livre_catalog_api import (
    SnapshotCatalogoMercadoLivre,
)

PRODUCT_ID = "MLB54058619"
ITEM_ID = "MLB6660104822"

LINK_WEB = (
    "https://www.mercadolivre.com.br/" "ssd-macrovip-mvgld256gb-nvme-m2-2280/" "p/MLB54058619"
)


def _snapshot(
    *,
    product_id: str = PRODUCT_ID,
    item_id: str = ITEM_ID,
    permalink: str | None = None,
) -> SnapshotCatalogoMercadoLivre:
    return SnapshotCatalogoMercadoLivre(
        product_id=product_id,
        item_id=item_id,
        titulo=("SSD Macrovip MVGLD/256GB " "NVMe M.2 2280 PCIe 3.0"),
        preco=354.05,
        currency_id="BRL",
        seller_id=132204345,
        permalink=permalink,
    )


def test_snapshot_preserva_identidade_ml_na_oferta():
    oferta = MercadoLivreScraper._oferta_de_snapshot(
        _snapshot(),
        link_fallback=LINK_WEB,
    )

    assert oferta is not None

    assert oferta.marketplace == "mercado_livre"
    assert oferta.id_produto == PRODUCT_ID
    assert oferta.id_anuncio == ITEM_ID

    assert oferta.link == LINK_WEB


def test_snapshot_normaliza_ids_ml():
    oferta = MercadoLivreScraper._oferta_de_snapshot(
        _snapshot(
            product_id=" mlb54058619 ",
            item_id=" mlb6660104822 ",
        ),
        link_fallback=LINK_WEB,
    )

    assert oferta is not None

    assert oferta.id_produto == PRODUCT_ID
    assert oferta.id_anuncio == ITEM_ID


def test_permalink_api_mantem_identidade_do_snapshot():
    link_api = "https://produto.mercadolivre.com.br/" "MLB-6660104822"

    oferta = MercadoLivreScraper._oferta_de_snapshot(
        _snapshot(
            permalink=link_api,
        ),
        link_fallback=LINK_WEB,
    )

    assert oferta is not None

    assert oferta.link == link_api
    assert oferta.marketplace == "mercado_livre"
    assert oferta.id_produto == PRODUCT_ID
    assert oferta.id_anuncio == ITEM_ID
