# 63.8738, -149.7525

from __future__ import annotations

from scrapers.mercado_livre_scraper import (
    MercadoLivreScraper,
)
from services.scout.mercado_livre_catalog_api import (
    SnapshotCatalogoMercadoLivre,
)


def _snapshot(
    *,
    permalink=None,
):
    return SnapshotCatalogoMercadoLivre(
        product_id="MLB54058619",
        item_id="MLB6660104822",
        titulo=("SSD Macrovip MVGLD/256GB NVMe " "M.2 2280 PCIe 3.0"),
        preco=354.05,
        currency_id="BRL",
        seller_id=132204345,
        permalink=permalink,
    )


def test_snapshot_sem_permalink_usa_link_do_discovery():
    link_web = (
        "https://www.mercadolivre.com.br/" "ssd-macrovip-mvgld256gb-nvme-m2-2280/" "p/MLB54058619"
    )

    oferta = MercadoLivreScraper._oferta_de_snapshot(
        _snapshot(),
        link_fallback=link_web,
    )

    assert oferta is not None
    assert oferta.link == link_web
    assert oferta.nome.startswith("SSD Macrovip")
    assert oferta.preco == 354.05
    assert oferta.loja == "Mercado Livre"


def test_permalink_da_api_tem_prioridade_sobre_fallback():
    link_api = "https://produto.mercadolivre.com.br/" "MLB-6660104822"

    link_web = "https://www.mercadolivre.com.br/" "produto/p/MLB54058619"

    oferta = MercadoLivreScraper._oferta_de_snapshot(
        _snapshot(
            permalink=link_api,
        ),
        link_fallback=link_web,
    )

    assert oferta is not None
    assert oferta.link == link_api


def test_sem_permalink_e_sem_fallback_continua_ignorado():
    oferta = MercadoLivreScraper._oferta_de_snapshot(
        _snapshot(),
    )

    assert oferta is None
