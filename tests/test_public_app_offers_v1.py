from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
OFFERS = APP / "src" / "offers"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, object]:
    return json.loads(_read(path))


def test_offers_source_files_exist():
    expected = [
        OFFERS / "offer-types.ts",
        OFFERS / "offer-presenter.ts",
        OFFERS / "offer-queries.ts",
        OFFERS / "index.ts",
        APP / "app" / "product" / "[canonicalKey].tsx",
    ]

    assert all(path.is_file() for path in expected)


def test_presenter_decouples_ui_from_raw_backend_payload():
    source = _read(OFFERS / "offer-presenter.ts")

    assert "presentProductList" in source
    assert "presentProductDetail" in source
    assert "presentPriceHistory" in source
    assert "normalizeProduct" in source
    assert "extractArray" in source
    assert "chave_canonica" in source
    assert "canonical_key" in source


def test_offer_queries_use_existing_public_api_client():
    source = _read(OFFERS / "offer-queries.ts")

    assert "createPublicApiClient" in source
    assert "api.listProducts" in source
    assert "api.getProduct(canonicalKey)" in source
    assert "api.getProductHistory" in source
    assert "useQuery" in source


def test_home_renders_product_list_and_refresh():
    source = _read(APP / "app" / "home.tsx")

    assert "useProductList(50, 0)" in source
    assert "<FlatList" in source
    assert "<RefreshControl" in source
    assert "products.refetch()" in source
    assert 'pathname: "/product/[canonicalKey]"' in source


def test_home_remains_protected():
    source = _read(APP / "app" / "home.tsx")

    assert 'snapshot.status !== "authenticated"' in source
    assert '<Redirect href="/"' in source


def test_detail_uses_canonical_key_and_history():
    source = _read(APP / "app" / "product" / "[canonicalKey].tsx")

    assert "useLocalSearchParams" in source
    assert "useProductDetail(canonicalKey)" in source
    assert "useProductHistory(canonicalKey, 50)" in source
    assert "formatHistoryTimestamp" in source


def test_detail_remains_protected():
    source = _read(APP / "app" / "product" / "[canonicalKey].tsx")

    assert 'snapshot.status !== "authenticated"' in source
    assert '<Redirect href="/"' in source


def test_root_layout_registers_product_detail_route():
    source = _read(APP / "app" / "_layout.tsx")

    assert 'name="product/[canonicalKey]"' in source
    assert 'title: "Ofertas"' in source


def test_offers_ui_contains_no_transport_credentials():
    paths = [
        APP / "app" / "home.tsx",
        APP / "app" / "product" / "[canonicalKey].tsx",
        *OFFERS.glob("*.ts"),
    ]

    forbidden = [
        "100.73.126.112",
        "API_APLICACAO_TOKEN",
        "X-User-Session",
        "Authorization",
    ]

    for path in paths:
        source = _read(path)

        for value in forbidden:
            assert value not in source, (path, value)


def test_contract_matches_scope_and_next_step():
    contract = _json(ROOT / "contracts" / "public_app_offers_v1.json")

    assert contract["offers_ui_version"] == 1
    assert contract["presentation"]["adapter_tolerates_optional_fields"] is True
    assert contract["presentation"]["raw_backend_payload_bound_directly_to_ui"] is False
    assert contract["boundaries"]["watchlist_ui"] is False
    assert contract["next_step"] == "public-app-mvp-watchlist-v1"
