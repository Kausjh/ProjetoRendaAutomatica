from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from scripts.community_moderation_operational_preflight import (  # noqa: E402
    build_preflight,
)
from services.community_moderation_authority import (  # noqa: E402
    CommunityModerationAuthorityV1,
)
from services.community_moderation_read_service import (  # noqa: E402
    CommunityModerationReadService,
)
from services.community_moderation_runtime import (  # noqa: E402
    ativar_community_moderation_runtime,
)
from services.controle.servidor_status import (  # noqa: E402
    ServidorStatusAdministrativo,
)

RUNTIME_FLAG = "COMMUNITY_MODERATION_RUNTIME_ATIVO"

RECONCILIATION_FLAG = "COMMUNITY_MODERATION_" "RECONCILIATION_STARTUP_ATIVA"

ADMIN_TOKEN_ENV = "RADAR_ADMIN_TOKEN"

MISSING_REPORT_ID = "rpt_8e12b_controlled_canary_missing_v1"


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


def _admin_token(
    dotenv_path: Path,
) -> tuple[str, str]:
    if ADMIN_TOKEN_ENV in os.environ:
        return (
            os.environ.get(
                ADMIN_TOKEN_ENV,
                "",
            ).strip(),
            "process",
        )

    dotenv = _read_dotenv(dotenv_path)

    return (
        dotenv.get(
            ADMIN_TOKEN_ENV,
            "",
        ).strip(),
        ("dotenv" if ADMIN_TOKEN_ENV in dotenv else "unset"),
    )


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
    snapshot: dict[str, Any] = {
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

        snapshot["integrity_check"] = str(conn.execute("PRAGMA integrity_check").fetchone()[0])

        snapshot["foreign_key_errors"] = len(conn.execute("PRAGMA foreign_key_check").fetchall())

        snapshot["schema_version"] = int(conn.execute("PRAGMA schema_version").fetchone()[0])

        queries = {
            "moderation_reports": "SELECT COUNT(*) " "FROM community_moderation_reports",
            "moderation_decisions": "SELECT COUNT(*) " "FROM community_moderation_decisions",
            "trust_evidence": "SELECT COUNT(*) " "FROM community_trust_evidence",
            "trust_profiles": "SELECT COUNT(*) " "FROM community_trust_profiles",
        }

        for key, query in queries.items():
            snapshot["counts"][key] = int(conn.execute(query).fetchone()[0])

    return snapshot


def _clone_database(
    source: Path,
    target: Path,
) -> None:
    source_uri = source.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(
        source_uri,
        uri=True,
        timeout=30,
    ) as source_conn:
        source_conn.execute("PRAGMA query_only = ON")

        with sqlite3.connect(
            target,
            timeout=30,
        ) as target_conn:
            source_conn.backup(target_conn)


def _get_json(
    url: str,
    *,
    token: str,
) -> tuple[
    int,
    dict[str, Any],
]:
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Request-Id": "8e12b-canary-read",
            "X-Radar-Device": "8e12b-operational-canary",
        },
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=5,
        ) as response:
            return (
                int(response.status),
                json.loads(response.read().decode("utf-8")),
            )

    except HTTPError as error:
        return (
            int(error.code),
            json.loads(error.read().decode("utf-8")),
        )


def _post_missing_decision(
    url: str,
    *,
    token: str,
) -> tuple[
    int,
    dict[str, Any],
]:
    payload = json.dumps(
        {
            "resultado": "dismissed",
            "justificativa": ("8E12B controlled canary " "against missing report"),
            "ocorrido_em": "2026-09-22T18:00:00+00:00",
        }
    ).encode("utf-8")

    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Idempotency-Key": "8e12b-missing-report-probe-v1",
            "X-Request-Id": "8e12b-canary-decision",
            "X-Radar-Device": "8e12b-operational-canary",
        },
        method="POST",
        data=payload,
    )

    try:
        with urlopen(
            request,
            timeout=5,
        ) as response:
            return (
                int(response.status),
                json.loads(response.read().decode("utf-8")),
            )

    except HTTPError as error:
        return (
            int(error.code),
            json.loads(error.read().decode("utf-8")),
        )


def _environment_state(
    name: str,
) -> tuple[
    bool,
    str | None,
]:
    return (
        name in os.environ,
        os.environ.get(name),
    )


def _restore_environment(
    name: str,
    state: tuple[
        bool,
        str | None,
    ],
) -> None:
    existed, value = state

    if existed:
        os.environ[name] = "" if value is None else value
    else:
        os.environ.pop(
            name,
            None,
        )


