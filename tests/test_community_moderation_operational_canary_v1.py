from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = ROOT / "scripts" / "community_moderation_operational_canary.py"

CONTRACT = ROOT / "contracts" / "community_moderation_operational_canary_v1.json"

LIVE_DB = ROOT / "database" / "user_identity.sqlite3"


def _clone_live(
    target: Path,
) -> None:
    with sqlite3.connect(
        LIVE_DB.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=30,
    ) as source:
        source.execute("PRAGMA query_only = ON")

        with sqlite3.connect(target) as destination:
            source.backup(destination)


def _run(
    tmp_path: Path,
    *,
    token: str | None,
) -> subprocess.CompletedProcess[str]:
    source_db = tmp_path / "source.sqlite3"

    _clone_live(source_db)

    dotenv = tmp_path / ".env"

    if token is None:
        dotenv.write_text(
            "",
            encoding="utf-8",
        )
    else:
        dotenv.write_text(
            ("RADAR_ADMIN_TOKEN=" + token + "\n"),
            encoding="utf-8",
        )

    env = os.environ.copy()

    env["COMMUNITY_MODERATION_RUNTIME_ATIVO"] = "0"

    env["COMMUNITY_MODERATION_RECONCILIATION_STARTUP_ATIVA"] = "0"

    env.pop(
        "RADAR_ADMIN_TOKEN",
        None,
    )

    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ROOT),
            "--database",
            str(source_db),
            "--dotenv",
            str(dotenv),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _payload(
    completed: subprocess.CompletedProcess[str],
) -> dict[str, object]:
    return json.loads(completed.stdout)


def test_8e12b_contract_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E12B-controlled-operational-canary"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "016ee2c"

    assert data["source_stage"]["8E12A"] == "completed"

    assert data["next_step"] == "8E12C-final-operational-closure"


def test_canary_script_compiles():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(SCRIPT),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0


def test_canary_fails_closed_without_admin_token(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token=None,
    )

    assert completed.returncode == 2

    payload = _payload(completed)

    assert payload["ready"] is False

    assert "admin_token_not_configured" in payload["blockers"]


def test_canary_activates_real_runtime_on_temporary_clone(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12b-test-secret",
    )

    assert completed.returncode == 0

    payload = _payload(completed)

    activation = payload["activation"]

    assert activation["active"] is True

    assert activation["schema_activation_authorized"] is True

    assert activation["components_present"] is True

    assert activation["reconciliation_executed"] is False


def test_canary_admin_read_and_wrong_token(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12b-test-secret",
    )

    assert completed.returncode == 0

    admin_http = _payload(completed)["admin_http"]

    assert admin_http["authorized_read_status"] == 200

    assert admin_http["wrong_token_status"] == 401


def test_canary_decision_probe_is_non_writing_404(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12b-test-secret",
    )

    assert completed.returncode == 0

    payload = _payload(completed)

    assert payload["admin_http"]["missing_report_decision_status"] == 404

    assert payload["clone"]["counts_unchanged"] is True


def test_canary_preserves_source_database(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12b-test-secret",
    )

    assert completed.returncode == 0

    safety = _payload(completed)["safety"]

    assert safety["source_database_hash_unchanged"] is True

    assert safety["source_database_counts_unchanged"] is True

    assert safety["source_database_schema_unchanged"] is True

    assert safety["source_database_write"] is False


def test_canary_restores_environment_and_stops_server(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12b-test-secret",
    )

    assert completed.returncode == 0

    payload = _payload(completed)

    assert payload["safety"]["environment_restored"] is True

    assert payload["admin_http"]["server_stopped"] is True

    assert payload["clone"]["temporary_clone_removed"] is True


def test_canary_never_exposes_real_admin_token(
    tmp_path: Path,
):
    secret = "8e12b-super-secret-value"

    completed = _run(
        tmp_path,
        token=secret,
    )

    assert completed.returncode == 0

    assert secret not in completed.stdout
    assert secret not in completed.stderr

    payload = _payload(completed)

    assert payload["admin_token_value_exposed"] is False

    assert payload["safety"]["admin_token_value_exposed"] is False


def test_8e12b_safety_and_tree():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    safety = data["safety"]

    assert safety["live_database_write"] is False

    assert safety["live_schema_write"] is False

    assert safety["persistent_runtime_started"] is False

    assert safety["reconciliation_executed"] is False

    assert safety["real_admin_token_value_exposed"] is False

    assert data["operational_closure_tree"] == {
        "8E12A": "completed",
        "8E12B": "completed",
        "8E12C": "final-operational-closure",
        "hidden_sublevels": False,
    }


def test_canary_contract_declares_windows_safe_teardown():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    safety = data["safety"]

    assert safety["windows_teardown_retry"] is True

    assert safety["temporary_clone_cleanup_attempts"] == 20

    assert safety["temporary_clone_cleanup_delay_seconds"] == 0.1

    assert safety["service_references_released_before_cleanup"] is True

    assert safety["garbage_collection_before_cleanup"] is True

    source = SCRIPT.read_text(encoding="utf-8")

    assert "def _remove_temp_dir_with_retry(" in source

    assert "gc.collect()" in source

    assert "_remove_temp_dir_with_retry(" in source


def test_8e12b_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E12C-final-operational-closure"

    assert data["operational_closure_tree"] == {
        "8E12A": "completed",
        "8E12B": "completed",
        "8E12C": "final-operational-closure",
        "hidden_sublevels": False,
    }

    validation = data["validation"]

    assert validation["real_canary_ready"] is True

    assert validation["real_canary_blockers"] == 0

    assert validation["runtime_activation_scope"] == "temporary-clone-process-only"

    assert validation["schema_activation_authorized"] is True

    assert validation["reconciliation_executed"] is False

    assert validation["admin_http_authorized_read_status"] == 200

    assert validation["admin_http_wrong_token_status"] == 401

    assert validation["admin_http_missing_report_decision_status"] == 404

    assert validation["temporary_clone_removed"] is True

    assert validation["temporary_environment_restored"] is True

    assert validation["live_database_hash_unchanged"] is True

    assert validation["live_database_counts_unchanged"] is True

    assert validation["live_database_schema_unchanged"] is True

    assert validation["admin_token_value_exposed"] is False

    assert validation["persistent_runtime_started"] is False

    assert validation["live_database_write"] is False

    assert validation["live_schema_write"] is False

    assert validation["isolated_8e12b_cases_passed_pre_closure"] == 11

    assert validation["community_moderation_cases_passed_pre_closure"] == 183

    assert validation["public_mobile_cases_passed"] == 61

    assert validation["backend_reporting_cases_passed"] == 70

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_8e12b_cases_after_closure"] == 12

    assert closure["expected_community_moderation_cases_after_closure"] == 184

    assert closure["expected_community_moderation_test_files_after_closure"] == 15

    assert closure["expected_public_mobile_cases_after_closure"] == 61

    assert closure["expected_public_mobile_test_files_after_closure"] == 6

    assert closure["expected_backend_reporting_cases_after_closure"] == 70

    assert closure["8E12A"] == "completed"

    assert closure["8E12B"] == "completed"

    assert closure["8E12C"] == "pending"
