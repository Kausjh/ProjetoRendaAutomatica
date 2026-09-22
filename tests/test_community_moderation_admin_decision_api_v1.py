from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from repositories.community_moderation_repository import (
    CommunityModerationRepository,
)
from services.community_moderation_authority import (
    CommunityModerationAuthorityV1,
)
from services.community_moderation_service import (
    CommunityModerationService,
)
from services.controle.servidor_status import (
    ServidorStatusAdministrativo,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_admin_decision_api_v1.json"

RUNTIME = ROOT / "runtime.py"

SERVER_SOURCE = ROOT / "services" / "controle" / "servidor_status.py"


class FakeBridge:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def processar_decisao(
        self,
        resultado,
    ):
        self.calls.append(resultado)

        return object()


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _core(
    tmp_path: Path,
    *,
    motivo: str = "spam",
):
    db = tmp_path / "moderation.sqlite3"

    with sqlite3.connect(db) as conn:
        conn.execute("""
            CREATE TABLE contas_usuario (
                id TEXT PRIMARY KEY
            )
            """)

        conn.execute("""
            CREATE TABLE community_discoveries (
                id TEXT PRIMARY KEY
            )
            """)

        conn.execute("""
            INSERT INTO contas_usuario(id)
            VALUES ('usr_test')
            """)

        conn.execute("""
            INSERT INTO community_discoveries(id)
            VALUES ('discovery_test')
            """)

    repository = CommunityModerationRepository(db)

    report = repository.registrar_denuncia(
        reporter_conta_id="usr_test",
        target_type="community_discovery",
        target_id="discovery_test",
        motivo=motivo,
        detalhes="teste 8E9B",
        agora=("2026-09-22T12:00:00+00:00"),
    ).denuncia

    authority = CommunityModerationAuthorityV1(
        token_administrativo=("admin-secret"),
    )

    bridge = FakeBridge()

    service = CommunityModerationService(
        repository=repository,
        authority=authority,
        trust_bridge=bridge,
    )

    return (
        db,
        repository,
        report,
        bridge,
        service,
    )


def _request_json(
    url: str,
    *,
    token: str | None,
    payload: object,
    idempotency_key: str | None,
    raw_body: bytes | None = None,
) -> tuple[
    int,
    dict[str, object],
]:
    headers: dict[str, str] = {
        "Content-Type": ("application/json"),
    }

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    data = raw_body if raw_body is not None else json.dumps(payload).encode("utf-8")

    request = Request(
        url,
        headers=headers,
        method="POST",
        data=data,
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

    servidor.community_moderation_decision_service = service

    servidor.iniciar()

    assert servidor._servidor is not None

    porta = int(servidor._servidor.server_address[1])

    return (
        servidor,
        f"http://127.0.0.1:{porta}",
    )


def _decision_url(
    base: str,
    report_id: str,
) -> str:
    return f"{base}/moderation/reports/" f"{report_id}/decision"


def _payload(
    *,
    resultado: str = "dismissed",
    ocorrido_em: str = ("2026-09-22T12:10:00+00:00"),
):
    return {
        "resultado": resultado,
        "justificativa": "teste",
        "ocorrido_em": ocorrido_em,
    }


def test_8e9b_contract_boundary():
    data = _contract()

    assert data["stage"] == "8E9B-authoritative-admin-decision-api"

    assert data["status"] == "completed"

    assert data["route"]["method"] == "POST"

    assert data["route"]["idempotency_header"] == "Idempotency-Key"

    assert data["runtime"]["inactive_runtime_fail_closed"] is True


def test_8e9b_contract_forbids_client_authority_fields():
    route = _contract()["route"]

    assert route["client_may_set_moderator_actor_id"] is False

    assert route["client_may_set_authority_origin"] is False

    assert route["client_may_set_trust_family"] is False

    assert route["accepted_body_fields"] == [
        "resultado",
        "justificativa",
        "ocorrido_em",
    ]


def test_runtime_wires_decision_service_only_from_active_components():
    source = RUNTIME.read_text(encoding="utf-8")

    assert "community_moderation_resultado" in source

    assert "community_moderation_resultado.ativo" in source

    assert ".componentes.moderation_service" in source.replace(
        "\n",
        "",
    ).replace(
        " ",
        "",
    ) or ("moderation_service" in source and "componentes" in source)

    assert "community_moderation_decision_service" in source

    assert "executar_reconciliation=False" in source


def test_admin_decision_http_fails_closed_without_admin_token(
    tmp_path: Path,
):
    _, _, report, _, service = _core(tmp_path)

    server, base = _start_server(
        token="",
        service=service,
    )

    try:
        status, body = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token=None,
            payload=_payload(),
            idempotency_key="action-1",
        )

        assert status == 503

        assert "RADAR_ADMIN_TOKEN" in str(body["erro"])

    finally:
        server.encerrar()


def test_admin_decision_http_rejects_wrong_token(
    tmp_path: Path,
):
    _, _, report, _, service = _core(tmp_path)

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        status, _ = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="wrong-secret",
            payload=_payload(),
            idempotency_key="action-1",
        )

        assert status == 401

    finally:
        server.encerrar()


