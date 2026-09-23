from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = ROOT / "scripts" / "community_moderation_final_operational_closure.py"

CONTRACT = ROOT / "contracts" / "community_moderation_final_operational_closure_v1.json"

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
    token: str,
) -> subprocess.CompletedProcess[str]:
    database = tmp_path / "source.sqlite3"

    _clone_live(database)

    dotenv = tmp_path / ".env"

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
            str(database),
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


def test_8e12c_contract_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E12C-final-operational-closure"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "75c2a5f"

    assert data["source_stages"] == {
        "8E12A": "completed",
        "8E12B": "completed",
    }

    assert data["source_commits"] == {
        "8E12A": "016ee2c",
        "8E12B": "75c2a5f",
    }

    assert data["next_step"] == "8F-trust-read-api-public-app-surface"


def test_final_operational_closure_script_compiles():
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


def test_final_operational_closure_ready(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12c-test-secret",
    )

    assert completed.returncode == 0

    payload = _payload(completed)

    assert payload["ready"] is True
    assert payload["blockers"] == []


def test_final_operational_closure_reexecutes_preflight_and_canary(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12c-test-secret",
    )

    assert completed.returncode == 0

    payload = _payload(completed)

    assert payload["preflight"]["ready"] is True

    assert payload["preflight"]["blockers"] == []

    assert payload["canary"]["executed"] is True

    assert payload["canary"]["ready"] is True

    assert payload["canary"]["blockers"] == []

    assert payload["canary"]["runtime_activation_scope"] == "temporary-clone-process-only"


def test_final_operational_closure_canary_boundaries(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12c-test-secret",
    )

    assert completed.returncode == 0

    canary = _payload(completed)["canary"]

    assert canary["schema_activation_authorized"] is True

    assert canary["reconciliation_executed"] is False

    assert canary["admin_read_status"] == 200

    assert canary["wrong_token_status"] == 401

    assert canary["missing_report_decision_status"] == 404

    assert canary["temporary_clone_removed"] is True

    assert canary["environment_restored"] is True


def test_final_operational_closure_preserves_source(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12c-test-secret",
    )

    assert completed.returncode == 0

    payload = _payload(completed)

    safety = payload["safety"]

    assert safety["live_database_hash_unchanged"] is True

    assert safety["live_database_counts_unchanged"] is True

    assert safety["live_database_schema_unchanged"] is True

    assert safety["live_database_write"] is False

    assert safety["live_schema_write"] is False

    assert safety["persistent_runtime_started"] is False

    assert safety["reconciliation_executed"] is False


def test_final_operational_closure_does_not_expose_token(
    tmp_path: Path,
):
    secret = "8e12c-super-secret-value"

    completed = _run(
        tmp_path,
        token=secret,
    )

    assert completed.returncode == 0

    assert secret not in completed.stdout
    assert secret not in completed.stderr

    payload = _payload(completed)

    assert payload["canary"]["admin_token_value_exposed"] is False

    assert payload["safety"]["admin_token_value_exposed"] is False


def test_final_operational_closure_live_shape(
    tmp_path: Path,
):
    completed = _run(
        tmp_path,
        token="8e12c-test-secret",
    )

    assert completed.returncode == 0

    payload = _payload(completed)

    before = payload["live_before"]

    after = payload["live_after"]

    assert before["sha256"] == after["sha256"]

    assert before["counts"] == after["counts"]

    assert before["schema_version"] == after["schema_version"]

    assert after["integrity_check"] == "ok"

    assert after["foreign_key_errors"] == 0


def test_8e12c_tree_and_safety_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["operational_closure_tree"] == {
        "8E12A": "completed",
        "8E12B": "completed",
        "8E12C": "completed",
        "hidden_sublevels": False,
    }

    assert data["stage_completion"]["completes_8E12_operational_closure"] is True

    assert data["stage_completion"]["completes_8E_moderation_reporting_operational_closure"] is True

    security = data["security"]

    assert security["admin_token_value_exposed"] is False

    assert security["persistent_runtime_started"] is False

    assert security["live_database_write"] is False

    assert security["live_schema_write"] is False


def test_8e12c_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8F-trust-read-api-public-app-surface"

    assert data["operational_closure_tree"] == {
        "8E12A": "completed",
        "8E12B": "completed",
        "8E12C": "completed",
        "hidden_sublevels": False,
    }

    validation = data["validation"]

    assert validation["real_final_operational_closure_ready"] is True

    assert validation["real_final_operational_closure_blockers"] == 0

    assert validation["standby_preflight_ready"] is True

    assert validation["controlled_canary_ready"] is True

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

    assert validation["live_integrity_check"] == "ok"

    assert validation["live_foreign_key_errors"] == 0

    assert validation["live_moderation_report_rows"] == 0

    assert validation["live_moderation_decision_rows"] == 0

    assert validation["live_trust_evidence_total"] == 2

    assert validation["live_trust_profile_total"] == 1

    assert validation["admin_token_value_exposed"] is False

    assert validation["persistent_runtime_started"] is False

    assert validation["live_database_write"] is False

    assert validation["live_schema_write"] is False

    assert validation["isolated_8e12c_cases_passed_pre_closure"] == 9

    assert validation["community_moderation_cases_passed_pre_closure"] == 193

    assert validation["public_mobile_cases_passed"] == 61

    assert validation["backend_reporting_cases_passed"] == 70

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["security_first_class"] is True

    assert security["secure_by_design"] is True

    assert security["zero_trust"] is True

    assert security["least_privilege"] is True

    assert security["defense_in_depth"] is True

    assert security["assume_breach"] is True

    assert security["existing_security_silently_weakened"] is False

    assert security["new_secret"] is False

    assert security["secret_value_exposed"] is False

    assert security["new_live_write_path"] is False

    assert security["persistent_attack_surface_increase"] is False

    assert security["security_regression_detected"] is False

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_8e12c_cases_after_closure"] == 10

    assert closure["expected_community_moderation_cases_after_closure"] == 194

    assert closure["expected_community_moderation_test_files_after_closure"] == 16

    assert closure["expected_public_mobile_cases_after_closure"] == 61

    assert closure["expected_backend_reporting_cases_after_closure"] == 70

    assert closure["8E12A"] == "completed"

    assert closure["8E12B"] == "completed"

    assert closure["8E12C"] == "completed"

    assert closure["8E12"] == "completed"

    assert closure["8E_moderation_reporting_operational_closure"] == "completed"
