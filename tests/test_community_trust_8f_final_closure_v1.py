from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_trust_8f_final_closure_v1.json"

APP_ROOT = ROOT / "apps" / "public-mobile"

API_CLIENT = APP_ROOT / "src" / "api" / "public-api-client.ts"

TRUST_PANEL = APP_ROOT / "src" / "trust" / "trust-panel.tsx"

TRUST_QUERIES = APP_ROOT / "src" / "trust" / "trust-queries.ts"

ACCOUNT = APP_ROOT / "app" / "account.tsx"

SERVER = ROOT / "services" / "api_aplicacao" / "servidor.py"


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_8f6_contract_identity_and_status():
    data = load_contract()

    assert data["stage"] == "8F6-final-closure"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "bc20a85"

    assert data["next_step"] == "phase2-9-social-competitive"


def test_8f6_source_commits_are_frozen():
    data = load_contract()

    assert data["source_commits"] == {
        "8F1": "5775f6c",
        "8F2": "2a55c56",
        "8F3": "7583dae",
        "8F4": "73569b5",
        "8F5": "bc20a85",
    }


def test_8f6_source_contracts_are_completed():
    data = load_contract()

    sources = data["source_contracts"]

    assert set(sources) == {
        "8F1",
        "8F2",
        "8F3",
        "8F4",
        "8F5",
    }

    for entry in sources.values():
        assert entry["status"] == "completed"

        assert Path(entry["path"]).exists()


def test_8f6_tree_is_fully_completed():
    data = load_contract()

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "completed",
        "8F3": "completed",
        "8F4": "completed",
        "8F5": "completed",
        "8F6": "completed",
        "hidden_sublevels": False,
    }


def test_8f6_capabilities_cover_end_to_end_read_experience():
    data = load_contract()

    capabilities = data["capabilities"]

    assert capabilities["trust_public_read_model"] is True

    assert capabilities["authenticated_self_only_profile_api"] is True

    assert capabilities["authenticated_self_only_evidence_history_api"] is True

    assert capabilities["public_app_trust_client"] is True

    assert capabilities["public_app_trust_surface"] is True

    assert capabilities["public_app_surface_location"] == "account"

    assert capabilities["numeric_score_publicly_defined"] is False

    assert capabilities["numeric_score_invented"] is False

    assert capabilities["trust_write_api_added_by_8f"] is False


def test_8f6_authenticated_api_paths_are_preserved():
    data = load_contract()

    api = data["api"]

    assert api["profile_method"] == "GET"

    assert api["profile_path"] == "/api/v1/me/trust"

    assert api["evidence_method"] == "GET"

    assert api["evidence_path"] == "/api/v1/me/trust/evidence"

    assert api["self_only"] is True

    assert api["account_selector"] is False

    assert api["evidence_detail_endpoint"] is False

    assert api["write_endpoint_added"] is False


def test_8f6_privacy_boundary_remains_minimized():
    data = load_contract()

    privacy = data["privacy"]

    for value in privacy.values():
        assert value is False


def test_8f6_public_app_client_methods_are_present():
    source = read(API_CLIENT)

    assert "getCommunityTrustProfile" in source

    assert "listCommunityTrustEvidence" in source

    assert 'path: "/me/trust"' in source

    assert 'path: "/me/trust/evidence"' in source


def test_8f6_public_app_queries_and_panel_are_present():
    queries = read(TRUST_QUERIES)

    panel = read(TRUST_PANEL)

    account = read(ACCOUNT)

    assert "useCommunityTrustProfile" in queries

    assert "useCommunityTrustEvidenceHistory" in queries

    assert "export function TrustPanel" in panel

    assert "<TrustPanel" in account


def test_8f6_ui_has_no_standalone_fetch_or_direct_auth():
    combined = "\n".join(
        (
            read(TRUST_PANEL),
            read(ACCOUNT),
        )
    )

    assert (
        re.search(
            r"(?<![A-Za-z0-9_])fetch\s*\(",
            combined,
        )
        is None
    )

    forbidden = (
        "X-User-Session",
        "Authorization",
        "Bearer ",
        "API_APLICACAO_TOKEN",
        "infrastructureToken",
    )

    for value in forbidden:
        assert value not in combined


def test_8f6_server_routes_remain_present():
    source = read(SERVER)

    assert "/api/v1/me/trust" in source

    assert "/api/v1/me/trust/evidence" in source


def test_8f6_has_no_new_product_mutation_boundary():
    data = load_contract()

    boundaries = data["boundaries"]

    assert boundaries["new_functionality_in_8f6"] is False

    assert boundaries["product_code_changed_in_8f6"] is False

    assert boundaries["server_changed_in_8f6"] is False

    assert boundaries["public_app_changed_in_8f6"] is False

    assert boundaries["navigation_changed_in_8f6"] is False

    assert boundaries["database_changed_in_8f6"] is False

    assert boundaries["database_write_in_8f6"] is False

    assert boundaries["trust_write_in_8f6"] is False

    assert boundaries["runtime_restart_in_8f6"] is False


def test_8f6_aegis_security_closure():
    data = load_contract()

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["security_first_class"] is True

    assert security["secure_by_design"] is True

    assert security["zero_trust"] is True

    assert security["least_privilege"] is True

    assert security["defense_in_depth"] is True

    assert security["assume_breach"] is True

    assert security["data_minimization"] is True

    assert security["fail_closed"] is True

    assert security["source_contracts_completed"] is True

    assert security["self_only_boundary_preserved"] is True

    assert security["query_level_minimization_preserved"] is True

    assert security["strict_read_only_trust_reader_preserved"] is True

    assert security["bounded_pagination_preserved"] is True

    assert security["no_account_selector"] is True

    assert security["no_internal_identifier_exposure"] is True

    assert security["no_internal_evidence_context_exposure"] is True

    assert security["no_numeric_score_invention"] is True

    assert security["no_write_path_added"] is True

    assert security["no_direct_ui_transport"] is True

    assert security["no_direct_ui_auth_handling"] is True

    assert security["no_new_server_attack_surface_in_8f6"] is True

    assert security["existing_security_silently_weakened"] is False

    assert security["security_regression_detected"] is False


def test_8f6_macro_roadmap_advances_to_item_9():
    data = load_contract()

    roadmap = data["macro_roadmap"]

    assert roadmap["phase_2_item_8"] == "Community Reputation & Trust"

    assert roadmap["phase_2_item_8_status"] == "completed"

    assert roadmap["next_item"] == "9 Social/Competitive"

    assert data["next_step"] == "phase2-9-social-competitive"
