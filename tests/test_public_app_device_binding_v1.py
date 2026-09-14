from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
DEVICE = APP / "src" / "device"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, object]:
    return json.loads(_read(path))


def test_device_binding_files_exist():
    expected = [
        DEVICE / "device-installation.ts",
        DEVICE / "device-push-token.ts",
        DEVICE / "device-registration-service.ts",
        DEVICE / "device-registration-bootstrap.tsx",
        DEVICE / "index.ts",
    ]
    assert all(path.is_file() for path in expected)


def test_dependencies_and_notifications_plugin_are_declared():
    package = _json(APP / "package.json")
    dependencies = package["dependencies"]

    assert "expo-notifications" in dependencies
    assert "expo-crypto" in dependencies

    app_config = _json(APP / "app.json")
    assert "expo-notifications" in app_config["expo"]["plugins"]


def test_installation_id_is_random_stable_and_not_cleared_on_logout():
    source = _read(DEVICE / "device-installation.ts")

    assert 'const INSTALLATION_ID_KEY = "pra_public_installation_id_v1"' in source
    assert "Crypto.randomUUID()" in source
    assert "SecureStore.getItemAsync(INSTALLATION_ID_KEY)" in source
    assert "SecureStore.setItemAsync(INSTALLATION_ID_KEY, generated)" in source
    assert "deleteItemAsync" not in source


def test_push_token_flow_is_expo_go_safe_and_requires_project_id():
    source = _read(DEVICE / "device-push-token.ts")

    assert "Constants.expoGoConfig" in source
    assert '"expo-go-remote-push-unavailable"' in source
    assert "Constants.expoConfig?.extra?.eas?.projectId" in source
    assert "Constants.easConfig?.projectId" in source
    assert "Notifications.setNotificationChannelAsync" in source
    assert "Notifications.getPermissionsAsync()" in source
    assert "Notifications.requestPermissionsAsync()" in source
    assert "Notifications.getExpoPushTokenAsync" in source

    assert source.index("Constants.expoGoConfig") < source.index(
        "Notifications.getExpoPushTokenAsync"
    )


def test_public_api_client_covers_device_routes_with_user_session():
    source = _read(APP / "src" / "api" / "public-api-client.ts")

    assert 'path: "/me/devices"' in source
    assert "`/me/devices/${encodeURIComponent(installationId)}`" in source
    assert "putDevice" in source
    assert "deleteDevice" in source

    device_tail = source.split("listDevices", maxsplit=1)[1]
    assert device_tail.count("requiresUserSession: true") >= 3


def test_authenticated_bootstrap_registers_without_exposing_token():
    bootstrap = _read(DEVICE / "device-registration-bootstrap.tsx")
    service = _read(DEVICE / "device-registration-service.ts")

    assert 'snapshot.status !== "authenticated"' in bootstrap
    assert "bindCurrentDeviceRegistration()" in bootstrap

    assert "ensureInstallationId()" in service
    assert "acquireExpoPushToken()" in service
    assert "api.putDevice(installationId" in service
    assert "push_token: tokenResult.token" in service

    combined = "\n".join(_read(path) for path in DEVICE.glob("*.*"))
    assert "console.log" not in combined
    assert "console.error" not in combined
    assert "exp.host/--/api/v2/push/send" not in combined


def test_explicit_logout_revokes_device_before_server_logout_but_never_blocks_local_logout():
    source = _read(APP / "src" / "auth" / "auth-session-context.tsx")
    logout = source.split("const logout =", maxsplit=1)[1].split(
        "const refreshMe =",
        maxsplit=1,
    )[0]

    assert "await revokeCurrentDeviceRegistration()" in logout
    assert "await api.logout()" in logout
    assert logout.index("await revokeCurrentDeviceRegistration()") < logout.index(
        "await api.logout()"
    )
    assert "await clearUserSession()" in logout
    assert "finally" in logout


def test_root_layout_mounts_device_bootstrap_inside_auth_provider():
    source = _read(APP / "app" / "_layout.tsx")

    assert "DeviceRegistrationBootstrap" in source
    assert "<AuthSessionProvider>" in source
    assert "<AuthSessionBootstrap>" in source
    assert "<DeviceRegistrationBootstrap>" in source


def test_contract_keeps_dispatcher_out_and_marks_real_token_validation_pending():
    contract = _json(ROOT / "contracts" / "public_app_device_binding_v1.json")

    assert contract["device_binding_version"] == 1
    assert contract["backend"]["client_sends_account_id"] is False
    assert contract["installation_identity"]["generated_once"] is True
    assert contract["push_token"]["token_logged"] is False
    assert contract["runtime"]["expo_go_remote_push_supported"] is False
    assert contract["runtime"]["development_build_required_for_remote_push"] is True
    assert contract["runtime"]["real_push_token_validation_completed"] is False
    assert contract["delivery"]["push_delivery_implemented"] is False
    assert contract["delivery"]["dispatcher_implemented"] is False
    assert (
        contract["next_step"] == "development-build-push-credentials-and-real-token-validation-v1"
    )
