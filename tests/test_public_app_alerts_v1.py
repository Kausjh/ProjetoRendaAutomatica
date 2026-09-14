from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
ALERTS = APP / "src" / "alerts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, object]:
    return json.loads(_read(path))


def test_alert_source_files_exist():
    expected = [
        ALERTS / "alert-types.ts",
        ALERTS / "alert-presenter.ts",
        ALERTS / "alert-queries.ts",
        ALERTS / "index.ts",
        APP / "app" / "alerts.tsx",
    ]

    assert all(path.is_file() for path in expected)


def test_alert_presenter_supports_expected_optional_fields():
    source = _read(ALERTS / "alert-presenter.ts")

    assert "presentAlertList" in source
    assert "chave_canonica" in source
    assert "preco_anterior" in source
    assert "preco_atual" in source
    assert "marketplace" in source
    assert "formatAlertTimestamp" in source


def test_alert_queries_use_existing_read_only_api():
    source = _read(ALERTS / "alert-queries.ts")

    assert "api.listAlerts" in source
    assert "presentAlertList" in source
    assert "useQuery" in source
    assert "limite" in source
    assert "offset" in source


def test_alert_screen_is_app_auth_guarded():
    source = _read(APP / "app" / "alerts.tsx")

    assert 'snapshot.status !== "authenticated"' in source
    assert '<Redirect href="/"' in source


def test_alert_screen_has_loading_error_empty_and_refresh():
    source = _read(APP / "app" / "alerts.tsx")

    assert "alerts.isPending" in source
    assert "alerts.isError" in source
    assert "ListEmptyComponent" in source
    assert "<RefreshControl" in source
    assert "alerts.refetch()" in source


def test_alert_screen_navigates_to_product_when_key_exists():
    source = _read(APP / "app" / "alerts.tsx")

    assert "item.canonicalKey" in source
    assert 'pathname: "/product/[canonicalKey]"' in source


def test_home_links_to_alerts():
    source = _read(APP / "app" / "home.tsx")

    assert 'router.push("/alerts")' in source


def test_root_layout_registers_alerts_route():
    source = _read(APP / "app" / "_layout.tsx")

    assert 'name="alerts"' in source


def test_alert_ui_does_not_handle_transport_headers_or_credentials():
    paths = [
        APP / "app" / "alerts.tsx",
        *ALERTS.glob("*.ts"),
    ]

    forbidden = [
        "API_APLICACAO_TOKEN",
        "X-User-Session",
        "Authorization",
        "100.73.126.112",
    ]

    for path in paths:
        source = _read(path)

        for value in forbidden:
            assert value not in source, (path, value)


def test_contract_keeps_personalized_features_out_of_scope():
    contract = _json(ROOT / "contracts" / "public_app_alerts_v1.json")

    assert contract["alerts_ui_version"] == 1
    assert contract["features"]["list_alerts"] is True
    assert contract["features"]["product_navigation_when_canonical_key_exists"] is True
    assert contract["semantics"]["personalized_feed"] is False
    assert contract["semantics"]["push_delivery"] is False
    assert contract["next_step"] == "public-app-mvp-android-smoke-v1"
