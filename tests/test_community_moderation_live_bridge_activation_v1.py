from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_live_bridge_activation_v1.json"

MAIN_WIRING_CONTRACT = ROOT / "contracts" / "community_moderation_runtime_main_wiring_v1.json"

RUNTIME_SOURCE = ROOT / "services" / "community_moderation_runtime.py"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_8e8b_contract_boundary():
    data = _contract()

    assert data["stage"] == "8E8B-controlled-live-bridge-activation"

    assert data["status"] == "completed"

    assert data["activation"]["real_live_database_used"] is True

    assert data["activation"]["persistent_runtime_flag_changed"] is False


def test_8e8b_failed_attempt_was_safe():
    failed = _contract()["failed_attempt"]

    assert failed["imports_completed"] is False

    assert failed["live_domain_state_changed"] is False

    assert failed["git_state_changed"] is False


def test_8e8b_real_components_composed():
    activation = _contract()["activation"]

    assert activation["components_composed"] is True

    assert activation["moderation_service_active"] is True

    assert activation["trust_bridge_active"] is True


def test_8e8b_bridge_identity_wiring():
    activation = _contract()["activation"]

    assert activation["trust_bridge_injected_in_moderation_service"] is True

    assert activation["trust_bridge_shared_with_reconciliation_service"] is True

    assert activation["trust_repository_injected"] is True

    assert activation["discovery_repository_injected"] is True

    assert activation["moderation_repository_shared_with_reconciliation_service"] is True


def test_8e8b_reconciliation_was_blocked():
    reconciliation = _contract()["reconciliation"]

    assert reconciliation["environment_flag_forced_on_during_probe"] is True

    assert reconciliation["explicit_override"] is False

    assert reconciliation["executed"] is False

    assert reconciliation["explicit_override_prevailed_over_environment"] is True


def test_8e8b_live_domain_state_unchanged():
    state = _contract()["live_state"]

    assert state["schema_unchanged"] is True

    assert state["moderation_report_rows"] == 0

    assert state["moderation_decision_rows"] == 0

    assert state["trust_evidence_total"] == 2

    assert state["trust_profile_total"] == 1

    assert state["moderation_rows_created"] == 0

    assert state["trust_rows_created"] == 0

    assert state["integrity_check"] == "ok"

    assert state["foreign_key_errors"] == 0


def test_8e8b_preserves_product_boundaries():
    boundaries = _contract()["boundaries"]

    assert boundaries["admin_http_integration"] is False

    assert boundaries["public_report_api_integration"] is False

    assert boundaries["moderation_decision_canary"] is False

    assert boundaries["confirmed_abuse_canary"] is False

    assert boundaries["automatic_reconciliation"] is False

    assert boundaries["runtime_configuration_persisted"] is False


def test_8e8b_matches_8e8a_safe_main_wiring():
    main = json.loads(MAIN_WIRING_CONTRACT.read_text(encoding="utf-8"))

    assert main["status"] == "completed"

    assert main["next_step"] == "8E8B-controlled-live-bridge-activation"

    assert main["reconciliation"]["explicit_override_in_main"] is True

    assert main["reconciliation"]["explicit_override_value"] is False

    source = RUNTIME_SOURCE.read_text(encoding="utf-8")

    assert "trust_bridge=trust_bridge" in source

    assert "executar_reconciliation" in source


def test_8e8b_closure_metadata():
    data = _contract()

    assert data["status"] == "completed"

    assert data["next_step"] == "8E8C-controlled-manual-reconciliation"

    validation = data["validation"]

    assert validation["baseline"] == "c61a63f"

    assert validation["initial_failed_attempt_safe"] is True

    assert validation["project_root_sys_path_fix_validated"] is True

    assert validation["isolated_tests_passed_pre_closure"] == 8

    assert validation["stage_8e_tests_passed_pre_closure"] == 102

    assert validation["trust_moderation_tests_passed_pre_closure"] == 151

    assert validation["real_live_database_used"] is True

    assert validation["full_runtime_restart"] is False

    assert validation["persistent_runtime_flag_changed"] is False

    assert validation["ephemeral_authority_used"] is True

    assert validation["authority_token_persisted"] is False

    assert validation["components_composed"] is True

    assert validation["trust_bridge_injected_in_moderation_service"] is True

    assert validation["trust_bridge_shared_with_reconciliation_service"] is True

    assert validation["reconciliation_explicit_override_value"] is False

    assert validation["reconciliation_executed"] is False

    assert validation["runtime_flag_restored"] is True

    assert validation["reconciliation_flag_restored"] is True

    assert validation["live_schema_unchanged"] is True

    assert validation["moderation_rows_created"] == 0

    assert validation["trust_rows_created"] == 0

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0
