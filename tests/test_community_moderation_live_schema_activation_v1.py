from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_live_schema_activation_v1.json"

RUNTIME_CONTRACT = ROOT / "contracts" / "community_moderation_runtime_v1.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_8e7_contract_completed():
    data = _contract()

    assert data["stage"] == "8E7-moderation-live-schema-activation"

    assert data["status"] == "completed"

    assert {key: value["status"] for key, value in data["sub_stages"].items()} == {
        "8E7A": "completed",
        "8E7B": "completed",
        "8E7C": "completed",
    }


def test_8e7_recovery_point():
    recovery = _contract()["recovery_point"]

    assert recovery["backup_sha256"] == (
        "74f8bb85b28738d535ad73622f394143" "dd3c671703469472beb18cc852ad1526"
    )

    assert recovery["integrity_check"] == "ok"
    assert recovery["foreign_key_errors"] == 0
    assert recovery["moderation_tables"] == 0
    assert recovery["trust_evidence"] == 2
    assert recovery["trust_profiles"] == 1


def test_8e7_live_schema_state():
    activation = _contract()["activation"]

    assert activation["rehearsal_before_live"] is True

    assert activation["live_schema_write"] is True

    assert activation["live_schema_matches_rehearsal"] is True

    assert activation["moderation_tables"] == [
        "community_moderation_decisions",
        "community_moderation_reports",
    ]

    assert activation["moderation_report_rows"] == 0

    assert activation["moderation_decision_rows"] == 0

    assert activation["integrity_check"] == "ok"
    assert activation["foreign_key_errors"] == 0
    assert activation["trust_evidence"] == 2
    assert activation["trust_profiles"] == 1


def test_8e7_rollback_proof():
    proof = _contract()["rollback_proof"]

    assert proof["simulated_restore_from_backup"] is True

    assert proof["restored_schema_matches_pre_activation"] is True

    assert proof["restored_moderation_tables"] == 0

    assert proof["forward_replay_after_restore"] is True

    assert proof["forward_replay_matches_live_schema"] is True

    assert proof["live_restore_performed"] is False

    assert proof["windows_temp_cleanup_is_correctness_boundary"] is False


def test_8e7_boundaries():
    boundaries = _contract()["boundaries"]

    assert boundaries["live_database_write_by_8e7c"] is False

    assert boundaries["moderation_rows_created"] is False

    assert boundaries["trust_rows_changed"] is False

    assert boundaries["main_runtime_activation"] is False

    assert boundaries["trust_bridge_live_activation"] is False

    assert boundaries["reconciliation_live_execution"] is False


def test_runtime_contract_advances_to_8e8():
    data = json.loads(RUNTIME_CONTRACT.read_text(encoding="utf-8"))

    assert data["live_schema_activation"]["status"] == "completed"

    assert data["live_schema_activation"]["moderation_tables_active"] is True

    assert data["live_schema_activation"]["moderation_rows"] == 0

    assert data["live_schema_activation"]["runtime_activation"] is False

    assert data["next_step"] == "8E8-controlled-runtime-wiring"
