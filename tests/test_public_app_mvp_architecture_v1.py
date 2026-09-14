from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "public_app_mvp_architecture_v1.json"
DOC = ROOT / "docs" / "25-public-app-mvp-architecture.md"
README = ROOT / "README.md"
STACK = ROOT / "STACK.md"


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_contract_identifica_public_app_android_expo():
    data = _contract()

    assert data["schema"] == ("projeto-renda-automatica.public-app-mvp-architecture")
    assert data["architecture_version"] == 1
    assert data["phase"] == 2
    assert data["stage"] == 2

    platform = data["platform"]
    assert platform["primary"] == "android"
    assert platform["framework"] == "react-native"
    assert platform["toolchain"] == "expo"
    assert platform["language"] == "typescript"
    assert platform["planned_source_root"] == "apps/public-mobile"


def test_transport_preserva_fronteira_publico_admin():
    data = _contract()
    api = data["api"]

    assert api["application_backend_port"] == 8766
    assert api["tailscale_forward_port"] == 18767
    assert api["admin_port_8765_allowed"] is False

    boundaries = data["repository_boundaries"]
    assert boundaries["public_user_app_source_allowed"] is True
    assert boundaries["private_admin_android_app_allowed"] is False
    assert boundaries["admin_credentials_allowed"] is False
    assert boundaries["admin_control_plane_usage_allowed"] is False


def test_segredos_nao_sao_embutidos():
    policy = _contract()["secret_policy"]

    assert policy["api_application_token_bundled"] is False
    assert policy["api_application_token_committed"] is False
    assert policy["api_application_token_hardcoded"] is False
    assert policy["plaintext_secret_in_repository"] is False
    assert policy["user_session_persisted_in_secure_store"] is True


def test_mvp_tem_rotas_necessarias_sem_features_posteriores():
    data = _contract()
    screens = {item["id"]: item for item in data["mvp_screens"]}

    assert set(screens) == {
        "auth",
        "offers",
        "alerts",
        "watchlist",
        "account",
    }

    ui = data["ui"]
    assert ui["personalized_feed_in_mvp"] is False
    assert ui["push_notifications_in_mvp"] is False
    assert ui["device_registration_in_mvp"] is False


def test_transporte_e_abstraido_da_ui():
    transport = _contract()["transport_abstraction"]

    assert transport["required"] is True
    assert transport["current_profile"] == ("tailscale-http-trusted-tunnel")
    assert transport["future_profile"] == "public-https-gateway"
    assert transport["ui_must_not_depend_on_transport_profile"] is True


def test_documentacao_registra_alpha_e_nao_distribuicao_publica():
    text = DOC.read_text(encoding="utf-8")

    assert "internal alpha over tailnet" in text
    assert "8765" in text
    assert "18767" in text
    assert "Expo Secure Store" in text
    assert "public-https-gateway" in text


def test_readme_e_stack_refletem_decisao():
    readme = README.read_text(encoding="utf-8")
    stack = STACK.read_text(encoding="utf-8")

    assert "<!-- fase2-public-app-mvp-architecture-v1:start -->" in readme
    assert "React Native + Expo + TypeScript" in readme
    assert (
        "| App público | Fase 2 — arquitetura MVP definida; " "implementação pendente |"
    ) in stack
