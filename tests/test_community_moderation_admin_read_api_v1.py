from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from services.community_moderation_read_service import (
    CommunityModerationReadService,
)
from services.controle.servidor_status import (
    ServidorStatusAdministrativo,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_admin_read_api_v1.json"

RUNTIME = ROOT / "runtime.py"

SERVER_SOURCE = ROOT / "services" / "controle" / "servidor_status.py"

WRITE_REPOSITORY = ROOT / "repositories" / "community_moderation_repository.py"


class FakeModerationReadService:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def listar_pendentes(
        self,
        *,
        limite: object,
        offset: object,
    ) -> dict[str, object]:
        self.calls.append(
            (
                "listar",
                limite,
                offset,
            )
        )

        return {
            "api_version": "v1",
            "recurso": ("moderation_reports_pending"),
            "limite": int(limite),
            "offset": int(offset),
            "quantidade": 0,
            "itens": [],
        }

    def obter_denuncia(
        self,
        denuncia_id: object,
    ) -> dict[str, object] | None:
        self.calls.append(
            (
                "obter",
                denuncia_id,
            )
        )

        if denuncia_id != "rpt_test":
            return None

        return {
            "api_version": "v1",
            "recurso": ("moderation_report"),
            "denuncia": {
                "id": "rpt_test",
                "estado": "received",
            },
            "decisoes": [],
        }


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _create_read_db(
    tmp_path: Path,
) -> Path:
    db = tmp_path / "moderation.sqlite3"

    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE
                community_moderation_reports (
                    id TEXT PRIMARY KEY,
                    chave_idempotencia TEXT
                        NOT NULL UNIQUE,
                    reporter_conta_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    motivo TEXT NOT NULL,
                    detalhes TEXT,
                    estado TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                );

            CREATE TABLE
                community_moderation_decisions (
                    id TEXT PRIMARY KEY,
                    chave_idempotencia TEXT
                        NOT NULL UNIQUE,
                    denuncia_id TEXT NOT NULL,
                    moderator_actor_id TEXT NOT NULL,
                    resultado TEXT NOT NULL,
                    familia_abuso_confirmado TEXT,
                    justificativa TEXT,
                    ocorrido_em TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                );
            """)

    return db


def _request_json(
    url: str,
    *,
    token: str | None = None,
) -> tuple[
    int,
    dict[str, object],
]:
    headers: dict[str, str] = {}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        url,
        headers=headers,
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=5,
        ) as response:
            return (
                response.status,
                json.loads(response.read().decode("utf-8")),
            )

    except HTTPError as error:
        return (
            error.code,
            json.loads(error.read().decode("utf-8")),
        )


def _start_server(
    *,
    token: str | None,
    service,
):
    servidor = ServidorStatusAdministrativo(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token=token,
    )

    servidor.community_moderation_read_service = service

    servidor.iniciar()

    assert servidor._servidor is not None

    porta = int(servidor._servidor.server_address[1])

    return (
        servidor,
        f"http://127.0.0.1:{porta}",
    )


def test_8e9a_contract_boundary():
    data = _contract()

    assert data["stage"] == "8E9A-admin-moderation-read-api"

    assert data["status"] == "completed"

    assert data["transport"]["admin_token_env"] == "RADAR_ADMIN_TOKEN"

    assert data["transport"]["fail_closed_without_admin_token"] is True

    assert data["recovery"]["structural_patch_used"] is True


def test_8e9a_routes_are_get_only():
    routes = _contract()["routes"]

    assert [item["method"] for item in routes] == [
        "GET",
        "GET",
    ]

    assert [item["path"] for item in routes] == [
        "/moderation/reports",
        "/moderation/reports/{denuncia_id}",
    ]


def test_read_projection_paginates_pending(
    tmp_path: Path,
):
    db = _create_read_db(tmp_path)

    with sqlite3.connect(db) as conn:
        for index in range(3):
            conn.execute(
                """
                INSERT INTO
                    community_moderation_reports (
                        id,
                        chave_idempotencia,
                        reporter_conta_id,
                        target_type,
                        target_id,
                        motivo,
                        detalhes,
                        estado,
                        criado_em,
                        atualizado_em
                    )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
                """,
                (
                    f"rpt_{index}",
                    f"key_{index}",
                    "usr_test",
                    "community_discovery",
                    f"discovery_{index}",
                    "spam",
                    None,
                    "received",
                    ("2026-09-22T12:" f"0{index}:00+00:00"),
                    ("2026-09-22T12:" f"0{index}:00+00:00"),
                ),
            )

    service = CommunityModerationReadService(db)

    result = service.listar_pendentes(
        limite=1,
        offset=1,
    )

    assert result["limite"] == 1
    assert result["offset"] == 1
    assert result["quantidade"] == 1

    assert result["itens"][0]["id"] == "rpt_1"


def test_read_projection_caps_limit_and_validates_offset(
    tmp_path: Path,
):
    db = _create_read_db(tmp_path)

    service = CommunityModerationReadService(db)

    result = service.listar_pendentes(
        limite=999,
        offset=0,
    )

    assert result["limite"] == 100

    with pytest.raises(
        ValueError,
        match="offset",
    ):
        service.listar_pendentes(
            limite=10,
            offset=-1,
        )


def test_read_projection_returns_report_and_decisions(
    tmp_path: Path,
):
    db = _create_read_db(tmp_path)

    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            INSERT INTO
                community_moderation_reports (
                    id,
                    chave_idempotencia,
                    reporter_conta_id,
                    target_type,
                    target_id,
                    motivo,
                    detalhes,
                    estado,
                    criado_em,
                    atualizado_em
                )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            """,
            (
                "rpt_test",
                "key_report",
                "usr_test",
                "community_discovery",
                "discovery_test",
                "spam",
                "teste",
                "resolved",
                "2026-09-22T12:00:00+00:00",
                "2026-09-22T12:10:00+00:00",
            ),
        )

        conn.execute(
            """
            INSERT INTO
                community_moderation_decisions (
                    id,
                    chave_idempotencia,
                    denuncia_id,
                    moderator_actor_id,
                    resultado,
                    familia_abuso_confirmado,
                    justificativa,
                    ocorrido_em,
                    criado_em
                )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                "mod_test",
                "key_decision",
                "rpt_test",
                "radar-admin-control-plane-v1",
                "dismissed",
                None,
                "teste",
                "2026-09-22T12:10:00+00:00",
                "2026-09-22T12:10:01+00:00",
            ),
        )

    service = CommunityModerationReadService(db)

    result = service.obter_denuncia("rpt_test")

    assert result is not None

    assert result["denuncia"]["id"] == "rpt_test"

    assert result["decisoes"][0]["id"] == "mod_test"


def test_read_projection_connection_is_strict_read_only(
    tmp_path: Path,
):
    db = _create_read_db(tmp_path)

    service = CommunityModerationReadService(db)

    conn = service._conectar()

    try:
        assert int(conn.execute("PRAGMA query_only").fetchone()[0]) == 1

        with pytest.raises(sqlite3.OperationalError):
            conn.execute("""
                INSERT INTO
                    community_moderation_reports (
                        id
                    )
                VALUES (
                    'should_fail'
                )
                """)

    finally:
        conn.close()


def test_admin_http_lists_pending_with_valid_token():
    service = FakeModerationReadService()

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        status, body = _request_json(
            (f"{base}/moderation/reports" "?limite=20&offset=5"),
            token="admin-secret",
        )

        assert status == 200
        assert body["limite"] == 20
        assert body["offset"] == 5

        assert service.calls == [
            (
                "listar",
                20,
                5,
            )
        ]

    finally:
        server.encerrar()


def test_admin_http_returns_report_detail():
    service = FakeModerationReadService()

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        status, body = _request_json(
            (f"{base}/moderation/" "reports/rpt_test"),
            token="admin-secret",
        )

        assert status == 200

        assert body["denuncia"]["id"] == "rpt_test"

    finally:
        server.encerrar()


def test_admin_http_returns_404_for_unknown_report():
    service = FakeModerationReadService()

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        status, body = _request_json(
            (f"{base}/moderation/" "reports/rpt_missing"),
            token="admin-secret",
        )

        assert status == 404
        assert "erro" in body

    finally:
        server.encerrar()


def test_admin_http_rejects_wrong_token():
    service = FakeModerationReadService()

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        status, body = _request_json(
            f"{base}/moderation/reports",
            token="wrong-secret",
        )

        assert status == 401

        assert body == {"erro": "Nao autorizado."}

    finally:
        server.encerrar()


def test_admin_http_fails_closed_without_admin_token():
    service = FakeModerationReadService()

    server, base = _start_server(
        token="",
        service=service,
    )

    try:
        status, body = _request_json(f"{base}/moderation/reports")

        assert status == 503

        assert "RADAR_ADMIN_TOKEN" in str(body["erro"])

    finally:
        server.encerrar()


def test_admin_http_fails_closed_without_read_service_and_runtime_wires_it():
    server, base = _start_server(
        token="admin-secret",
        service=None,
    )

    try:
        status, body = _request_json(
            f"{base}/moderation/reports",
            token="admin-secret",
        )

        assert status == 503

        assert "read service" in str(body["erro"])

    finally:
        server.encerrar()

    runtime_source = RUNTIME.read_text(encoding="utf-8")

    assert "CommunityModerationReadService(" in runtime_source

    assert "community_moderation_read_service" in runtime_source

    assert "executar_reconciliation=False" in runtime_source

    server_source = SERVER_SOURCE.read_text(encoding="utf-8-sig")

    assert '"/moderation/reports"' in server_source

    write_repository_source = WRITE_REPOSITORY.read_text(encoding="utf-8")

    assert "somente_leitura" not in write_repository_source


def test_8e9a_closure_metadata():
    data = _contract()

    assert data["status"] == "completed"

    assert data["next_step"] == "8E9B-authoritative-admin-decision-api"

    validation = data["validation"]

    assert validation["baseline"] == "02b2f23"

    assert validation["structural_patch_strategy"] == "python-ast-semantic-line-insertion"

    assert validation["write_repository_modified"] is False

    assert validation["isolated_tests_passed_pre_closure"] == 12

    assert validation["stage_8e_tests_passed_pre_closure"] == 124

    assert validation["trust_moderation_tests_passed_pre_closure"] == 173

    assert validation["dedicated_read_projection"] is True

    assert validation["sqlite_mode_ro"] is True

    assert validation["query_only"] is True

    assert validation["accidental_write_blocked"] is True

    assert validation["admin_auth_env"] == "RADAR_ADMIN_TOKEN"

    assert validation["fail_closed_without_admin_token"] is True

    assert validation["runtime_restart"] is False

    assert validation["moderation_runtime_persistently_enabled"] is False

    assert validation["automatic_reconciliation_enabled"] is False

    assert validation["decision_write_api"] is False

    assert validation["public_report_api"] is False

    assert validation["live_database_write"] is False

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0
