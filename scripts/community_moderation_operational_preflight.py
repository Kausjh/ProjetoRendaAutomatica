from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

TRUTHY = {
    "1",
    "true",
    "yes",
    "on",
}

RUNTIME_FLAG = "COMMUNITY_MODERATION_RUNTIME_ATIVO"

RECONCILIATION_FLAG = "COMMUNITY_MODERATION_" "RECONCILIATION_STARTUP_ATIVA"

ADMIN_TOKEN_ENV = "RADAR_ADMIN_TOKEN"

REQUIRED_TABLES = {
    "community_moderation_reports",
    "community_moderation_decisions",
    "community_trust_evidence",
    "community_trust_profiles",
}

TERMINAL_STAGE_PREFIXES = (
    "8E9C",
    "8E10C",
    "8E11C",
)

RUNTIME_MARKERS = (
    "_ativar_community_moderation_controlado",
    "permitir_schema_activation=True",
    "executar_reconciliation=False",
    "community_moderation_decision_service",
    "community_moderation_repository=",
)


def _truthy(
    value: str | None,
) -> bool:
    if value is None:
        return False

    return value.strip().casefold() in TRUTHY


def _read_dotenv(
    path: Path,
) -> dict[str, str]:
    result: dict[str, str] = {}

    if not path.is_file():
        return result

    for raw in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        line = raw.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        key, value = line.split(
            "=",
            1,
        )

        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0]
            in {
                '"',
                "'",
            }
        ):
            value = value[1:-1]

        if key:
            result[key] = value

    return result


def _effective_value(
    name: str,
    dotenv: dict[str, str],
) -> tuple[str, str]:
    if name in os.environ:
        return (
            os.environ.get(
                name,
                "",
            ).strip(),
            "process",
        )

    dotenv_value = dotenv.get(
        name,
        "",
    ).strip()

    if dotenv_value:
        return (
            dotenv_value,
            "dotenv",
        )

    return (
        "",
        "unset",
    )


