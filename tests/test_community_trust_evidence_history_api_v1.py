from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from models.community_trust import (
    ResumoEvidenciaCommunityTrust,
)
from models.user_identity import (
    ContaUsuario,
)
from repositories.community_trust_read_repository import (
    CommunityTrustReadOnlyRepository,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.api_aplicacao.servidor import (
    ServidorApiAplicacao,
)
from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
)
from services.api_aplicacao.user_facing_trust import (
    UserFacingCommunityTrustController,
)
from services.community_trust_read_service import (
    CommunityTrustReadService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_trust_evidence_history_api_v1.json"


def _conta(
    conta_id: str = "usr_a",
    *,
    ativa: bool = True,
) -> ContaUsuario:
    return ContaUsuario(
        id=conta_id,
        email=(f"{conta_id}@example.com"),
        criado_em=("2026-09-23T12:00:00+00:00"),
        ativa=ativa,
    )


class FakeIdentityService:
    def __init__(
        self,
        conta: ContaUsuario,
    ) -> None:
        self.conta = conta

    def resolver_sessao(
        self,
        token: str,
    ) -> ContaUsuario | None:
        if token != "pra_usr_v1_valid":
            return None

        return self.conta


class SpyTrustReader:
    def __init__(
        self,
    ) -> None:
        self.calls: list[
            tuple[
                str,
                int,
                int,
            ]
        ] = []

    def obter_perfil(
        self,
        conta_id: str,
    ):
        raise AssertionError("obter_perfil nao deveria ser chamado.")

    def listar_evidencias_publicas(
        self,
        *,
        conta_id: str,
        limite: int,
        offset: int,
    ) -> list[ResumoEvidenciaCommunityTrust]:
        self.calls.append(
            (
                conta_id,
                limite,
                offset,
            )
        )

        return [
            ResumoEvidenciaCommunityTrust(
                tipo_evidencia=("community_discovery"),
                classificacao=("positive"),
                ocorrido_em=("2026-09-23T12:00:00+00:00"),
            )
        ]


def _sha256(
    path: Path,
) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _create_account(
    database: Path,
    *,
    conta_id: str,
) -> ContaUsuario:
    identities = UserIdentityRepository(database)

    return identities.criar_conta(
        conta_id=conta_id,
        email_normalizado=(f"{conta_id}@example.com"),
        email_exibicao=(f"{conta_id}@example.com"),
        senha_salt=(b"salt-" + conta_id.encode("utf-8")),
        senha_hash=(b"hash-" + conta_id.encode("utf-8")),
        criado_em=("2026-09-23T12:00:00+00:00"),
    )


def _seed_history(
    database: Path,
    *,
    conta_id: str = "usr_a",
    eventos: int = 3,
) -> tuple[
    ContaUsuario,
    CommunityTrustReadService,
]:
    account = _create_account(
        database,
        conta_id=conta_id,
    )

    writer = CommunityTrustRepository(database)

    classes = [
        "positive",
        "neutral",
        "negative",
    ]

    for index in range(eventos):
        classe = classes[index % len(classes)]

        writer.registrar_evidencia(
            conta_id=account.id,
            chave_idempotencia=(f"8f3:{conta_id}:{index}"),
            tipo_evidencia=(f"event_type_{index}"),
            classificacao=classe,
            origem="internal-test-origin",
            origem_id=(f"internal-source-{index}"),
            motivo=(f"internal-reason-{index}"),
            politica_versao=("internal-policy-v1"),
            metadados={
                "private_marker": f"secret-{index}",
            },
            ocorrido_em=("2026-09-23T" f"12:0{index}:00+00:00"),
        )

    reader = CommunityTrustReadOnlyRepository(database)

    return (
        account,
        CommunityTrustReadService(reader),
    )


def _start_server(
    read_service: CommunityTrustReadService | None,
    *,
    conta: ContaUsuario | None = None,
    infrastructure_token: str = "",
):
    server = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token=infrastructure_token,
        user_identity_service=(FakeIdentityService(conta or _conta())),  # type: ignore[arg-type]
        community_trust_read_service=(read_service),
    )

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
    user_session: str | None = ("pra_usr_v1_valid"),
    infrastructure_token: str | None = None,
):
    headers: dict[
        str,
        str,
    ] = {}

    if user_session is not None:
        headers["X-User-Session"] = user_session

    if infrastructure_token is not None:
        headers["Authorization"] = "Bearer " + infrastructure_token

    data = b"{}" if method == "POST" else None

    request = Request(
        url,
        method=method,
        headers=headers,
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


def test_8f3_contract_identity_tree_and_source():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8F3-trust-evidence-history-api"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "2a55c56"

    assert data["source_stage"]["8F2"] == "completed"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "completed",
        "8F3": "completed",
        "8F4": "public-app-trust-client",
        "8F5": "public-app-trust-surface",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    assert data["next_step"] == "8F4-public-app-trust-client"


def test_read_repository_empty_history(
    tmp_path: Path,
):
    database = tmp_path / "empty.sqlite3"

    account, service = _seed_history(
        database,
        eventos=0,
    )

    history = service.listar_evidencias(
        conta_id=account.id,
        limite=20,
        offset=0,
    )

    assert history.itens == ()

    assert history.limite == 20

    assert history.offset == 0


def test_read_repository_order_and_projection(
    tmp_path: Path,
):
    database = tmp_path / "order.sqlite3"

    account, service = _seed_history(
        database,
        eventos=3,
    )

    history = service.listar_evidencias(
        conta_id=account.id,
        limite=20,
        offset=0,
    )

    assert [item.tipo_evidencia for item in history.itens] == [
        "event_type_2",
        "event_type_1",
        "event_type_0",
    ]

    assert [item.classificacao for item in history.itens] == [
        "negative",
        "neutral",
        "positive",
    ]

    for item in history.itens:
        assert set(item.__dataclass_fields__) == {
            "tipo_evidencia",
            "classificacao",
            "ocorrido_em",
        }


def test_read_repository_pagination(
    tmp_path: Path,
):
    database = tmp_path / "pagination.sqlite3"

    account, service = _seed_history(
        database,
        eventos=3,
    )

    page = service.listar_evidencias(
        conta_id=account.id,
        limite=1,
        offset=1,
    )

    assert len(page.itens) == 1

    assert page.itens[0].tipo_evidencia == "event_type_1"


def test_read_repository_is_account_scoped(
    tmp_path: Path,
):
    database = tmp_path / "scope.sqlite3"

    account_a, service = _seed_history(
        database,
        conta_id="usr_a",
        eventos=1,
    )

    _seed_history(
        database,
        conta_id="usr_b",
        eventos=3,
    )

    history = service.listar_evidencias(
        conta_id=account_a.id,
        limite=100,
        offset=0,
    )

    assert len(history.itens) == 1

    assert history.itens[0].tipo_evidencia == "event_type_0"


def test_read_repository_does_not_mutate_database(
    tmp_path: Path,
):
    database = tmp_path / "hash.sqlite3"

    account, service = _seed_history(
        database,
        eventos=2,
    )

    before = _sha256(database)

    service.listar_evidencias(
        conta_id=account.id,
        limite=20,
        offset=0,
    )

    after = _sha256(database)

    assert before == after


def test_controller_rejects_invalid_pagination():
    reader = SpyTrustReader()

    controller = UserFacingCommunityTrustController(CommunityTrustReadService(reader))

    for limite, offset in (
        ("abc", "0"),
        ("0", "0"),
        ("101", "0"),
        ("20", "-1"),
    ):
        with pytest.raises(ErroHttpUserFacing) as captured:
            controller.listar_evidencias(
                _conta(),
                limite=limite,
                offset=offset,
            )

        assert captured.value.status == 400

        assert captured.value.codigo == "paginacao_trust_invalida"


def test_controller_projection_is_minimized():
    reader = SpyTrustReader()

    controller = UserFacingCommunityTrustController(CommunityTrustReadService(reader))

    status, body = controller.listar_evidencias(
        _conta(),
        limite="20",
        offset="0",
    )

    assert status == 200

    assert body == {
        "itens": [
            {
                "tipo_evidencia": "community_discovery",
                "classificacao": "positive",
                "ocorrido_em": "2026-09-23T12:00:00+00:00",
            }
        ],
        "limite": 20,
        "offset": 0,
        "quantidade": 1,
    }


def test_http_requires_user_session(
    tmp_path: Path,
):
    database = tmp_path / "http-auth.sqlite3"

    account, service = _seed_history(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, _ = _request(
            f"{base}/api/v1/me/trust/evidence",
            user_session=None,
        )

        assert status == 401

        assert body["erro"]["codigo"] == "sessao_usuario_obrigatoria"

    finally:
        server.encerrar()


def test_http_rejects_invalid_user_session(
    tmp_path: Path,
):
    database = tmp_path / "http-invalid.sqlite3"

    account, service = _seed_history(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, _ = _request(
            f"{base}/api/v1/me/trust/evidence",
            user_session=("pra_usr_v1_invalid"),
        )

        assert status == 401

        assert body["erro"]["codigo"] == "sessao_usuario_invalida"

    finally:
        server.encerrar()


def test_http_returns_authenticated_own_history(
    tmp_path: Path,
):
    database = tmp_path / "http-history.sqlite3"

    account, service = _seed_history(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, headers = _request(f"{base}/api/v1/me/trust/evidence")

        assert status == 200

        assert headers.get("Cache-Control") == "no-store"

        assert body["api_version"] == "v1"

        assert body["dados"]["quantidade"] == 3

        assert body["dados"]["itens"][0]["tipo_evidencia"] == "event_type_2"

    finally:
        server.encerrar()


def test_http_pagination(
    tmp_path: Path,
):
    database = tmp_path / "http-pagination.sqlite3"

    account, service = _seed_history(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, _ = _request(f"{base}/api/v1/me/trust/evidence" "?limite=1&offset=1")

        assert status == 200

        assert body["dados"]["limite"] == 1

        assert body["dados"]["offset"] == 1

        assert body["dados"]["quantidade"] == 1

        assert body["dados"]["itens"][0]["tipo_evidencia"] == "event_type_1"

    finally:
        server.encerrar()


def test_http_subject_is_server_derived():
    reader = SpyTrustReader()

    service = CommunityTrustReadService(reader)

    server, base = _start_server(
        service,
        conta=_conta("usr_session"),
    )

    try:
        status, _, _ = _request(f"{base}/api/v1/me/trust/evidence" "?conta_id=usr_other")

        assert status == 200

        assert reader.calls == [
            (
                "usr_session",
                20,
                0,
            )
        ]

    finally:
        server.encerrar()


def test_http_preserves_infrastructure_auth(
    tmp_path: Path,
):
    database = tmp_path / "http-infra.sqlite3"

    account, service = _seed_history(database)

    server, base = _start_server(
        service,
        conta=account,
        infrastructure_token=("infra-secret"),
    )

    try:
        status, body, _ = _request(f"{base}/api/v1/me/trust/evidence")

        assert status == 401

        assert body["erro"]["codigo"] == "infraestrutura_nao_autorizada"

        ok, _, _ = _request(
            f"{base}/api/v1/me/trust/evidence",
            infrastructure_token=("infra-secret"),
        )

        assert ok == 200

    finally:
        server.encerrar()


def test_http_projection_does_not_leak_internal_fields(
    tmp_path: Path,
):
    database = tmp_path / "http-private.sqlite3"

    account, service = _seed_history(
        database,
        eventos=1,
    )

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, _ = _request(f"{base}/api/v1/me/trust/evidence")

        assert status == 200

        rendered = json.dumps(
            body,
            ensure_ascii=False,
        )

        assert account.id not in rendered

        for private in (
            "conta_id",
            "chave_idempotencia",
            "origem",
            "origem_id",
            "motivo",
            "politica_versao",
            "metadados",
            "criado_em",
            "internal-test-origin",
            "internal-source",
            "internal-reason",
            "internal-policy-v1",
            "private_marker",
            "secret-0",
        ):
            assert private not in rendered

    finally:
        server.encerrar()


def test_http_unavailable_service_fails_closed():
    server, base = _start_server(
        None,
        conta=_conta(),
    )

    try:
        status, body, _ = _request(f"{base}/api/v1/me/trust/evidence")

        assert status == 503

        assert body["erro"]["codigo"] == "trust_comunitario_indisponivel"

    finally:
        server.encerrar()


def test_http_post_is_not_allowed(
    tmp_path: Path,
):
    database = tmp_path / "http-post.sqlite3"

    account, service = _seed_history(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, _, _ = _request(
            f"{base}/api/v1/me/trust/evidence",
            method="POST",
        )

        assert status == 405

    finally:
        server.encerrar()


def test_no_evidence_detail_endpoint(
    tmp_path: Path,
):
    database = tmp_path / "http-detail.sqlite3"

    account, service = _seed_history(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, _, _ = _request(f"{base}/api/v1/me/trust/evidence/" "internal-evidence-id")

        assert status == 404

    finally:
        server.encerrar()


def test_8f3_aegis_and_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    public = data["public_projection"]

    assert public["fields"] == [
        "tipo_evidencia",
        "classificacao",
        "ocorrido_em",
    ]

    for key in (
        "account_id_exposed",
        "evidence_id_exposed",
        "idempotency_key_exposed",
        "origin_exposed",
        "origin_id_exposed",
        "reason_exposed",
        "policy_version_exposed",
        "metadata_exposed",
        "created_at_exposed",
        "moderator_actor_exposed",
        "internal_policy_exposed",
    ):
        assert public[key] is False

    minimization = data["query_minimization"]

    assert minimization["selects_only_public_fields"] is True

    assert minimization["selected_columns"] == [
        "tipo_evidencia",
        "classificacao",
        "ocorrido_em",
    ]

    assert minimization["internal_id_used_only_for_stable_order"] is True

    assert minimization["loads_raw_metadata"] is False

    http = data["http"]

    assert http["self_only"] is True

    assert http["subject_from_authenticated_session"] is True

    assert http["detail_endpoint_added"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["query_level_data_minimization"] is True

    assert security["raw_evidence_object_loaded"] is False

    assert security["stable_internal_id_exposed"] is False

    assert security["sensitive_internal_context_exposed"] is False

    assert security["horizontal_idor_subject_parameter"] is False

    assert security["new_write_path"] is False

    assert security["persistent_attack_surface_increase"] is True

    assert security["existing_security_silently_weakened"] is False


def test_8f3_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8F4-public-app-trust-client"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "completed",
        "8F3": "completed",
        "8F4": "public-app-trust-client",
        "8F5": "public-app-trust-surface",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    validation = data["validation"]

    assert validation["initial_validation_harness_expected_cases"] == 17

    assert validation["actual_8f3_cases"] == 19

    assert validation["validation_harness_count_corrected"] is True

    assert validation["functional_failure_detected"] is False

    assert validation["tests_removed_to_match_count"] is False

    assert validation["tests_relaxed"] is False

    assert validation["isolated_8f3_cases_passed_pre_closure"] == 19

    assert validation["community_trust_test_files"] == 11

    assert validation["community_trust_cases_passed_pre_closure"] == 148

    assert validation["server_api_test_files"] == 18

    assert validation["server_api_broad_cases_passed_pre_closure"] == 259

    assert validation["community_moderation_cases_passed"] == 194

    assert validation["public_mobile_cases_passed"] == 61

    assert validation["backend_reporting_cases_passed"] == 70

    assert validation["live_query_only"] is True

    assert validation["live_integrity_check"] == "ok"

    assert validation["live_foreign_key_errors"] == 0

    assert validation["live_schema_version"] == 43

    assert validation["live_moderation_report_rows"] == 0

    assert validation["live_moderation_decision_rows"] == 0

    assert validation["live_trust_evidence_total"] == 2

    assert validation["live_trust_profile_total"] == 1

    assert validation["live_public_history_rows"] == 2

    assert validation["live_public_history_fields_only"] is True

    assert validation["live_internal_account_id_printed"] is False

    assert validation["live_database_sha256_unchanged"] is True

    assert validation["live_database_write"] is False

    assert validation["live_schema_write"] is False

    assert validation["query_level_data_minimization"] is True

    assert validation["detail_endpoint_added"] is False

    assert validation["public_app_changed"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["validation_completed"] is True

    assert security["authenticated_self_only_boundary_validated"] is True

    assert security["query_level_minimization_validated"] is True

    assert security["strict_read_only_repository_validated"] is True

    assert security["bounded_pagination_validated"] is True

    assert security["no_detail_endpoint_validated"] is True

    assert security["internal_context_non_exposure_validated"] is True

    assert security["live_state_preserved"] is True

    assert security["security_regression_detected"] is False

    assert security["existing_security_silently_weakened"] is False

    closure = data["closure"]

    assert closure["expected_isolated_8f3_cases_after_closure"] == 20

    assert closure["expected_community_trust_cases_after_closure"] == 149

    assert closure["expected_community_trust_test_files_after_closure"] == 11

    assert closure["expected_server_api_broad_cases_after_closure"] == 260

    assert closure["expected_server_api_test_files_after_closure"] == 18

    assert closure["expected_community_moderation_cases_after_closure"] == 194

    assert closure["expected_public_mobile_cases_after_closure"] == 61

    assert closure["expected_backend_reporting_cases_after_closure"] == 70

    assert closure["8F1"] == "completed"

    assert closure["8F2"] == "completed"

    assert closure["8F3"] == "completed"

    assert closure["8F4"] == "pending"
