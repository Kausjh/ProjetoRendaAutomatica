from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = ROOT / "scripts" / "community_moderation_operational_preflight.py"

CONTRACT = ROOT / "contracts" / "community_moderation_operational_readiness_v1.json"


def _database(
    path: Path,
    *,
    complete: bool = True,
) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE community_moderation_reports (
                id TEXT PRIMARY KEY
            )
            """)

        if complete:
            conn.execute("""
                CREATE TABLE community_moderation_decisions (
                    id TEXT PRIMARY KEY
                )
                """)

            conn.execute("""
                CREATE TABLE community_trust_evidence (
                    id TEXT PRIMARY KEY
                )
                """)

            conn.execute("""
                CREATE TABLE community_trust_profiles (
                    id TEXT PRIMARY KEY
                )
                """)


def _run(
    database: Path,
    *,
    mode: str,
    runtime: str,
    reconciliation: str,
    token: str | None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()

    env["COMMUNITY_MODERATION_RUNTIME_ATIVO"] = runtime

    env["COMMUNITY_MODERATION_RECONCILIATION_STARTUP_ATIVA"] = reconciliation

    if token is None:
        env["RADAR_ADMIN_TOKEN"] = ""
    else:
        env["RADAR_ADMIN_TOKEN"] = token

    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ROOT),
            "--database",
            str(database),
            "--mode",
            mode,
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


def test_8e12a_contract_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E12A-operational-readiness-preflight"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "3e66ed1"

    assert data["next_step"] == "8E12B-controlled-operational-canary"


def test_preflight_script_compiles():
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


def test_standby_ready_with_safe_flags(
    tmp_path: Path,
):
    database = tmp_path / "standby.sqlite3"

    _database(database)

    completed = _run(
        database,
        mode="standby",
        runtime="0",
        reconciliation="0",
        token=None,
    )

    assert completed.returncode == 0

    payload = _payload(completed)

    assert payload["ready"] is True
    assert payload["blockers"] == []

    assert payload["database"]["opened_read_only"] is True

    assert payload["database"]["query_only"] is True


def test_standby_blocks_runtime_enabled(
    tmp_path: Path,
):
    database = tmp_path / "runtime-on.sqlite3"

    _database(database)

    completed = _run(
        database,
        mode="standby",
        runtime="1",
        reconciliation="0",
        token=None,
    )

    assert completed.returncode == 2

    payload = _payload(completed)

    assert payload["ready"] is False

    assert "runtime_flag_should_be_off" in payload["blockers"]


def test_activation_requires_admin_token(
    tmp_path: Path,
):
    database = tmp_path / "activation-no-token.sqlite3"

    _database(database)

    completed = _run(
        database,
        mode="activation",
        runtime="1",
        reconciliation="0",
        token=None,
    )

    assert completed.returncode == 2

    payload = _payload(completed)

    assert "admin_token_not_configured" in payload["blockers"]


def test_activation_readiness_does_not_activate(
    tmp_path: Path,
):
    database = tmp_path / "activation-ready.sqlite3"

    _database(database)

    completed = _run(
        database,
        mode="activation",
        runtime="1",
        reconciliation="0",
        token="8e12a-test-token",
    )

    assert completed.returncode == 0

    payload = _payload(completed)

    assert payload["ready"] is True

    assert payload["safety"]["runtime_activation_performed"] is False

    assert payload["safety"]["reconciliation_performed"] is False

    assert payload["safety"]["database_write_performed"] is False


def test_admin_token_value_is_never_exposed(
    tmp_path: Path,
):
    database = tmp_path / "token.sqlite3"

    _database(database)

    secret = "super-secret-8e12a-token"

    completed = _run(
        database,
        mode="activation",
        runtime="1",
        reconciliation="0",
        token=secret,
    )

    assert completed.returncode == 0
    assert secret not in completed.stdout

    payload = _payload(completed)

    assert payload["configuration"]["admin_token_configured"] is True

    assert payload["configuration"]["admin_token_value_exposed"] is False


def test_missing_database_fails_closed(
    tmp_path: Path,
):
    database = tmp_path / "missing.sqlite3"

    completed = _run(
        database,
        mode="standby",
        runtime="0",
        reconciliation="0",
        token=None,
    )

    assert completed.returncode == 2

    payload = _payload(completed)

    assert "database_missing" in payload["blockers"]


def test_missing_required_table_fails_closed(
    tmp_path: Path,
):
    database = tmp_path / "incomplete.sqlite3"

    _database(
        database,
        complete=False,
    )

    completed = _run(
        database,
        mode="standby",
        runtime="0",
        reconciliation="0",
        token=None,
    )

    assert completed.returncode == 2

    payload = _payload(completed)

    assert "required_tables_missing" in payload["blockers"]


def test_operational_tree_is_only_a_b_c():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    tree = data["operational_closure_tree"]

    assert tree == {
        "8E12A": "operational-readiness-preflight",
        "8E12B": "controlled-operational-canary",
        "8E12C": "final-operational-closure",
        "hidden_sublevels": False,
    }

    assert data["safety_boundary"]["runtime_activation"] is False

    assert data["safety_boundary"]["live_canary"] is False

    assert data["safety_boundary"]["database_write"] is False


def test_8e12a_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E12B-controlled-operational-canary"

    validation = data["validation"]

    assert validation["baseline_commit"] == "3e66ed1"

    assert validation["materialized_state_recovered"] is True

    assert validation["implementation_recreated"] is False

    assert validation["pre_commit_passed"] is True

    assert validation["python_syntax_passed"] is True

    assert validation["temporary_json_encoding"] == "utf-8-no-bom"

    assert validation["process_environment_precedence"] is True

    assert validation["explicit_empty_process_value_masks_dotenv"] is True

    assert validation["admin_token_test_isolation"] is True

    assert validation["real_standby_preflight_ready"] is True

    assert validation["real_standby_preflight_blockers"] == 0

    assert validation["database_open_mode"] == "read-only"

    assert validation["database_query_only"] is True

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0

    assert validation["required_tables_complete"] is True

    assert validation["terminal_contract_8E9C"] == "completed"

    assert validation["terminal_contract_8E10C"] == "completed"

    assert validation["terminal_contract_8E11C"] == "completed"

    assert validation["runtime_wiring_complete"] is True

    assert validation["admin_token_configured"] is True

    assert validation["admin_token_value_exposed"] is False

    assert validation["live_moderation_report_rows"] == 0

    assert validation["live_moderation_decision_rows"] == 0

    assert validation["live_trust_evidence_total"] == 2

    assert validation["live_trust_profile_total"] == 1

    assert validation["isolated_8e12a_cases_passed_pre_closure"] == 10

    assert validation["community_moderation_test_files"] == 14

    assert validation["community_moderation_cases_passed_pre_closure"] == 171

    assert validation["public_mobile_test_files"] == 6

    assert validation["public_mobile_cases_passed"] == 61

    assert validation["backend_reporting_cases_passed"] == 70

    assert validation["runtime_activated"] is False

    assert validation["reconciliation_executed"] is False

    assert validation["admin_http_request_performed"] is False

    assert validation["user_http_request_performed"] is False

    assert validation["live_canary_performed"] is False

    assert validation["live_database_write"] is False

    assert validation["live_schema_write"] is False

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_8e12a_cases_after_closure"] == 11

    assert closure["expected_community_moderation_cases_after_closure"] == 172

    assert closure["expected_community_moderation_test_files_after_closure"] == 14

    assert closure["expected_public_mobile_cases_after_closure"] == 61

    assert closure["expected_public_mobile_test_files_after_closure"] == 6

    assert closure["expected_backend_reporting_cases_after_closure"] == 70

    assert closure["8E12A"] == "completed"
    assert closure["8E12B"] == "pending"
    assert closure["8E12C"] == "pending"
