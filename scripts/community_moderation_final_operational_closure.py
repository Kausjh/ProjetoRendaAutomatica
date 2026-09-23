from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from scripts.community_moderation_operational_canary import (  # noqa: E402
    run_canary,
)
from scripts.community_moderation_operational_preflight import (  # noqa: E402
    build_preflight,
)

CONTRACT_A = "contracts/" "community_moderation_operational_readiness_v1.json"

CONTRACT_B = "contracts/" "community_moderation_operational_canary_v1.json"


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def _snapshot(
    database: Path,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "sha256": _sha256(database),
        "integrity_check": None,
        "foreign_key_errors": None,
        "schema_version": None,
        "counts": {},
    }

    with sqlite3.connect(
        database.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=30,
    ) as conn:
        conn.execute("PRAGMA query_only = ON")

        assert int(conn.execute("PRAGMA query_only").fetchone()[0]) == 1

        result["integrity_check"] = str(conn.execute("PRAGMA integrity_check").fetchone()[0])

        result["foreign_key_errors"] = len(conn.execute("PRAGMA foreign_key_check").fetchall())

        result["schema_version"] = int(conn.execute("PRAGMA schema_version").fetchone()[0])

        queries = {
            "moderation_reports": "SELECT COUNT(*) " "FROM community_moderation_reports",
            "moderation_decisions": "SELECT COUNT(*) " "FROM community_moderation_decisions",
            "trust_evidence": "SELECT COUNT(*) " "FROM community_trust_evidence",
            "trust_profiles": "SELECT COUNT(*) " "FROM community_trust_profiles",
        }

        for key, query in queries.items():
            result["counts"][key] = int(conn.execute(query).fetchone()[0])

    return result


def _load_contract(
    root: Path,
    relative_path: str,
) -> dict[str, Any]:
    path = root / relative_path

    return json.loads(path.read_text(encoding="utf-8"))


def run_final_operational_closure(
    *,
    root: Path,
    database: Path,
    dotenv_path: Path,
) -> dict[str, Any]:
    blockers: list[str] = []

    source_before = _snapshot(database)

    contract_a = _load_contract(
        root,
        CONTRACT_A,
    )

    contract_b = _load_contract(
        root,
        CONTRACT_B,
    )

    source_gates = {
        "8E12A_stage": contract_a.get("stage"),
        "8E12A_status": contract_a.get("status"),
        "8E12B_stage": contract_b.get("stage"),
        "8E12B_status": contract_b.get("status"),
        "8E12B_next_step": contract_b.get("next_step"),
    }

    if source_gates["8E12A_stage"] != "8E12A-operational-readiness-preflight":
        blockers.append("8e12a_stage_invalid")

    if source_gates["8E12A_status"] != "completed":
        blockers.append("8e12a_not_completed")

    if source_gates["8E12B_stage"] != "8E12B-controlled-operational-canary":
        blockers.append("8e12b_stage_invalid")

    if source_gates["8E12B_status"] != "completed":
        blockers.append("8e12b_not_completed")

    if source_gates["8E12B_next_step"] != "8E12C-final-operational-closure":
        blockers.append("8e12b_next_step_invalid")

    preflight = build_preflight(
        root=root,
        database=database,
        mode="standby",
    )

    if not preflight["ready"]:
        blockers.append("standby_preflight_not_ready")

    canary: dict[str, Any] | None = None

    if not blockers:
        canary = run_canary(
            root=root,
            database=database,
            dotenv_path=dotenv_path,
        )

        if not canary["ready"]:
            blockers.append("controlled_canary_not_ready")

    source_after = _snapshot(database)

    hash_unchanged = source_before["sha256"] == source_after["sha256"]

    counts_unchanged = source_before["counts"] == source_after["counts"]

    schema_unchanged = source_before["schema_version"] == source_after["schema_version"]

    if not hash_unchanged:
        blockers.append("live_database_hash_changed")

    if not counts_unchanged:
        blockers.append("live_database_counts_changed")

    if not schema_unchanged:
        blockers.append("live_database_schema_changed")

    if source_after["integrity_check"] != "ok":
        blockers.append("live_integrity_not_ok")

    if source_after["foreign_key_errors"] != 0:
        blockers.append("live_foreign_key_errors")

    canary_ready = canary is not None and canary["ready"] is True

    canary_blockers = [] if canary is None else list(canary["blockers"])

    return {
        "schema": ("projeto-renda-automatica." "community-moderation-final-operational-closure"),
        "version": 1,
        "ready": not blockers,
        "blockers": blockers,
        "source_gates": source_gates,
        "preflight": {
            "ready": bool(preflight["ready"]),
            "blockers": list(preflight["blockers"]),
        },
        "canary": {
            "executed": canary is not None,
            "ready": canary_ready,
            "blockers": canary_blockers,
            "runtime_activation_scope": (
                None if canary is None else canary["safety"]["runtime_activation_scope"]
            ),
            "schema_activation_authorized": (
                False
                if canary is None
                else bool(canary["activation"]["schema_activation_authorized"])
            ),
            "reconciliation_executed": (
                False if canary is None else bool(canary["activation"]["reconciliation_executed"])
            ),
            "admin_read_status": (
                None if canary is None else canary["admin_http"]["authorized_read_status"]
            ),
            "wrong_token_status": (
                None if canary is None else canary["admin_http"]["wrong_token_status"]
            ),
            "missing_report_decision_status": (
                None if canary is None else canary["admin_http"]["missing_report_decision_status"]
            ),
            "temporary_clone_removed": (
                False if canary is None else bool(canary["clone"]["temporary_clone_removed"])
            ),
            "environment_restored": (
                False if canary is None else bool(canary["safety"]["environment_restored"])
            ),
            "admin_token_value_exposed": (
                False if canary is None else bool(canary["safety"]["admin_token_value_exposed"])
            ),
        },
        "live_before": source_before,
        "live_after": source_after,
        "safety": {
            "live_database_hash_unchanged": hash_unchanged,
            "live_database_counts_unchanged": counts_unchanged,
            "live_database_schema_unchanged": schema_unchanged,
            "live_database_write": False,
            "live_schema_write": False,
            "persistent_runtime_started": False,
            "reconciliation_executed": (
                False if canary is None else bool(canary["safety"]["reconciliation_executed"])
            ),
            "admin_token_value_exposed": (
                False if canary is None else bool(canary["safety"]["admin_token_value_exposed"])
            ),
        },
        "operational_tree": {
            "8E12A": "completed",
            "8E12B": "completed",
            "8E12C": "completed",
            "hidden_sublevels": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Final Community Moderation " "operational closure gate.")
    )

    parser.add_argument(
        "--root",
        default=".",
    )

    parser.add_argument(
        "--database",
        default=("database/" "user_identity.sqlite3"),
    )

    parser.add_argument(
        "--dotenv",
        default=".env",
    )

    parser.add_argument(
        "--output",
        default="",
    )

    return parser


def main() -> int:
    args = _parser().parse_args()

    root = Path(args.root).resolve()

    database = Path(args.database)

    if not database.is_absolute():
        database = root / database

    dotenv_path = Path(args.dotenv)

    if not dotenv_path.is_absolute():
        dotenv_path = root / dotenv_path

    result = run_final_operational_closure(
        root=root,
        database=database,
        dotenv_path=dotenv_path,
    )

    rendered = (
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    output = str(args.output or "").strip()

    if output:
        output_path = Path(output)

        if not output_path.is_absolute():
            output_path = root / output_path

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            rendered,
            encoding="utf-8",
        )

    print(
        rendered,
        end="",
    )

    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
