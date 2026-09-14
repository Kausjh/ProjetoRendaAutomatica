from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
ACCOUNT = APP / "src" / "account"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, object]:
    return json.loads(_read(path))


def test_account_source_files_exist():
    expected = [
        ACCOUNT / "account-types.ts",
        ACCOUNT / "account-presenter.ts",
        ACCOUNT / "account-queries.ts",
        ACCOUNT / "index.ts",
        APP / "app" / "account.tsx",
    ]

    assert all(path.is_file() for path in expected)


def test_presenter_supports_preferences_contract_fields():
    source = _read(ACCOUNT / "account-presenter.ts")

    assert "notificacoes_preco_habilitadas" in source
    assert "marketplaces_preferidos" in source
    assert "presentAccountPreferences" in source
    assert "normalizeMarketplaceInput" in source


def test_marketplace_input_is_trimmed_filtered_and_deduplicated():
    source = _read(ACCOUNT / "account-presenter.ts")

    assert '.split(",")' in source
    assert ".map((item) => item.trim())" in source
    assert ".filter(Boolean)" in source
    assert "[...new Set(normalized)]" in source


def test_preferences_queries_use_existing_api_and_invalidate_cache():
    source = _read(ACCOUNT / "account-queries.ts")

    assert "api.getPreferences()" in source
    assert "api.patchPreferences" in source
    assert "notificacoes_preco_habilitadas" in source
    assert "marketplaces_preferidos" in source
    assert "invalidateQueries" in source


def test_account_screen_is_protected_and_uses_auth_snapshot():
    source = _read(APP / "app" / "account.tsx")

    assert 'snapshot.status === "authenticated"' in source
    assert '<Redirect href="/"' in source
    assert "snapshot.account" in source
    assert "refreshMe" in source


def test_account_screen_edits_price_notifications_and_marketplaces():
    source = _read(APP / "app" / "account.tsx")

    assert "<Switch" in source
    assert "priceNotificationsEnabled" in source
    assert "marketplacesText" in source
    assert "normalizeMarketplaceInput" in source
    assert "savePreferences.mutateAsync" in source


def test_account_screen_supports_connection_and_logout():
    source = _read(APP / "app" / "account.tsx")

    assert 'router.push("/connection")' in source
    assert "await logout()" in source
    assert 'router.replace("/")' in source


def test_bottom_nav_links_to_account():
    source = _read(APP / "src" / "ui" / "bottom-nav.tsx")

    assert 'route: "/account"' in source
    assert 'label: "Perfil"' in source
    assert "router.replace(item.route)" in source


def test_root_layout_registers_account_route():
    source = _read(APP / "app" / "_layout.tsx")

    assert 'name="account"' in source


def test_account_ui_does_not_handle_transport_headers_or_credentials():
    paths = [
        APP / "app" / "account.tsx",
        *ACCOUNT.glob("*.ts"),
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


def test_contract_matches_scope_and_next_step():
    contract = _json(ROOT / "contracts" / "public_app_account_preferences_v1.json")

    assert contract["account_preferences_ui_version"] == 1
    assert contract["account"]["manual_refresh"] is True
    assert contract["preferences"]["price_notifications_toggle"] is True
    assert contract["preferences"]["preferred_marketplaces_deduplicated"] is True
    assert contract["security"]["account_id_sent_by_client"] is False
    assert contract["boundaries"]["alerts_ui"] is False
    assert contract["next_step"] == "public-app-mvp-alerts-v1"
