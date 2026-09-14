from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
AUTH = APP / "src" / "auth"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, object]:
    return json.loads(_read(path))


def test_auth_session_files_exist():
    expected = [
        AUTH / "auth-session-types.ts",
        AUTH / "auth-session-context.tsx",
        AUTH / "auth-session-bootstrap.tsx",
        AUTH / "index.ts",
    ]

    assert all(path.is_file() for path in expected)


def test_provider_restores_saved_session_and_validates_me():
    source = _read(AUTH / "auth-session-context.tsx")

    assert "loadUserSession" in source
    assert "api.me<MeResult>()" in source
    assert '"restoring"' in source
    assert '"authenticated"' in source
    assert '"anonymous"' in source


def test_invalid_401_clears_but_transient_error_preserves_token():
    source = _read(AUTH / "auth-session-context.tsx")

    assert "error.status === 401" in source
    assert "await clearUserSession()" in source

    restore_error_block = source.split(
        'setSnapshot({\n        status: "error"',
        maxsplit=1,
    )[1]
    assert (
        "clearUserSession"
        not in restore_error_block.split(
            "const register",
            maxsplit=1,
        )[0]
    )


def test_register_does_not_auto_login():
    source = _read(AUTH / "auth-session-context.tsx")

    register_block = source.split(
        "const register =",
        maxsplit=1,
    )[1].split(
        "const login =", maxsplit=1
    )[0]

    assert "api.register<RegisterResult>" in register_block
    assert "saveUserSession" not in register_block
    assert 'status: "authenticated"' not in register_block


def test_login_persists_session_and_authenticates():
    source = _read(AUTH / "auth-session-context.tsx")

    login_block = source.split(
        "const login =",
        maxsplit=1,
    )[1].split(
        "const logout =", maxsplit=1
    )[0]

    assert "api.login<LoginResult>" in login_block
    assert "saveUserSession(token)" in login_block
    assert 'status: "authenticated"' in login_block


def test_logout_always_clears_local_session():
    source = _read(AUTH / "auth-session-context.tsx")

    logout_block = source.split(
        "const logout =",
        maxsplit=1,
    )[1].split(
        "const refreshMe =", maxsplit=1
    )[0]

    assert "await api.logout()" in logout_block
    assert "finally" in logout_block
    assert "await clearUserSession()" in logout_block
    assert "setSnapshot(anonymousSnapshot())" in logout_block


def test_refresh_me_handles_invalid_session():
    source = _read(AUTH / "auth-session-context.tsx")

    refresh_block = source.split(
        "const refreshMe =",
        maxsplit=1,
    )[1].split(
        "const value =", maxsplit=1
    )[0]

    assert "api.me<MeResult>()" in refresh_block
    assert "isInvalidSession(error)" in refresh_block
    assert "clearUserSession" in refresh_block


def test_root_layout_bootstraps_auth_provider():
    source = _read(APP / "app" / "_layout.tsx")

    assert "<AuthSessionProvider>" in source
    assert "<AuthSessionBootstrap>" in source
    assert "<QueryClientProvider" in source
    assert "<Stack" in source


def test_no_session_or_password_logging():
    for path in AUTH.glob("*.*"):
        source = _read(path)

        assert "console.log" not in source
        assert "console.error" not in source
        assert "API_APLICACAO_TOKEN" not in source


def test_contract_matches_lifecycle_and_boundaries():
    contract = _json(ROOT / "contracts" / "public_app_auth_session_v1.json")

    lifecycle = contract["lifecycle"]

    assert lifecycle["restore_on_app_boot"] is True
    assert lifecycle["invalid_session_401_clears_local_token"] is True
    assert lifecycle["transient_network_failure_clears_local_token"] is False
    assert lifecycle["register_auto_login"] is False
    assert lifecycle["login_persists_user_session"] is True
    assert lifecycle["logout_always_clears_local_session"] is True

    boundaries = contract["boundaries"]
    assert boundaries["final_auth_screens"] is False
    assert boundaries["device_registration"] is False
    assert contract["next_step"] == "public-app-mvp-auth-ui-v1"
