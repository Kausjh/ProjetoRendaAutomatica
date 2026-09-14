from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
WATCHLIST = APP / "src" / "watchlist"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, object]:
    return json.loads(_read(path))


def test_watchlist_source_files_exist():
    expected = [
        WATCHLIST / "watchlist-types.ts",
        WATCHLIST / "watchlist-presenter.ts",
        WATCHLIST / "watchlist-queries.ts",
        WATCHLIST / "index.ts",
        APP / "app" / "watchlist.tsx",
    ]

    assert all(path.is_file() for path in expected)


def test_presenter_accepts_watchlist_contract_fields():
    source = _read(WATCHLIST / "watchlist-presenter.ts")

    assert "chave_canonica" in source
    assert "preco_alvo" in source
    assert "notificar_queda_preco" in source
    assert "presentWatchlist" in source


def test_queries_use_authenticated_watchlist_api():
    source = _read(WATCHLIST / "watchlist-queries.ts")

    assert "api.getWatchlist()" in source
    assert "api.putWatchlist" in source
    assert "api.deleteWatchlist" in source
    assert "preco_alvo" in source
    assert "notificar_queda_preco" in source


def test_mutations_invalidate_watchlist_cache():
    source = _read(WATCHLIST / "watchlist-queries.ts")

    assert source.count("invalidateQueries") >= 2
    assert "watchlistQueryKeys.all" in source


def test_watchlist_screen_is_protected_and_refreshable():
    source = _read(APP / "app" / "watchlist.tsx")

    assert 'snapshot.status === "authenticated"' in source
    assert '<Redirect href="/"' in source
    assert "<RefreshControl" in source
    assert "watchlist.refetch()" in source


def test_product_detail_supports_watchlist_upsert_and_delete():
    source = _read(APP / "app" / "product" / "[canonicalKey].tsx")

    assert "useWatchlist(authenticated)" in source
    assert "useUpsertWatchlist()" in source
    assert "useDeleteWatchlist()" in source
    assert "upsertWatchlist.mutateAsync" in source
    assert "deleteWatchlist.mutateAsync" in source


def test_product_detail_validates_target_price_and_toggle():
    source = _read(APP / "app" / "product" / "[canonicalKey].tsx")

    assert "parseTargetPrice" in source
    assert "parsed <= 0" in source
    assert "<Switch" in source
    assert "notifyPriceDrop" in source


def test_home_links_to_watchlist():
    source = _read(APP / "app" / "home.tsx")

    assert 'router.push("/watchlist")' in source


def test_root_layout_registers_watchlist_route():
    source = _read(APP / "app" / "_layout.tsx")

    assert 'name="watchlist"' in source


def test_watchlist_ui_does_not_handle_identity_or_transport_headers():
    paths = [
        APP / "app" / "watchlist.tsx",
        APP / "app" / "product" / "[canonicalKey].tsx",
        *WATCHLIST.glob("*.ts"),
    ]

    forbidden = [
        "conta_id",
        "API_APLICACAO_TOKEN",
        "X-User-Session",
        "Authorization",
        "100.73.126.112",
    ]

    for path in paths:
        source = _read(path)

        for value in forbidden:
            assert value not in source, (path, value)


def test_contract_matches_scope_and_next_step():
    contract = _json(ROOT / "contracts" / "public_app_watchlist_v1.json")

    assert contract["watchlist_ui_version"] == 1
    assert contract["features"]["add_item"] is True
    assert contract["features"]["update_item"] is True
    assert contract["features"]["remove_item"] is True
    assert contract["security"]["account_id_from_client"] is False
    assert contract["boundaries"]["preferences_ui"] is False
    assert contract["next_step"] == "public-app-mvp-account-preferences-v1"
