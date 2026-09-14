from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESENTER = ROOT / "apps" / "public-mobile" / "src" / "offers" / "offer-presenter.ts"
PRODUCT = ROOT / "apps" / "public-mobile" / "app" / "product" / "[canonicalKey].tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_product_detail_uses_current_price_records_for_real_offer_link():
    source = _read(PRESENTER)

    assert "root.precos_atuais" in source
    assert '"marketplace_melhor_preco"' in source
    assert '"preco_minimo_atual"' in source
    assert "const bestCurrentPriceRecord" in source
    assert "detailRecord.url = currentPriceUrl" in source


def test_current_price_link_mapping_requires_a_real_url():
    source = _read(PRESENTER)

    assert "firstString(bestCurrentPriceRecord, [" in source
    assert '"link"' in source
    assert '"link_publicacao"' in source
    assert '"product_url"' in source


def test_product_screen_opens_presented_offer_url():
    source = _read(PRODUCT)

    assert "Linking.openURL(productUrl)" in source
    assert "product.data.productUrl" in source
    assert '"Ver oferta"' in source
