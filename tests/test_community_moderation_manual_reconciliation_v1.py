from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_manual_reconciliation_v1.json"

BRIDGE_CONTRACT = ROOT / "contracts" / "community_moderation_live_bridge_activation_v1.json"

MAIN_RUNTIME = ROOT / "runtime.py"

RECONCILIATION_SOURCE = ROOT / "services" / "community_moderation_trust_reconciliation.py"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_8e8c_contract_boundary():
    data = _contract()

    assert data["stage"] == "8E8C-controlled-manual-reconciliation"

    assert data["status"] == "completed"

    assert data["execution"]["real_live_database_used"] is True

    assert data["execution"]["full_runtime_restart"] is False


def test_8e8b_is_completed_before_8e8c():
    data = json.loads(BRIDGE_CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E8C-controlled-manual-reconciliation"


def test_8e8c_manual_not_automatic():
    execution = _contract()["execution"]

    assert execution["reconciliation_startup_flag_enabled"] is False

    assert execution["automatic_reconciliation_executed"] is False

    assert execution["manual_reconciliation_executed"] is True

    assert execution["authoritative_candidates_before"] == 0


def test_8e8c_first_manual_run():
    result = _contract()["first_run"]

    assert result == {
        "offset_inicial": 0,
        "proximo_offset": 0,
        "examinadas": 0,
        "evidencias_criadas": 0,
        "evidencias_existentes": 0,
        "falhas": 0,
    }


def test_8e8c_second_manual_run_is_empty_idempotent():
    data = _contract()

    assert data["second_run"] == data["first_run"]

    assert data["idempotency"]["second_manual_run_executed"] is True

    assert data["idempotency"]["empty_rerun_idempotent"] is True

    assert data["idempotency"]["duplicate_negative_created"] is False


def test_8e8c_live_state_unchanged():
    state = _contract()["live_state"]

    assert state["moderation_report_rows"] == 0

    assert state["moderation_decision_rows"] == 0

    assert state["trust_evidence_total"] == 2

    assert state["trust_profile_total"] == 1

    assert state["moderation_rows_created"] == 0

    assert state["trust_evidence_created"] == 0

    assert state["integrity_check"] == "ok"

    assert state["foreign_key_errors"] == 0


def test_8e8c_preserves_automatic_startup_boundary():
    boundaries = _contract()["boundaries"]

    assert boundaries["automatic_startup_reconciliation"] is False

    assert boundaries["persistent_reconciliation_flag_changed"] is False

    runtime_source = MAIN_RUNTIME.read_text(encoding="utf-8")

    assert "executar_reconciliation=False" in runtime_source


def test_reconciliation_service_supports_manual_pagination():
    source = RECONCILIATION_SOURCE.read_text(encoding="utf-8")

    assert "def reconciliar(" in source

    assert "limite: int = 100" in source

    assert "offset: int = 0" in source

    assert "evidencias_criadas" in source

    assert "evidencias_existentes" in source

    assert "falhas" in source


def test_8e8c_closure_and_stage_8e8_completion():
    data = _contract()

    assert data["status"] == "completed"

    assert data["next_step"] == "8E9A-admin-moderation-read-api"

    validation = data["validation"]

    assert validation["baseline"] == "921480c"

    assert validation["isolated_tests_passed_pre_closure"] == 8

    assert validation["stage_8e_tests_passed_pre_closure"] == 111

    assert validation["trust_moderation_tests_passed_pre_closure"] == 160

    assert validation["automatic_reconciliation_executed"] is False

    assert validation["manual_reconciliation_executed"] is True

    assert validation["authoritative_candidates_before"] == 0

    assert validation["first_run_examinadas"] == 0

    assert validation["first_run_evidencias_criadas"] == 0

    assert validation["first_run_falhas"] == 0

    assert validation["second_run_examinadas"] == 0

    assert validation["second_run_evidencias_criadas"] == 0

    assert validation["second_run_falhas"] == 0

    assert validation["empty_rerun_idempotent"] is True

    assert validation["runtime_flag_restored"] is True

    assert validation["reconciliation_flag_restored"] is True

    assert validation["trust_evidence_created"] == 0

    assert validation["moderation_rows_created"] == 0

    assert validation["live_domain_state_unchanged"] is True

    stage = data["stage_8e8"]

    assert stage["status"] == "completed"

    assert stage["sub_stages"] == {
        "8E8A": "completed",
        "8E8B": "completed",
        "8E8C": "completed",
    }

    assert stage["automatic_reconciliation_enabled"] is False

    assert stage["persistent_runtime_activation"] is False
