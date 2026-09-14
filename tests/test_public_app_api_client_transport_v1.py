from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
API = APP / "src" / "api"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, object]:
    return json.loads(_read(path))


def test_api_client_transport_files_exist():
    expected = [
        API / "api-error.ts",
        API / "api-types.ts",
        API / "http-transport.ts",
        API / "public-api-client.ts",
        API / "create-public-api-client.ts",
        API / "index.ts",
    ]

    assert all(path.is_file() for path in expected)


def test_transport_separates_infrastructure_and_user_session():
    source = _read(API / "http-transport.ts")

    assert "Authorization" in source
    assert "Bearer ${config.infrastructureToken}" in source
    assert 'headers["X-User-Session"] = userSession' in source
    assert "requiresUserSession" in source
    assert "console.log" not in source
    assert "console.error" not in source


def test_transport_has_timeout_retry_after_and_network_mapping():
    source = _read(API / "http-transport.ts")

    assert "AbortController" in source
    assert "Retry-After" in source
    assert "timeout_cliente" in source
    assert "falha_rede" in source
    assert "resposta_json_invalida" in source


def test_client_covers_read_only_and_user_facing_routes():
    source = _read(API / "public-api-client.ts")

    expected = [
        'path: "/health"',
        'path: "/produtos"',
        'path: "/alertas"',
        'path: "/auth/register"',
        'path: "/auth/login"',
        'path: "/auth/logout"',
        'path: "/me"',
        'path: "/me/preferences"',
        'path: "/me/watchlist"',
    ]

    for item in expected:
        assert item in source

    assert "/historico" in source
    assert "encodeURIComponent(canonicalKey)" in source


def test_authenticated_routes_require_user_session():
    source = _read(API / "public-api-client.ts")

    assert source.count("requiresUserSession: true") >= 6
    assert 'path: "/auth/login"' in source
    assert 'path: "/auth/register"' in source


def test_response_modes_preserve_existing_contract_split():
    source = _read(API / "public-api-client.ts")

    assert 'responseMode: "raw-json"' in source
    assert 'responseMode: "user-facing-envelope"' in source


def test_runtime_config_requires_api_v1_and_rejects_admin_port():
    source = _read(APP / "src" / "config" / "runtime-config.ts")

    assert 'parsed.port === "8765"' in source
    assert 'parsed.pathname.endsWith("/api/v1")' in source
    assert "EXPO_PUBLIC_" not in source


def test_factory_uses_secure_store_loaders_indirectly():
    source = _read(API / "create-public-api-client.ts")

    assert "loadRuntimeConfig" in source
    assert "loadUserSession" in source
    assert "HttpApiTransport" in source
    assert "PublicApiClient" in source


def test_no_real_transport_secret_or_host_is_bundled():
    forbidden = [
        "100.73.126.112",
        "API_APLICACAO_TOKEN=",
        "pra_usr_v1_real",
    ]

    for path in API.glob("*.ts"):
        source = _read(path)

        for value in forbidden:
            assert value not in source, (path, value)


def test_contract_documents_boundaries():
    contract = _json(ROOT / "contracts" / "public_app_api_client_transport_v1.json")

    assert contract["client_transport_version"] == 1
    assert contract["transport"]["ui_knows_transport_details"] is False
    assert contract["transport"]["admin_port_8765_allowed"] is False
    assert contract["authentication"]["user_session_only_when_required"] is True
    assert contract["boundaries"]["ui_changes"] is False
    assert contract["next_step"] == "public-app-mvp-auth-session-v1"
