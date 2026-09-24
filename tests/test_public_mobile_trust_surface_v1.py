from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

APP = ROOT / "apps" / "public-mobile"

TRUST = APP / "src" / "trust"

PANEL = TRUST / "trust-panel.tsx"
INDEX = TRUST / "index.ts"
ACCOUNT = APP / "app" / "account.tsx"

CONTRACT = ROOT / "contracts" / "community_trust_public_app_surface_v1.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_8f5_contract_identity_tree_and_source():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8F5-public-app-trust-surface"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "73569b5"

    assert data["source_stage"]["8F4"] == "completed"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "completed",
        "8F3": "completed",
        "8F4": "completed",
        "8F5": "completed",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    assert data["next_step"] == "8F6-final-closure"


def test_trust_panel_exists_and_is_exported():
    assert PANEL.exists()

    source = read(INDEX)

    assert 'export * from "@/src/trust/trust-panel";' in source


def test_account_integrates_trust_panel_after_missions():
    source = read(ACCOUNT)

    assert 'import { TrustPanel } from "@/src/trust";' in source

    assert "{authenticated ? <TrustPanel /> : null}" in source

    assert source.index("<MissionsPanel") < source.index("<TrustPanel")


def test_trust_panel_uses_8f4_read_hooks():
    source = read(PANEL)

    assert "useCommunityTrustProfile" in source

    assert "useCommunityTrustEvidenceHistory" in source

    assert "useCommunityTrustEvidenceHistory(" in source

    assert "20," in source

    assert "0," in source


def test_trust_panel_displays_public_profile_counts():
    source = read(PANEL)

    expected = (
        "profileData.evidenceTotal",
        "profileData.positiveTotal",
        "profileData.neutralTotal",
        "profileData.negativeTotal",
        "profileData.modelVersion",
    )

    for value in expected:
        assert value in source


def test_trust_panel_does_not_invent_numeric_score():
    source = read(PANEL)

    assert "Nao usamos uma nota numerica." in source

    assert "sem score numerico" in source

    assert "numericScore" not in source


def test_trust_panel_displays_minimized_history():
    source = read(PANEL)

    expected = (
        "item.type",
        "item.classification",
        "item.occurredAt",
    )

    for value in expected:
        assert value in source

    forbidden = (
        "item.accountId",
        "item.evidenceId",
        "item.idempotencyKey",
        "item.origin",
        "item.originId",
        "item.reason",
        "item.policyVersion",
        "item.rawMetadata",
        "item.moderatorActor",
    )

    for value in forbidden:
        assert value not in source


def test_trust_panel_has_public_classification_labels():
    source = read(PANEL)

    assert 'value === "positive"' in source

    assert 'value === "negative"' in source

    assert '"Positiva"' in source

    assert '"Negativa"' in source

    assert '"Neutra"' in source


def test_trust_panel_has_loading_state():
    source = read(PANEL)

    assert "profile.isPending" in source

    assert "history.isPending" in source

    assert "ActivityIndicator" in source

    assert "Carregando sinais de confianca" in source


def test_trust_panel_has_error_retry_and_manual_refresh():
    source = read(PANEL)

    assert "profile.isError" in source

    assert "history.isError" in source

    assert "profile.refetch()" in source

    assert "history.refetch()" in source

    assert "Tentar novamente" in source

    assert "Atualizar reputacao comunitaria" in source


def test_trust_panel_has_empty_state():
    source = read(PANEL)

    assert "historyData.items.length === 0" in source

    assert "Nenhuma evidencia ainda" in source


def test_trust_ui_does_not_handle_transport_identity_or_write():
    combined = "\n".join(
        (
            read(PANEL),
            read(ACCOUNT),
        )
    )

    forbidden = (
        "X-User-Session",
        "Authorization",
        "Bearer ",
        "API_APLICACAO_TOKEN",
        "infrastructureToken",
        "conta_id",
        "axios",
        "POST",
        "PATCH",
        "PUT",
        "DELETE",
    )

    for value in forbidden:
        assert value not in combined

    assert (
        re.search(
            r"(?<![A-Za-z0-9_])fetch\s*\(",
            combined,
        )
        is None
    )


