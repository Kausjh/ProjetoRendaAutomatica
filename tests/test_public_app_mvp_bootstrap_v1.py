from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_bootstrap_files_exist():
    expected = [
        APP / "package.json",
        APP / "package-lock.json",
        APP / "app.json",
        APP / "tsconfig.json",
        APP / "expo-env.d.ts",
        APP / ".gitignore",
        APP / ".env.example",
        APP / "app" / "_layout.tsx",
        APP / "app" / "index.tsx",
        APP / "src" / "config" / "runtime-config.ts",
        APP / "src" / "storage" / "secure-runtime-config.ts",
    ]

    missing = [str(path) for path in expected if not path.is_file()]
    assert not missing, missing


def test_package_has_required_foundation_dependencies():
    package = _json(APP / "package.json")
    dependencies = package["dependencies"]

    for name in [
        "expo",
        "expo-router",
        "expo-secure-store",
        "react",
        "react-native",
        "@tanstack/react-query",
    ]:
        assert name in dependencies

    assert package["main"] == "expo-router/entry"
    assert "typecheck" in package["scripts"]


def test_typescript_is_strict():
    config = _json(APP / "tsconfig.json")
    compiler = config["compilerOptions"]

    assert compiler["strict"] is True
    assert compiler["noUncheckedIndexedAccess"] is True
    assert compiler["noImplicitOverride"] is True


def test_expo_config_uses_router_and_secure_store():
    config = _json(APP / "app.json")["expo"]

    assert "expo-router" in config["plugins"]
    assert "expo-secure-store" in config["plugins"]
    assert config["android"]["package"] == "com.rendaautomatica.app"


def test_query_provider_is_bootstrapped():
    layout = (APP / "app" / "_layout.tsx").read_text(encoding="utf-8")

    assert "QueryClientProvider" in layout
    assert "expo-router" in layout


def test_secure_store_handles_runtime_credentials():
    source = (APP / "src" / "storage" / "secure-runtime-config.ts").read_text(encoding="utf-8")

    assert 'from "expo-secure-store"' in source
    assert "INFRASTRUCTURE_TOKEN_KEY" in source
    assert "USER_SESSION_KEY" in source


def test_no_infrastructure_secret_is_bundled_or_committed():
    forbidden = [
        "API_APLICACAO_TOKEN=",
        "100.73.126.112",
        ":8765",
    ]

    inspected = [
        APP / "package.json",
        APP / "app.json",
        APP / ".env.example",
        APP / "app" / "_layout.tsx",
        APP / "app" / "index.tsx",
        APP / "src" / "config" / "runtime-config.ts",
        APP / "src" / "storage" / "secure-runtime-config.ts",
    ]

    for path in inspected:
        content = path.read_text(encoding="utf-8")
        for value in forbidden:
            assert value not in content, (path, value)


def test_bootstrap_contract_matches_stage():
    contract = _json(ROOT / "contracts" / "public_app_mvp_bootstrap_v1.json")

    assert contract["bootstrap_version"] == 1
    assert contract["source_root"] == "apps/public-mobile"
    assert contract["foundation"]["api_client_implemented"] is False
    assert contract["boundaries"]["admin_port_8765_used"] is False
