from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
ROUTES = APP / "app"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, object]:
    return json.loads(_read(path))


def test_auth_ui_routes_exist():
    expected = [
        ROUTES / "index.tsx",
        ROUTES / "connection.tsx",
        ROUTES / "login.tsx",
        ROUTES / "register.tsx",
        ROUTES / "home.tsx",
    ]

    assert all(path.is_file() for path in expected)


def test_entry_gate_checks_config_and_auth_state():
    source = _read(ROUTES / "index.tsx")

    assert "loadRuntimeConfig" in source
    assert "isRuntimeConfigComplete" in source
    assert '<Redirect href="/connection"' in source
    assert '<Redirect href="/home"' in source
    assert '<Redirect href="/login"' in source
    assert "snapshot.status" in source
    assert "restore()" in source


def test_connection_screen_never_prefills_real_endpoint_or_secret():
    source = _read(ROUTES / "connection.tsx")

    assert "loadRuntimeConfig" in source
    assert "saveRuntimeConfig" in source
    assert "clearUserSession" in source
    assert "requireRuntimeConfig" in source
    assert "secureTextEntry" in source

    forbidden = [
        "100.73.126.112",
        "API_APLICACAO_TOKEN=",
        "pra_usr_v1_",
    ]

    for value in forbidden:
        assert value not in source


def test_connection_change_clears_user_session():
    source = _read(ROUTES / "connection.tsx")

    assert "configChanged" in source
    assert "await clearUserSession()" in source
    assert "await restore()" in source


def test_login_uses_auth_provider_and_secure_password_input():
    source = _read(ROUTES / "login.tsx")

    assert "useAuthSession" in source
    assert "await login({" in source
    assert "secureTextEntry" in source
    assert 'router.replace("/home")' in source
    assert 'router.push("/register")' in source


def test_register_confirms_password_and_does_not_save_session():
    source = _read(ROUTES / "register.tsx")

    assert "senha !== confirmacao" in source
    assert "await register({" in source
    assert 'router.replace("/login")' in source
    assert "saveUserSession" not in source


def test_home_is_protected_and_account_supports_logout():
    home_source = _read(ROUTES / "home.tsx")
    account_source = _read(ROUTES / "account.tsx")

    assert 'snapshot.status !== "authenticated"' in home_source
    assert '<Redirect href="/"' in home_source
    assert "await logout()" in account_source
    assert 'router.replace("/")' in account_source


def test_root_stack_registers_auth_routes():
    source = _read(ROUTES / "_layout.tsx")

    for route in [
        'name="index"',
        'name="connection"',
        'name="login"',
        'name="register"',
        'name="home"',
    ]:
        assert route in source


def test_auth_ui_does_not_log_credentials():
    for name in [
        "index.tsx",
        "connection.tsx",
        "login.tsx",
        "register.tsx",
        "home.tsx",
    ]:
        source = _read(ROUTES / name)

        assert "console.log" not in source
        assert "console.error" not in source


def test_contract_matches_scope_and_next_step():
    contract = _json(ROOT / "contracts" / "public_app_auth_ui_v1.json")

    assert contract["auth_ui_version"] == 1
    assert contract["connection"]["real_endpoint_bundled"] is False
    assert contract["connection"]["changed_config_clears_user_session"] is True
    assert contract["register"]["auto_login"] is False
    assert contract["protected_home"]["offers_implemented"] is False
    assert contract["next_step"] == "public-app-mvp-offers-v1"