def _terminal_contracts(
    root: Path,
) -> dict[str, dict[str, Any]]:
    contracts_dir = root / "contracts"

    result: dict[str, dict[str, Any]] = {}

    for prefix in TERMINAL_STAGE_PREFIXES:
        matches: list[dict[str, str]] = []

        for path in sorted(contracts_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (
                OSError,
                json.JSONDecodeError,
            ):
                continue

            stage = str(
                payload.get(
                    "stage",
                    "",
                )
            ).strip()

            if not stage.startswith(prefix):
                continue

            matches.append(
                {
                    "file": str(path.relative_to(root)).replace(
                        "\\",
                        "/",
                    ),
                    "stage": stage,
                    "status": str(
                        payload.get(
                            "status",
                            "",
                        )
                    ).strip(),
                }
            )

        completed = any(item["status"] == "completed" for item in matches)

        result[prefix] = {
            "found": bool(matches),
            "completed": completed,
            "matches": matches,
        }

    return result


def _runtime_wiring(
    root: Path,
) -> dict[str, Any]:
    path = root / "runtime.py"

    if not path.is_file():
        return {
            "file_present": False,
            "markers": {},
            "complete": False,
        }

    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    markers = {marker: marker in source for marker in RUNTIME_MARKERS}

    return {
        "file_present": True,
        "markers": markers,
        "complete": all(markers.values()),
    }


def _database_snapshot(
    database: Path,
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "path": str(database),
        "exists": database.is_file(),
        "opened_read_only": False,
        "query_only": False,
        "integrity_check": None,
        "foreign_key_errors": None,
        "required_tables": {},
        "required_tables_complete": False,
        "counts": {},
    }

    if not database.is_file():
        return snapshot

    try:
        uri = database.resolve().as_uri() + "?mode=ro"

        with sqlite3.connect(
            uri,
            uri=True,
            timeout=30,
        ) as conn:
            conn.execute("PRAGMA query_only = ON")

            conn.execute("PRAGMA foreign_keys = ON")

            snapshot["opened_read_only"] = True

            snapshot["query_only"] = int(conn.execute("PRAGMA query_only").fetchone()[0]) == 1

            snapshot["integrity_check"] = str(conn.execute("PRAGMA integrity_check").fetchone()[0])

            snapshot["foreign_key_errors"] = len(
                conn.execute("PRAGMA foreign_key_check").fetchall()
            )

            tables = {str(row[0]) for row in conn.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """).fetchall()}

            table_state = {table: table in tables for table in sorted(REQUIRED_TABLES)}

            snapshot["required_tables"] = table_state

            snapshot["required_tables_complete"] = all(table_state.values())

            count_queries = {
                "moderation_reports": "SELECT COUNT(*) " "FROM community_moderation_reports",
                "moderation_decisions": "SELECT COUNT(*) " "FROM community_moderation_decisions",
                "trust_evidence": "SELECT COUNT(*) " "FROM community_trust_evidence",
                "trust_profiles": "SELECT COUNT(*) " "FROM community_trust_profiles",
            }

            for (
                key,
                query,
            ) in count_queries.items():
                table = {
                    "moderation_reports": "community_moderation_reports",
                    "moderation_decisions": "community_moderation_decisions",
                    "trust_evidence": "community_trust_evidence",
                    "trust_profiles": "community_trust_profiles",
                }[key]

                if table not in tables:
                    continue

                snapshot["counts"][key] = int(conn.execute(query).fetchone()[0])

    except sqlite3.Error as exc:
        snapshot["sqlite_error"] = f"{type(exc).__name__}: " f"{exc}"

    return snapshot


def build_preflight(
    *,
    root: Path,
    database: Path,
    mode: str,
) -> dict[str, Any]:
    dotenv = _read_dotenv(root / ".env")

    runtime_raw, runtime_source = _effective_value(
        RUNTIME_FLAG,
        dotenv,
    )

    reconciliation_raw, reconciliation_source = _effective_value(
        RECONCILIATION_FLAG,
        dotenv,
    )

    token_raw, token_source = _effective_value(
        ADMIN_TOKEN_ENV,
        dotenv,
    )

    runtime_active = _truthy(runtime_raw)

    reconciliation_active = _truthy(reconciliation_raw)

    admin_token_configured = bool(token_raw.strip())

    database_state = _database_snapshot(database)

    terminal_contracts = _terminal_contracts(root)

    runtime_wiring = _runtime_wiring(root)

    blockers: list[str] = []

    if not database_state["exists"]:
        blockers.append("database_missing")

    elif not database_state["opened_read_only"]:
        blockers.append("database_read_only_open_failed")

    if database_state["integrity_check"] != "ok":
        blockers.append("database_integrity_not_ok")

    if database_state["foreign_key_errors"] not in {
        0,
    }:
        blockers.append("database_foreign_key_errors")

    if not database_state["required_tables_complete"]:
        blockers.append("required_tables_missing")

    incomplete_contracts = [
        prefix
        for (
            prefix,
            state,
        ) in terminal_contracts.items()
        if not state["completed"]
    ]

    if incomplete_contracts:
        blockers.append("terminal_contracts_incomplete")

    if not runtime_wiring["complete"]:
        blockers.append("runtime_wiring_incomplete")

    if mode == "standby":
        if runtime_active:
            blockers.append("runtime_flag_should_be_off")

        if reconciliation_active:
            blockers.append("reconciliation_flag_should_be_off")

    elif mode == "activation":
        if not runtime_active:
            blockers.append("runtime_flag_should_be_on")

        if reconciliation_active:
            blockers.append("reconciliation_startup_should_be_off")

        if not admin_token_configured:
            blockers.append("admin_token_not_configured")

    else:
        blockers.append("invalid_mode")

    return {
        "schema": ("projeto-renda-automatica." "community-moderation-operational-preflight"),
        "version": 1,
        "mode": mode,
        "ready": not blockers,
        "blockers": blockers,
        "configuration": {
            "runtime_flag_active": runtime_active,
            "runtime_flag_source": runtime_source,
            "reconciliation_flag_active": reconciliation_active,
            "reconciliation_flag_source": reconciliation_source,
            "admin_token_configured": admin_token_configured,
            "admin_token_source": token_source,
            "admin_token_value_exposed": False,
        },
        "database": database_state,
        "terminal_contracts": terminal_contracts,
        "runtime_wiring": runtime_wiring,
        "safety": {
            "runtime_activation_performed": False,
            "reconciliation_performed": False,
            "admin_http_request_performed": False,
            "user_http_request_performed": False,
            "database_write_performed": False,
            "schema_write_performed": False,
            "secret_value_printed": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Community Moderation " "operational readiness preflight.")
    )

    parser.add_argument(
        "--mode",
        choices=(
            "standby",
            "activation",
        ),
        default="standby",
    )

    parser.add_argument(
        "--database",
        default=("database/" "user_identity.sqlite3"),
    )

    parser.add_argument(
        "--root",
        default=".",
    )

    return parser


def main() -> int:
    args = _parser().parse_args()

    root = Path(args.root).resolve()

    database = Path(args.database)

    if not database.is_absolute():
        database = root / database

    report = build_preflight(
        root=root,
        database=database,
        mode=args.mode,
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