def test_8f5_contract_scope_privacy_and_aegis():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    architecture = data["architecture"]

    assert architecture["panel_component"] == "TrustPanel"

    assert architecture["integrated_surface"] == "account"

    assert architecture["dedicated_route"] is False

    assert architecture["bottom_nav_entry"] is False

    assert architecture["layout_route_change"] is False

    ui = data["ui"]

    assert ui["numeric_score_visible"] is False

    assert ui["numeric_score_invented"] is False

    assert ui["history_visible"] is True

    assert ui["manual_refresh"] is True

    assert ui["loading_state"] is True

    assert ui["error_retry_state"] is True

    assert ui["empty_state"] is True

    privacy = data["privacy"]

    for value in privacy.values():
        assert value is False

    boundaries = data["boundaries"]

    assert boundaries["public_app_ui_changed"] is True

    assert boundaries["account_screen_changed"] is True

    assert boundaries["new_route"] is False

    assert boundaries["bottom_nav_changed"] is False

    assert boundaries["server_changed"] is False

    assert boundaries["server_endpoint_added"] is False

    assert boundaries["database_write"] is False

    assert boundaries["trust_write"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["existing_trust_client_reused"] is True

    assert security["ui_handles_transport_directly"] is False

    assert security["ui_handles_auth_headers_directly"] is False

    assert security["ui_handles_user_session_directly"] is False

    assert security["account_selector_added"] is False

    assert security["internal_identifiers_rendered"] is False

    assert security["internal_evidence_context_rendered"] is False

    assert security["numeric_score_invented"] is False

    assert security["write_control_added"] is False

    assert security["new_server_attack_surface"] is False

    assert security["existing_security_silently_weakened"] is False


def test_8f5_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8F6-final-closure"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "completed",
        "8F3": "completed",
        "8F4": "completed",
        "8F5": "completed",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    validation = data["validation"]

    assert validation["initial_fetch_test_false_positive"] is True

    assert validation["functional_failure_detected"] is False

    assert validation["implementation_reapplied_after_failure"] is False

    assert validation["product_files_modified_by_recovery"] is False

    assert validation["standalone_fetch_security_check_preserved"] is True

    assert validation["react_query_refetch_permitted"] is True

    assert validation["pre_commit_passed"] is True

    assert validation["public_app_typecheck_passed"] is True

    assert validation["isolated_8f5_cases_passed_pre_closure"] == 13

    assert validation["public_mobile_legacy_test_files"] == 6

    assert validation["public_mobile_legacy_cases_passed"] == 61

    assert validation["public_mobile_combined_test_files"] == 8

    assert validation["public_mobile_combined_cases_passed_pre_closure"] == 88

    assert validation["account_surface_regression_cases_passed_pre_closure"] == 75

    assert validation["community_trust_backend_test_files"] == 11

    assert validation["community_trust_backend_cases_passed"] == 149

    assert validation["live_database_sha256_unchanged"] is True

    assert validation["database_write"] is False

    assert validation["trust_write"] is False

    assert validation["runtime_main_still_running"] is True

    assert validation["health_monitor_still_enabled"] is True

    assert validation["runtime_restart"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["validation_completed"] is True

    assert security["existing_trust_client_reuse_validated"] is True

    assert security["ui_transport_encapsulation_validated"] is True

    assert security["ui_auth_header_non_handling_validated"] is True

    assert security["ui_user_session_non_handling_validated"] is True

    assert security["account_selector_absence_validated"] is True

    assert security["internal_identifier_non_rendering_validated"] is True

    assert security["internal_evidence_context_non_rendering_validated"] is True

    assert security["numeric_score_non_invention_validated"] is True

    assert security["standalone_fetch_absence_validated"] is True

    assert security["write_control_absence_validated"] is True

    assert security["runtime_state_preserved"] is True

    assert security["live_database_state_preserved"] is True

    assert security["security_regression_detected"] is False

    assert security["existing_security_silently_weakened"] is False

    closure = data["closure"]

    assert closure["expected_isolated_8f5_cases_after_closure"] == 14

    assert closure["expected_public_mobile_legacy_cases_after_closure"] == 61

    assert closure["expected_public_mobile_combined_cases_after_closure"] == 89

    assert closure["expected_account_surface_regression_cases_after_closure"] == 76

    assert closure["expected_community_trust_backend_cases_after_closure"] == 149

    assert closure["8F5"] == "completed"

    assert closure["8F6"] == "pending"