def test_admin_decision_http_fails_closed_without_runtime_service():
    server, base = _start_server(
        token="admin-secret",
        service=None,
    )

    try:
        status, body = _request_json(
            _decision_url(
                base,
                "rpt_missing",
            ),
            token="admin-secret",
            payload=_payload(),
            idempotency_key="action-1",
        )

        assert status == 503

        assert "decision service" in str(body["erro"])

    finally:
        server.encerrar()


def test_admin_decision_http_rejects_invalid_json(
    tmp_path: Path,
):
    _, repository, report, _, service = _core(tmp_path)

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        status, _ = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload={},
            idempotency_key="action-1",
            raw_body=b"{invalid-json",
        )

        assert status == 400

        assert (
            repository.listar_decisoes(
                denuncia_id=report.id,
            )
            == []
        )

    finally:
        server.encerrar()


def test_admin_decision_http_rejects_client_authority_fields(
    tmp_path: Path,
):
    _, repository, report, _, service = _core(tmp_path)

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        payload = _payload()

        payload["moderator_actor_id"] = "client-controlled"

        payload["familia_abuso_confirmado"] = "fraude_confirmada"

        status, _ = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload=payload,
            idempotency_key="action-1",
        )

        assert status == 400

        assert (
            repository.listar_decisoes(
                denuncia_id=report.id,
            )
            == []
        )

    finally:
        server.encerrar()


def test_admin_decision_http_persists_authoritative_dismissal(
    tmp_path: Path,
):
    _, repository, report, bridge, service = _core(tmp_path)

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        status, body = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload=_payload(resultado="dismissed"),
            idempotency_key="action-dismiss",
        )

        assert status == 201

        assert body["criado"] is True

        decisao = body["decisao"]

        assert decisao["moderator_actor_id"] == (CommunityModerationAuthorityV1.ACTOR_ID)

        assert decisao["familia_abuso_confirmado"] is None

        persisted = repository.listar_decisoes(
            denuncia_id=report.id,
        )

        assert len(persisted) == 1

        assert persisted[0].moderator_actor_id == (CommunityModerationAuthorityV1.ACTOR_ID)

        assert bridge.calls == []

    finally:
        server.encerrar()


def test_confirmed_abuse_derives_family_and_calls_bridge(
    tmp_path: Path,
):
    _, repository, report, bridge, service = _core(
        tmp_path,
        motivo="spam",
    )

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        status, body = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload=_payload(resultado="confirmed_abuse"),
            idempotency_key="action-abuse",
        )

        assert status == 201

        assert body["decisao"]["familia_abuso_confirmado"] == "spam_confirmado"

        persisted = repository.listar_decisoes(
            denuncia_id=report.id,
        )

        assert len(persisted) == 1

        assert persisted[0].familia_abuso_confirmado == "spam_confirmado"

        assert len(bridge.calls) == 1

    finally:
        server.encerrar()


