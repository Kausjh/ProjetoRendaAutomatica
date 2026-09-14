from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "user_facing_api_auth_v1.json"
DOC = ROOT / "docs" / "18-user-facing-api-auth-v1.md"
SERVER = ROOT / "services" / "api_aplicacao" / "servidor.py"


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_contract_define_duas_camadas_distintas():
    data = _contract()

    assert data["schema"] == "projeto-renda-automatica.user-facing-api-auth"
    assert data["auth_contract_version"] == 1

    infra = data["layers"]["infrastructure_access"]
    user = data["layers"]["end_user_session"]

    assert infra["header"] == "Authorization"
    assert infra["scheme"] == "Bearer"
    assert infra["credential_source"] == "API_APLICACAO_TOKEN"
    assert infra["must_not_identify_end_user"] is True

    assert user["header"] == "X-User-Session"
    assert user["scheme"] == "opaque"
    assert user["token_prefix"] == "pra_usr_v1_"
    assert user["must_not_replace_infrastructure_guard"] is True


def test_contract_preserva_politica_de_transporte():
    infra = _contract()["layers"]["infrastructure_access"]

    assert infra["optional_on_loopback"] is True
    assert infra["required_outside_loopback"] is True


def test_contract_sessao_falha_fechada():
    semantics = _contract()["session_semantics"]

    assert semantics["session_resolved_server_side"] is True
    assert semantics["inactive_account_fails_closed"] is True
    assert semantics["expired_session_fails_closed"] is True
    assert semantics["revoked_session_fails_closed"] is True


def test_me_nao_aceita_conta_id_do_cliente():
    semantics = _contract()["session_semantics"]

    assert semantics["account_id_never_accepted_from_client_for_me_routes"] is True


def test_register_e_login_nao_exigem_sessao():
    routes = _contract()["route_policy"]["public_user_routes"]

    by_path = {route["path"]: route for route in routes}

    assert by_path["/api/v1/auth/register"]["requires_user_session"] is False
    assert by_path["/api/v1/auth/login"]["requires_user_session"] is False


def test_rotas_autenticadas_exigem_sessao():
    routes = _contract()["route_policy"]["authenticated_user_routes"]

    assert routes
    assert all(route["requires_user_session"] is True for route in routes)


def test_logout_revoga_somente_sessao_atual():
    semantics = _contract()["session_semantics"]

    assert semantics["logout_revokes_only_current_user_session"] is True


def test_contract_nao_usa_cookie():
    security = _contract()["security"]

    assert security["cookies_used_for_user_session"] is False
    assert security["csrf_token_required"] is False


def test_contract_preserva_fronteiras():
    boundaries = _contract()["boundaries"]

    assert boundaries["admin_control_plane_is_separate"] is True
    assert boundaries["infrastructure_bearer_is_not_user_identity"] is True
    assert boundaries["user_session_is_not_infrastructure_bearer"] is True
    assert boundaries["existing_read_only_data_routes_keep_current_auth_policy"] is True
    assert boundaries["no_routes_added_by_this_contract_block"] is True


def test_contract_define_erros_importantes():
    errors = _contract()["error_semantics"]

    assert errors["missing_or_invalid_infrastructure_credential"] == 401
    assert errors["missing_or_invalid_user_session"] == 401
    assert errors["cross_user_resource_access"] == 404
    assert errors["duplicate_email_on_register"] == 409
    assert errors["unsupported_method"] == 405


def test_documentacao_declara_headers_e_fronteiras():
    text = DOC.read_text(encoding="utf-8")

    assert "Authorization: Bearer <API_APLICACAO_TOKEN>" in text
    assert "X-User-Session: pra_usr_v1_<token-opaco>" in text
    assert "nunca identifica o usuário final" in text
    assert "nunca substitui a proteção de infraestrutura" in text
    assert "Rotas sob `/me` nunca aceitam `conta_id`" in text


def test_contrato_auth_e_compativel_com_logout_me_posteriores():
    source = SERVER.read_text(encoding="utf-8")

    implementadas = (
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        'rota == "/api/v1/me"',
    )
    ainda_futuras = (
        "/api/v1/me/preferences",
        "/api/v1/me/watchlist",
    )

    assert all(route in source for route in implementadas)
    assert all(route not in source for route in ainda_futuras)