def _remove_temp_dir_with_retry(
    temp_dir: Path,
    *,
    attempts: int = 20,
    delay_seconds: float = 0.1,
) -> bool:
    for attempt in range(attempts):
        gc.collect()

        try:
            shutil.rmtree(temp_dir)

        except FileNotFoundError:
            return True

        except OSError:
            if attempt + 1 >= attempts:
                break

            time.sleep(delay_seconds)

            continue

        if not temp_dir.exists():
            return True

        if attempt + 1 < attempts:
            time.sleep(delay_seconds)

    gc.collect()

    return not temp_dir.exists()


def run_canary(
    *,
    root: Path,
    database: Path,
    dotenv_path: Path,
) -> dict[str, Any]:
    blockers: list[str] = []

    source_before = _snapshot(database)

    standby = build_preflight(
        root=root,
        database=database,
        mode="standby",
    )

    if not standby["ready"]:
        blockers.append("standby_preflight_not_ready")

    token, token_source = _admin_token(dotenv_path)

    if not token:
        blockers.append("admin_token_not_configured")

    if blockers:
        return {
            "schema": ("projeto-renda-automatica." "community-moderation-operational-canary"),
            "version": 1,
            "ready": False,
            "blockers": blockers,
            "standby_preflight_ready": bool(standby["ready"]),
            "admin_token_configured": bool(token),
            "admin_token_source": token_source,
            "admin_token_value_exposed": False,
            "source_before": source_before,
            "safety": {
                "source_database_write": False,
                "persistent_runtime_started": False,
                "reconciliation_executed": False,
                "admin_token_value_exposed": False,
            },
        }

    temp_dir = Path(tempfile.mkdtemp(prefix=("radar_8e12b_")))

    clone = temp_dir / "canary.sqlite3"

    runtime_state = _environment_state(RUNTIME_FLAG)

    reconciliation_state = _environment_state(RECONCILIATION_FLAG)

    server = None
    authority = None
    activation = None
    read_service = None

    activation_active = False
    schema_authorized = False
    reconciliation_executed = False
    components_present = False
    admin_server_started = False
    admin_server_stopped = False
    environment_restored = False

    read_status = None
    read_quantity = None
    wrong_token_status = None
    decision_missing_status = None

    clone_before: dict[str, Any] | None = None
    clone_after: dict[str, Any] | None = None

    try:
        _clone_database(
            database,
            clone,
        )

        clone_before = _snapshot(clone)

        os.environ[RUNTIME_FLAG] = "1"

        os.environ[RECONCILIATION_FLAG] = "0"

        authority = CommunityModerationAuthorityV1(
            token_administrativo=token,
        )

        activation = ativar_community_moderation_runtime(
            caminho_banco=clone,
            permitir_schema_activation=True,
            authority=authority,
            executar_reconciliation=False,
        )

        activation_active = bool(activation.ativo)

        schema_authorized = bool(activation.schema_activation_autorizada)

        reconciliation_executed = bool(activation.reconciliation_executada)

        components_present = activation.componentes is not None

        if not activation_active:
            blockers.append("runtime_activation_failed")

        if not schema_authorized:
            blockers.append("schema_activation_not_authorized")

        if reconciliation_executed:
            blockers.append("reconciliation_executed_unexpectedly")

        if not components_present:
            blockers.append("runtime_components_missing")

        if not blockers:
            assert activation.componentes is not None

            read_service = CommunityModerationReadService(clone)

            server = ServidorStatusAdministrativo(
                object(),  # type: ignore[arg-type]
                host="127.0.0.1",
                porta=0,
                token=token,
            )

            server.community_moderation_read_service = read_service

            server.community_moderation_decision_service = activation.componentes.moderation_service

            server.iniciar()

            admin_server_started = True

            if server._servidor is None:
                blockers.append("admin_server_not_started")

            else:
                port = int(server._servidor.server_address[1])

                base = "http://127.0.0.1:" + str(port)

                (
                    read_status,
                    read_body,
                ) = _get_json(
                    (base + "/moderation/reports" + "?limite=1&offset=0"),
                    token=token,
                )

                if read_status != 200:
                    blockers.append("authorized_admin_read_failed")

                if isinstance(
                    read_body,
                    dict,
                ):
                    quantity = read_body.get("quantidade")

                    if isinstance(
                        quantity,
                        int,
                    ):
                        read_quantity = quantity

                wrong_token = token + "-wrong"

                (
                    wrong_token_status,
                    _,
                ) = _get_json(
                    (base + "/moderation/reports"),
                    token=wrong_token,
                )

                if wrong_token_status != 401:
                    blockers.append("wrong_token_not_rejected")

                (
                    decision_missing_status,
                    _,
                ) = _post_missing_decision(
                    (base + "/moderation/reports/" + MISSING_REPORT_ID + "/decision"),
                    token=token,
                )

                if decision_missing_status != 404:
                    blockers.append("missing_report_decision_probe_not_404")

        clone_after = _snapshot(clone)

        if clone_before["counts"] != clone_after["counts"]:
            blockers.append("clone_data_counts_changed")

        if clone_before["schema_version"] != clone_after["schema_version"]:
            blockers.append("clone_schema_version_changed")

        if clone_after["integrity_check"] != "ok":
            blockers.append("clone_integrity_not_ok")

        if clone_after["foreign_key_errors"] != 0:
            blockers.append("clone_foreign_key_errors")

    finally:
        if server is not None:
            try:
                server.encerrar()
                admin_server_stopped = True
            except Exception:
                blockers.append("admin_server_stop_failed")

        _restore_environment(
            RUNTIME_FLAG,
            runtime_state,
        )

        _restore_environment(
            RECONCILIATION_FLAG,
            reconciliation_state,
        )

        environment_restored = (
            _environment_state(RUNTIME_FLAG) == runtime_state
            and _environment_state(RECONCILIATION_FLAG) == reconciliation_state
        )

        if server is not None:
            try:
                server.community_moderation_read_service = None
                server.community_moderation_decision_service = None
            except Exception:
                pass

        read_service = None
        authority = None
        activation = None
        server = None

        gc.collect()

        _remove_temp_dir_with_retry(
            temp_dir,
            attempts=20,
            delay_seconds=0.1,
        )

    source_after = _snapshot(database)

    source_hash_unchanged = source_before["sha256"] == source_after["sha256"]

    source_counts_unchanged = source_before["counts"] == source_after["counts"]

    source_schema_unchanged = source_before["schema_version"] == source_after["schema_version"]

    temp_clone_removed = not temp_dir.exists()

    if not source_hash_unchanged:
        blockers.append("source_database_hash_changed")

    if not source_counts_unchanged:
        blockers.append("source_database_counts_changed")

    if not source_schema_unchanged:
        blockers.append("source_database_schema_changed")

    if not environment_restored:
        blockers.append("environment_not_restored")

    if not admin_server_stopped:
        blockers.append("admin_server_not_stopped")

    if not temp_clone_removed:
        blockers.append("temporary_clone_not_removed")

    return {
        "schema": ("projeto-renda-automatica." "community-moderation-operational-canary"),
        "version": 1,
        "ready": not blockers,
        "blockers": blockers,
        "standby_preflight_ready": bool(standby["ready"]),
        "admin_token_configured": True,
        "admin_token_source": token_source,
        "admin_token_value_exposed": False,
        "source_before": source_before,
        "source_after": source_after,
        "activation": {
            "active": activation_active,
            "schema_activation_authorized": schema_authorized,
            "components_present": components_present,
            "reconciliation_executed": reconciliation_executed,
        },
        "admin_http": {
            "server_started": admin_server_started,
            "server_stopped": admin_server_stopped,
            "authorized_read_status": read_status,
            "authorized_read_quantity": read_quantity,
            "wrong_token_status": wrong_token_status,
            "missing_report_decision_status": decision_missing_status,
        },
        "clone": {
            "before": clone_before,
            "after": clone_after,
            "counts_unchanged": (
                clone_before is not None
                and clone_after is not None
                and clone_before["counts"] == clone_after["counts"]
            ),
            "schema_version_unchanged": (
                clone_before is not None
                and clone_after is not None
                and clone_before["schema_version"] == clone_after["schema_version"]
            ),
            "temporary_clone_removed": temp_clone_removed,
        },
        "safety": {
            "source_database_hash_unchanged": source_hash_unchanged,
            "source_database_counts_unchanged": source_counts_unchanged,
            "source_database_schema_unchanged": source_schema_unchanged,
            "source_database_write": False,
            "persistent_runtime_started": False,
            "runtime_activation_scope": "temporary-clone-process-only",
            "environment_restored": environment_restored,
            "reconciliation_executed": reconciliation_executed,
            "admin_token_value_exposed": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Controlled Community Moderation " "operational canary.")
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

    result = run_canary(
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
