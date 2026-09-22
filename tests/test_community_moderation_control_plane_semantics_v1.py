from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.community_moderation_control_plane_policy import (
    CommunityModerationControlPlanePolicy,
)
from services.controle.controlador import (
    ControladorAdministrativo,
)
from services.controle.servidor_status import (
    ServidorStatusAdministrativo,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_control_plane_semantics_v1.json"

RUNTIME = ROOT / "runtime.py"

SERVER_SOURCE = ROOT / "services" / "controle" / "servidor_status.py"


class FakeClock:
    def __init__(
        self,
    ) -> None:
        self.value = 1000.0

    def __call__(
        self,
    ) -> float:
        return self.value

    def advance(
        self,
        seconds: float,
    ) -> None:
        self.value += float(seconds)


class FakeReadService:
    def __init__(
        self,
    ) -> None:
        self.list_calls = 0
        self.detail_calls = 0

    def listar_pendentes(
        self,
        *,
        limite: object,
        offset: object,
    ) -> dict[str, object]:
        self.list_calls += 1

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
        self.detail_calls += 1

        if str(denuncia_id) != "rpt_test":
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


@dataclass(
    frozen=True,
)
class FakeDecision:
    id: str = "mod_test"
    moderator_actor_id: str = "radar-admin-control-plane-v1"
    resultado: str = "dismissed"


@dataclass(
    frozen=True,
)
class FakeReport:
    id: str = "rpt_test"
    estado: str = "resolved"


@dataclass(
    frozen=True,
)
class FakeDecisionResult:
    decisao: FakeDecision
    denuncia: FakeReport
    criado: bool


class FakeDecisionService:
    def __init__(
        self,
    ) -> None:
        self.calls = 0

    def registrar_decisao_autorizada(
        self,
        **kwargs,
    ):
        self.calls += 1

        return FakeDecisionResult(
            decisao=FakeDecision(),
            denuncia=FakeReport(),
            criado=True,
        )


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _audit_collector():
    events: list[dict[str, object]] = []

    def sink(
        **kwargs,
    ):
        events.append(dict(kwargs))

        return True

    return (
        events,
        sink,
    )


def _policy(
    *,
    read_limit: int = 120,
    decision_limit: int = 30,
    clock=None,
    audit_sink=None,
):
    return CommunityModerationControlPlanePolicy(
        read_limit=read_limit,
        decision_limit=decision_limit,
        clock=clock,
        audit_sink=audit_sink,
    )


def _start_server(
    *,
    token: str | None,
    policy,
    read_service=None,
    decision_service=None,
):
    server = ServidorStatusAdministrativo(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token=token,
    )

    server.community_moderation_control_plane_policy = policy

    server.community_moderation_read_service = read_service

    server.community_moderation_decision_service = decision_service

    server.iniciar()

    assert server._servidor is not None

    porta = int(server._servidor.server_address[1])

    return (
        server,
        f"http://127.0.0.1:{porta}",
    )


def _request(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    request_id: str | None = None,
    idempotency_key: str | None = None,
    payload: object | None = None,
):
    headers: dict[str, str] = {}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    if request_id is not None:
        headers["X-Request-Id"] = request_id

    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    data = None

    if method == "POST":
        headers["Content-Type"] = "application/json"

        data = json.dumps(payload if payload is not None else {}).encode("utf-8")

    request = Request(
        url,
        headers=headers,
        method=method,
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
                dict(response.headers.items()),
            )

    except HTTPError as error:
        return (
            error.code,
            json.loads(error.read().decode("utf-8")),
            dict(error.headers.items()),
        )


def _decision_url(
    base: str,
) -> str:
    return f"{base}/moderation/" "reports/rpt_test/decision"


def _decision_payload():
    return {
        "resultado": "dismissed",
        "justificativa": "teste",
        "ocorrido_em": ("2026-09-22T12:10:00+00:00"),
    }


def test_8e9c_contract_boundary():
    data = _contract()

    assert data["stage"] == "8E9C-auth-audit-rate-error-semantics"

    assert data["status"] == "completed"

    assert data["recovery"]["clean_reapply"] is True

    assert data["auth"]["rate_limit_before_auth"] is True

    assert data["audit"]["authorization_token_recorded"] is False

    assert data["errors"]["body_backward_compatible"] is True


def test_policy_request_id_normalization():
    policy = _policy()

    assert policy.normalizar_request_id("req-ABC_123:xyz") == "req-ABC_123:xyz"

    generated = policy.normalizar_request_id("invalid request id com espaco")

    assert generated
    assert " " not in generated
    assert len(generated) <= 120


def test_policy_read_rate_limit():
    clock = FakeClock()

    policy = _policy(
        read_limit=2,
        clock=clock,
    )

    first = policy.consumir_rate_limit(
        escopo="read",
        chave="127.0.0.1",
    )

    second = policy.consumir_rate_limit(
        escopo="read",
        chave="127.0.0.1",
    )

    third = policy.consumir_rate_limit(
        escopo="read",
        chave="127.0.0.1",
    )

    assert first.permitido is True
    assert first.restantes == 1

    assert second.permitido is True
    assert second.restantes == 0

    assert third.permitido is False
    assert third.restantes == 0
    assert third.retry_after_segundos == 60

    clock.advance(61)

    recovered = policy.consumir_rate_limit(
        escopo="read",
        chave="127.0.0.1",
    )

    assert recovered.permitido is True


def test_policy_read_and_decision_buckets_are_separate():
    clock = FakeClock()

    policy = _policy(
        read_limit=1,
        decision_limit=1,
        clock=clock,
    )

    assert (
        policy.consumir_rate_limit(
            escopo="read",
            chave="client",
        ).permitido
        is True
    )

    assert (
        policy.consumir_rate_limit(
            escopo="decision",
            chave="client",
        ).permitido
        is True
    )

    assert (
        policy.consumir_rate_limit(
            escopo="read",
            chave="client",
        ).permitido
        is False
    )

    assert (
        policy.consumir_rate_limit(
            escopo="decision",
            chave="client",
        ).permitido
        is False
    )


def test_policy_error_code_semantics():
    policy = _policy()

    expected = {
        400: "moderation_bad_request",
        401: "moderation_unauthorized",
        404: "moderation_not_found",
        409: "moderation_conflict",
        429: "moderation_rate_limited",
        500: "moderation_internal_error",
        503: "moderation_unavailable",
    }

    assert {status: policy.codigo_erro(status) for status in expected} == expected

    assert policy.codigo_erro(200) is None


def test_policy_audit_result_semantics():
    policy = _policy()

    assert policy.resultado_auditoria(200) == "sucesso"

    assert policy.resultado_auditoria(401) == "negado_auth"

    assert policy.resultado_auditoria(409) == "conflito"

    assert policy.resultado_auditoria(429) == "rate_limited"

    assert policy.resultado_auditoria(503) == "indisponivel"


def test_policy_audit_sink():
    events, sink = _audit_collector()

    policy = _policy(audit_sink=sink)

    ok = policy.auditar(
        acao="moderation.admin.read.list",
        alvo="queue",
        detalhes={
            "request_id": "req-1",
            "status_code": 200,
        },
        dispositivo="test-device",
        resultado="sucesso",
    )

    assert ok is True
    assert len(events) == 1

    serialized = json.dumps(
        events[0],
        ensure_ascii=False,
    )

    assert "RADAR_ADMIN_TOKEN" not in serialized

    assert "Bearer " not in serialized


def test_controller_public_audit_bridge_persists(
    tmp_path: Path,
):
    repository = ControleAdministrativoRepository(str(tmp_path / "controle.sqlite3"))

    controller = ControladorAdministrativo(
        orquestrador=object(),  # type: ignore[arg-type]
        fila=object(),  # type: ignore[arg-type]
        verificador_chrome=lambda: True,
        repositorio_admin=repository,
    )

    result = controller.auditar_community_moderation_control_plane(
        acao=("moderation.admin.read.list"),
        alvo="queue",
        detalhes={
            "request_id": "req-persist",
            "status_code": 200,
        },
        dispositivo="device",
        resultado="sucesso",
    )

    assert result is True

    items = repository.listar_auditoria(limite=10)

    assert len(items) == 1

    assert items[0]["acao"] == "moderation.admin.read.list"

    assert items[0]["detalhes"]["request_id"] == "req-persist"


def test_get_invalid_auth_has_correlation_error_code_and_audit():
    events, sink = _audit_collector()

    server, base = _start_server(
        token="admin-secret",
        policy=_policy(audit_sink=sink),
        read_service=FakeReadService(),
    )

    try:
        status, body, headers = _request(
            f"{base}/moderation/reports",
            token="wrong-secret",
            request_id="req-auth",
        )

        assert status == 401

        assert body == {"erro": "Nao autorizado."}

        assert headers["X-Request-Id"] == "req-auth"

        assert headers["X-Moderation-Error-Code"] == "moderation_unauthorized"

        assert headers["X-Moderation-Audit"] == "persisted"

        assert len(events) == 1

        assert events[0]["resultado"] == "negado_auth"

    finally:
        server.encerrar()


def test_get_without_configured_token_is_503_with_error_code():
    events, sink = _audit_collector()

    server, base = _start_server(
        token="",
        policy=_policy(audit_sink=sink),
        read_service=FakeReadService(),
    )

    try:
        status, _, headers = _request(
            f"{base}/moderation/reports",
            request_id="req-no-token",
        )

        assert status == 503

        assert headers["X-Moderation-Error-Code"] == "moderation_unavailable"

        assert len(events) == 1

        assert events[0]["resultado"] == "indisponivel"

    finally:
        server.encerrar()


def test_get_rate_limit_returns_429_and_retry_after():
    events, sink = _audit_collector()

    read_service = FakeReadService()

    server, base = _start_server(
        token="admin-secret",
        policy=_policy(
            read_limit=1,
            audit_sink=sink,
        ),
        read_service=read_service,
    )

    try:
        first, _, _ = _request(
            f"{base}/moderation/reports",
            token="admin-secret",
        )

        second, body, headers = _request(
            f"{base}/moderation/reports",
            token="admin-secret",
        )

        assert first == 200
        assert second == 429

        assert "Limite" in str(body["erro"])

        assert headers["Retry-After"] == "60"

        assert headers["X-RateLimit-Limit"] == "1"

        assert headers["X-RateLimit-Remaining"] == "0"

        assert headers["X-Moderation-Error-Code"] == "moderation_rate_limited"

        assert read_service.list_calls == 1

        assert events[-1]["resultado"] == "rate_limited"

    finally:
        server.encerrar()


def test_get_list_success_is_audited():
    events, sink = _audit_collector()

    server, base = _start_server(
        token="admin-secret",
        policy=_policy(audit_sink=sink),
        read_service=FakeReadService(),
    )

    try:
        status, _, headers = _request(
            f"{base}/moderation/reports",
            token="admin-secret",
            request_id="req-list",
        )

        assert status == 200

        assert headers["X-Request-Id"] == "req-list"

        assert headers["Cache-Control"] == "no-store"

        assert len(events) == 1

        assert events[0]["acao"] == "moderation.admin.read.list"

        assert events[0]["alvo"] == "queue"

        assert events[0]["resultado"] == "sucesso"

    finally:
        server.encerrar()


def test_get_detail_success_audits_report_target():
    events, sink = _audit_collector()

    server, base = _start_server(
        token="admin-secret",
        policy=_policy(audit_sink=sink),
        read_service=FakeReadService(),
    )

    try:
        status, body, _ = _request(
            (f"{base}/moderation/" "reports/rpt_test"),
            token="admin-secret",
        )

        assert status == 200

        assert body["denuncia"]["id"] == "rpt_test"

        assert events[0]["acao"] == "moderation.admin.read.detail"

        assert events[0]["alvo"] == "rpt_test"

    finally:
        server.encerrar()


def test_post_invalid_auth_is_audited_without_service_call():
    events, sink = _audit_collector()

    service = FakeDecisionService()

    server, base = _start_server(
        token="admin-secret",
        policy=_policy(audit_sink=sink),
        decision_service=service,
    )

    try:
        status, _, headers = _request(
            _decision_url(base),
            method="POST",
            token="wrong-secret",
            idempotency_key="action-1",
            payload=_decision_payload(),
        )

        assert status == 401

        assert service.calls == 0

        assert headers["X-Moderation-Error-Code"] == "moderation_unauthorized"

        assert events[0]["acao"] == "moderation.admin.decision"

        assert events[0]["resultado"] == "negado_auth"

    finally:
        server.encerrar()


def test_post_rate_limit_blocks_second_core_call():
    events, sink = _audit_collector()

    service = FakeDecisionService()

    server, base = _start_server(
        token="admin-secret",
        policy=_policy(
            decision_limit=1,
            audit_sink=sink,
        ),
        decision_service=service,
    )

    try:
        first, _, _ = _request(
            _decision_url(base),
            method="POST",
            token="admin-secret",
            idempotency_key="action-1",
            payload=_decision_payload(),
        )

        second, _, headers = _request(
            _decision_url(base),
            method="POST",
            token="admin-secret",
            idempotency_key="action-2",
            payload=_decision_payload(),
        )

        assert first == 201
        assert second == 429

        assert service.calls == 1

        assert headers["X-Moderation-Error-Code"] == "moderation_rate_limited"

        assert events[-1]["resultado"] == "rate_limited"

    finally:
        server.encerrar()


def test_post_missing_idempotency_has_final_error_semantics():
    events, sink = _audit_collector()

    service = FakeDecisionService()

    server, base = _start_server(
        token="admin-secret",
        policy=_policy(audit_sink=sink),
        decision_service=service,
    )

    try:
        status, body, headers = _request(
            _decision_url(base),
            method="POST",
            token="admin-secret",
            payload=_decision_payload(),
        )

        assert status == 400

        assert body["erro"] == "Idempotency-Key e obrigatorio."

        assert headers["X-Moderation-Error-Code"] == "moderation_bad_request"

        assert service.calls == 0

        assert events[0]["detalhes"]["idempotency_key_present"] is False

    finally:
        server.encerrar()


def test_post_success_has_rate_correlation_and_audit():
    events, sink = _audit_collector()

    service = FakeDecisionService()

    server, base = _start_server(
        token="admin-secret",
        policy=_policy(
            decision_limit=3,
            audit_sink=sink,
        ),
        decision_service=service,
    )

    try:
        status, body, headers = _request(
            _decision_url(base),
            method="POST",
            token="admin-secret",
            request_id="req-decision",
            idempotency_key="action-ok",
            payload=_decision_payload(),
        )

        assert status == 201

        assert body["decisao"]["id"] == "mod_test"

        assert headers["X-Request-Id"] == "req-decision"

        assert headers["X-RateLimit-Limit"] == "3"

        assert headers["X-RateLimit-Remaining"] == "2"

        assert headers["X-Moderation-Audit"] == "persisted"

        assert "X-Moderation-Error-Code" not in headers

        assert service.calls == 1
        assert len(events) == 1

        serialized = json.dumps(
            events[0],
            ensure_ascii=False,
        )

        assert "admin-secret" not in serialized

        assert "justificativa" not in serialized

        assert "Authorization" not in serialized

    finally:
        server.encerrar()


def test_audit_failure_does_not_change_http_success():
    def failing_sink(
        **kwargs,
    ):
        raise RuntimeError("audit unavailable")

    service = FakeDecisionService()

    server, base = _start_server(
        token="admin-secret",
        policy=_policy(audit_sink=failing_sink),
        decision_service=service,
    )

    try:
        status, body, headers = _request(
            _decision_url(base),
            method="POST",
            token="admin-secret",
            idempotency_key=("action-audit-fail"),
            payload=_decision_payload(),
        )

        assert status == 201

        assert body["decisao"]["id"] == "mod_test"

        assert headers["X-Moderation-Audit"] == "unavailable"

        assert service.calls == 1

    finally:
        server.encerrar()


def test_error_body_backward_compatibility():
    server, base = _start_server(
        token="admin-secret",
        policy=_policy(),
        read_service=FakeReadService(),
    )

    try:
        status, body, _ = _request(
            f"{base}/moderation/reports",
            token="wrong-secret",
        )

        assert status == 401

        assert body == {"erro": "Nao autorizado."}

    finally:
        server.encerrar()


def test_runtime_wires_control_plane_policy_without_enabling_moderation():
    runtime_source = RUNTIME.read_text(encoding="utf-8")

    assert "CommunityModerationControlPlanePolicy" in runtime_source

    assert "community_moderation_control_plane_policy" in runtime_source

    assert "auditar_community_moderation_control_plane" in runtime_source

    assert "executar_reconciliation=False" in runtime_source

    server_source = SERVER_SOURCE.read_text(encoding="utf-8-sig")

    assert "X-Moderation-Error-Code" in server_source

    assert "X-Request-Id" in server_source

    assert "X-RateLimit-Limit" in server_source

    assert "X-Moderation-Audit" in server_source


def test_8e9c_final_closure_metadata():
    data = _contract()

    assert data["status"] == "completed"

    assert data["stage_8e9_status"] == "completed"

    assert data["next_step"] == "8E10A-authenticated-report-creation"

    validation = data["validation"]

    assert validation["baseline"] == "7a1a5cb"

    assert validation["test_function_count_pre_closure"] == 20

    assert validation["isolated_tests_passed_pre_closure"] == 20

    assert validation["stage_8e_tests_passed_pre_closure"] == 160

    assert validation["trust_moderation_tests_passed_pre_closure"] == 209

    assert validation["admin_server_tests_passed_pre_closure"] == 95

    assert validation["auth_constant_time_compare_preserved"] is True

    assert validation["rate_limit_before_auth"] is True

    assert validation["read_rate_limit_per_60s_per_ip"] == 120

    assert validation["decision_rate_limit_per_60s_per_ip"] == 30

    assert validation["rate_limit_status"] == 429

    assert validation["audit_authorization_token"] is False

    assert validation["audit_request_body"] is False

    assert validation["audit_justification"] is False

    assert validation["audit_failure_rolls_back_domain_result"] is False

    assert validation["error_body_backward_compatible"] is True

    assert validation["moderation_runtime_flag_enabled"] is False

    assert validation["automatic_reconciliation_enabled"] is False

    assert validation["runtime_restart"] is False

    assert validation["live_canary"] is False

    assert validation["live_moderation_domain_write"] is False

    assert validation["live_trust_write"] is False

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0