def test_admin_decision_http_exact_retry_is_idempotent(
    tmp_path: Path,
):
    _, repository, report, _, service = _core(tmp_path)

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        payload = _payload(resultado="keep_under_review")

        first_status, first_body = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload=payload,
            idempotency_key=("action-retry"),
        )

        second_status, second_body = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload=payload,
            idempotency_key=("action-retry"),
        )

        assert first_status == 201
        assert second_status == 200

        assert first_body["decisao"]["id"] == second_body["decisao"]["id"]

        assert second_body["criado"] is False

        assert (
            len(
                repository.listar_decisoes(
                    denuncia_id=report.id,
                )
            )
            == 1
        )

    finally:
        server.encerrar()


def test_admin_decision_http_idempotency_collision_is_conflict(
    tmp_path: Path,
):
    _, repository, report, _, service = _core(tmp_path)

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        first_status, _ = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload=_payload(resultado="keep_under_review"),
            idempotency_key="action-conflict",
        )

        second_status, _ = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload=_payload(resultado="dismissed"),
            idempotency_key="action-conflict",
        )

        assert first_status == 201
        assert second_status == 409

        assert (
            len(
                repository.listar_decisoes(
                    denuncia_id=report.id,
                )
            )
            == 1
        )

    finally:
        server.encerrar()


def test_admin_decision_http_missing_report_is_404(
    tmp_path: Path,
):
    _, _, _, _, service = _core(tmp_path)

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        status, _ = _request_json(
            _decision_url(
                base,
                "rpt_missing",
            ),
            token="admin-secret",
            payload=_payload(),
            idempotency_key="action-missing",
        )

        assert status == 404

    finally:
        server.encerrar()


def test_admin_decision_http_resolved_report_rejects_new_decision(
    tmp_path: Path,
):
    _, repository, report, _, service = _core(tmp_path)

    server, base = _start_server(
        token="admin-secret",
        service=service,
    )

    try:
        first_status, _ = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload=_payload(resultado="dismissed"),
            idempotency_key="action-final-1",
        )

        second_status, _ = _request_json(
            _decision_url(
                base,
                report.id,
            ),
            token="admin-secret",
            payload=_payload(
                resultado="dismissed",
                ocorrido_em=("2026-09-22T12:20:00+00:00"),
            ),
            idempotency_key="action-final-2",
        )

        assert first_status == 201
        assert second_status == 409

        assert (
            len(
                repository.listar_decisoes(
                    denuncia_id=report.id,
                )
            )
            == 1
        )

    finally:
        server.encerrar()


def test_8e9b_closure_metadata():
    data = _contract()

    assert data["status"] == "completed"

    assert data["next_step"] == "8E9C-auth-audit-rate-error-semantics"

    validation = data["validation"]

    assert validation["baseline"] == "76ea8d8"

    assert validation["audit_strategy"] == "ast-plus-behavioral-tests"

    assert validation["text_message_assertions"] is False

    assert validation["isolated_tests_passed_pre_closure"] == 14

    assert validation["stage_8e_tests_passed_pre_closure"] == 139

    assert validation["trust_moderation_tests_passed_pre_closure"] == 188

    assert validation["http_decision_service_call_validated"] is True

    assert validation["http_accepts_moderator_actor"] is False

    assert validation["http_accepts_authority_origin"] is False

    assert validation["http_accepts_trust_family"] is False

    assert validation["core_derives_moderator_actor"] is True

    assert validation["core_derives_trust_family"] is True

    assert validation["core_trust_bridge"] is True

    assert validation["runtime_service_only_when_active"] is True

    assert validation["runtime_inactive_fail_closed"] is True

    assert validation["persistent_runtime_flag_changed"] is False

    assert validation["automatic_reconciliation_enabled"] is False

    assert validation["runtime_restart"] is False

    assert validation["live_canary"] is False

    assert validation["live_database_write"] is False

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0

    assert data["http_semantics"]["full_error_semantics_deferred_to_8e9c"] is True
