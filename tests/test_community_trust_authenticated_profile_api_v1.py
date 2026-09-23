from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from models.community_trust import (
    PerfilCommunityTrust,
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

CONTRACT = ROOT / "contracts" / "community_trust_authenticated_profile_api_v1.json"


def _conta(
    conta_id: str = "usr_a",
    *,
    ativa: bool = True,
) -> ContaUsuario:
    return ContaUsuario(
        id=conta_id,
        email=f"{conta_id}@example.com",
        criado_em=("2026-09-22T12:00:00+00:00"),
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


class SpyProfileReader:
    def __init__(
        self,
        profiles: dict[
            str,
            PerfilCommunityTrust,
        ],
    ) -> None:
        self.profiles = dict(profiles)

        self.calls: list[str] = []

    def obter_perfil(
        self,
        conta_id: str,
    ) -> PerfilCommunityTrust:
        self.calls.append(conta_id)

        profile = self.profiles.get(conta_id)

        if profile is not None:
            return profile

        return PerfilCommunityTrust(
            conta_id=conta_id,
            evidencias_total=0,
            positivas_total=0,
            negativas_total=0,
            neutras_total=0,
            atualizado_em=None,
        )


def _sha256(
    path: Path,
) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _create_account(
    database: Path,
    *,
    conta_id: str = "usr_a",
) -> ContaUsuario:
    identities = UserIdentityRepository(database)

    return identities.criar_conta(
        conta_id=conta_id,
        email_normalizado=(f"{conta_id}@example.com"),
        email_exibicao=(f"{conta_id}@example.com"),
        senha_salt=(b"salt" + conta_id.encode("utf-8")),
        senha_hash=(b"hash" + conta_id.encode("utf-8")),
        criado_em=("2026-09-22T12:00:00+00:00"),
    )


def _seed_profile(
    database: Path,
    *,
    conta_id: str = "usr_a",
) -> tuple[
    ContaUsuario,
    CommunityTrustReadService,
]:
    account = _create_account(
        database,
        conta_id=conta_id,
    )

    writer = CommunityTrustRepository(database)

    writer.registrar_evidencia(
        conta_id=account.id,
        chave_idempotencia=("8f2-positive" + conta_id),
        tipo_evidencia=("8f2_test_positive"),
        classificacao="positive",
        origem="test",
        origem_id=("8f2-positive-origin" + conta_id),
        motivo="test",
        politica_versao="test-v1",
        metadados={
            "private_marker": "must-not-leak",
        },
        ocorrido_em=("2026-09-22T12:10:00+00:00"),
    )

    writer.registrar_evidencia(
        conta_id=account.id,
        chave_idempotencia=("8f2-negative" + conta_id),
        tipo_evidencia=("8f2_test_negative"),
        classificacao="negative",
        origem="test",
        origem_id=("8f2-negative-origin" + conta_id),
        motivo="test",
        politica_versao="test-v1",
        metadados={
            "private_marker": "must-not-leak",
        },
        ocorrido_em=("2026-09-22T12:11:00+00:00"),
    )

    reader = CommunityTrustReadOnlyRepository(database)

    return (
        account,
        CommunityTrustReadService(reader),
    )


def _zero_profile(
    database: Path,
    *,
    conta_id: str = "usr_zero",
) -> tuple[
    ContaUsuario,
    CommunityTrustReadService,
]:
    account = _create_account(
        database,
        conta_id=conta_id,
    )

    CommunityTrustRepository(database)

    return (
        account,
        CommunityTrustReadService(CommunityTrustReadOnlyRepository(database)),
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


def test_8f2_contract_identity_tree_and_source():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8F2-authenticated-trust-profile-api"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "5775f6c"

    assert data["source_stage"]["8F1"] == "completed"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "completed",
        "8F3": "trust-evidence-history-api",
        "8F4": "public-app-trust-client",
        "8F5": "public-app-trust-surface",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    assert data["next_step"] == "8F3-trust-evidence-history-api"


def test_read_only_repository_zero_state(
    tmp_path: Path,
):
    database = tmp_path / "trust-zero.sqlite3"

    account, service = _zero_profile(database)

    profile = service.obter(account.id).perfil

    assert profile.conta_id == account.id

    assert profile.evidencias_total == 0

    assert profile.positivas_total == 0

    assert profile.negativas_total == 0

    assert profile.neutras_total == 0

    assert profile.atualizado_em is None


def test_read_only_repository_reads_materialized_profile(
    tmp_path: Path,
):
    database = tmp_path / "trust-profile.sqlite3"

    account, service = _seed_profile(database)

    profile = service.obter(account.id).perfil

    assert profile.evidencias_total == 2

    assert profile.positivas_total == 1

    assert profile.negativas_total == 1

    assert profile.neutras_total == 0


def test_read_only_repository_does_not_mutate_database(
    tmp_path: Path,
):
    database = tmp_path / "trust-hash.sqlite3"

    account, service = _seed_profile(database)

    before = _sha256(database)

    service.obter(account.id)

    after = _sha256(database)

    assert before == after


def test_missing_trust_schema_fails_closed():
    database = ROOT / "logs" / "pytest-temp" / "8f2-missing-schema.sqlite3"

    database.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if database.exists():
        database.unlink()

    try:
        setup_connection = sqlite3.connect(database)
        setup_connection.close()

        controller = UserFacingCommunityTrustController(
            CommunityTrustReadService(CommunityTrustReadOnlyRepository(database))
        )

        with pytest.raises(ErroHttpUserFacing) as captured:
            controller.obter(_conta())

        assert captured.value.status == 503

        assert captured.value.codigo == "trust_comunitario_indisponivel"

    finally:
        if database.exists():
            database.unlink()


def test_http_requires_user_session(
    tmp_path: Path,
):
    database = tmp_path / "trust-http-auth.sqlite3"

    account, service = _seed_profile(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, _ = _request(
            f"{base}/api/v1/me/trust",
            user_session=None,
        )

        assert status == 401

        assert body["erro"]["codigo"] == "sessao_usuario_obrigatoria"

    finally:
        server.encerrar()


def test_http_rejects_invalid_user_session(
    tmp_path: Path,
):
    database = tmp_path / "trust-http-invalid.sqlite3"

    account, service = _seed_profile(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, _ = _request(
            f"{base}/api/v1/me/trust",
            user_session=("pra_usr_v1_invalid"),
        )

        assert status == 401

        assert body["erro"]["codigo"] == "sessao_usuario_invalida"

    finally:
        server.encerrar()


def test_http_returns_authenticated_own_profile(
    tmp_path: Path,
):
    database = tmp_path / "trust-http-profile.sqlite3"

    account, service = _seed_profile(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, headers = _request(f"{base}/api/v1/me/trust")

        assert status == 200

        assert headers.get("Cache-Control") == "no-store"

        assert body["api_version"] == "v1"

        assert body["dados"] == {
            "perfil": {
                "evidencias_total": 2,
                "positivas_total": 1,
                "negativas_total": 1,
                "neutras_total": 0,
                "atualizado_em": body["dados"]["perfil"]["atualizado_em"],
            },
            "modelo": {
                "versao": 1,
                "score_numerico_definido": False,
            },
        }

    finally:
        server.encerrar()


def test_http_zero_state(
    tmp_path: Path,
):
    database = tmp_path / "trust-http-zero.sqlite3"

    account, service = _zero_profile(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, _ = _request(f"{base}/api/v1/me/trust")

        assert status == 200

        assert body["dados"]["perfil"] == {
            "evidencias_total": 0,
            "positivas_total": 0,
            "negativas_total": 0,
            "neutras_total": 0,
            "atualizado_em": None,
        }

    finally:
        server.encerrar()


def test_http_preserves_infrastructure_auth(
    tmp_path: Path,
):
    database = tmp_path / "trust-http-infra.sqlite3"

    account, service = _seed_profile(database)

    server, base = _start_server(
        service,
        conta=account,
        infrastructure_token=("infra-secret"),
    )

    try:
        status, body, _ = _request(f"{base}/api/v1/me/trust")

        assert status == 401

        assert body["erro"]["codigo"] == "infraestrutura_nao_autorizada"

        ok, _, _ = _request(
            f"{base}/api/v1/me/trust",
            infrastructure_token=("infra-secret"),
        )

        assert ok == 200

    finally:
        server.encerrar()


def test_http_projection_does_not_leak_internal_fields(
    tmp_path: Path,
):
    database = tmp_path / "trust-http-private.sqlite3"

    account, service = _seed_profile(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, body, _ = _request(f"{base}/api/v1/me/trust")

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
            "metadados",
            "politica_versao",
            "moderator_actor_id",
            "justificativa",
            "private_marker",
            "trust_score",
            "pontuacao",
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
        status, body, _ = _request(f"{base}/api/v1/me/trust")

        assert status == 503

        assert body["erro"]["codigo"] == "trust_comunitario_indisponivel"

    finally:
        server.encerrar()


def test_http_post_is_not_allowed(
    tmp_path: Path,
):
    database = tmp_path / "trust-http-post.sqlite3"

    account, service = _seed_profile(database)

    server, base = _start_server(
        service,
        conta=account,
    )

    try:
        status, _, _ = _request(
            f"{base}/api/v1/me/trust",
            method="POST",
        )

        assert status == 405

    finally:
        server.encerrar()


def test_http_subject_is_server_derived_from_session():
    reader = SpyProfileReader(
        {
            "usr_a": PerfilCommunityTrust(
                conta_id="usr_a",
                evidencias_total=1,
                positivas_total=1,
                negativas_total=0,
                neutras_total=0,
                atualizado_em=("2026-09-22T12:00:00+00:00"),
            ),
            "usr_other": PerfilCommunityTrust(
                conta_id="usr_other",
                evidencias_total=99,
                positivas_total=0,
                negativas_total=99,
                neutras_total=0,
                atualizado_em=("2026-09-22T12:00:00+00:00"),
            ),
        }
    )

    service = CommunityTrustReadService(reader)

    server, base = _start_server(
        service,
        conta=_conta("usr_a"),
    )

    try:
        status, body, _ = _request(f"{base}/api/v1/me/trust" "?conta_id=usr_other")

        assert status == 200

        assert reader.calls == ["usr_a"]

        assert body["dados"]["perfil"]["evidencias_total"] == 1

        assert body["dados"]["perfil"]["negativas_total"] == 0

    finally:
        server.encerrar()


def test_runtime_wiring_uses_strict_read_only_repository():
    runtime = (ROOT / "runtime.py").read_text(encoding="utf-8")

    assert "CommunityTrustReadOnlyRepository" in runtime

    assert "community_trust_read_repository = " "CommunityTrustReadOnlyRepository(" in runtime

    assert "community_trust_read_service = " "CommunityTrustReadService(" in runtime

    assert "community_trust_read_service=" "community_trust_read_service" in runtime


def test_8f2_aegis_and_route_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    http = data["http"]

    assert http["method"] == "GET"

    assert http["path"] == "/api/v1/me/trust"

    assert http["authenticated"] is True

    assert http["self_only"] is True

    assert http["subject_from_authenticated_session"] is True

    assert http["subject_from_path"] is False

    assert http["subject_from_query"] is False

    assert http["subject_from_body"] is False

    assert http["write_methods_supported"] is False

    persistence = data["read_persistence"]

    assert persistence["sqlite_mode"] == "ro"

    assert persistence["pragma_query_only"] is True

    assert persistence["schema_creation_capability"] is False

    assert persistence["write_methods"] is False

    assert persistence["runtime_schema_activation"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["zero_trust"] is True

    assert security["least_privilege"] is True

    assert security["data_minimization"] is True

    assert security["fail_closed"] is True

    assert security["server_derived_subject"] is True

    assert security["horizontal_idor_subject_parameter"] is False

    assert security["new_secret"] is False

    assert security["new_write_path"] is False

    assert security["persistent_attack_surface_increase"] is True

    assert security["existing_security_silently_weakened"] is False

    server = (ROOT / "services" / "api_aplicacao" / "servidor.py").read_text(encoding="utf-8")

    assert 'rota == "/api/v1/me/trust"' in server

    assert '"/api/v1/me/trust"' in server

    assert "user_facing_trust.obter(" in server


def test_8f2_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8F3-trust-evidence-history-api"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "completed",
        "8F3": "trust-evidence-history-api",
        "8F4": "public-app-trust-client",
        "8F5": "public-app-trust-surface",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    validation = data["validation"]

    assert validation["isolated_8f2_cases_passed_pre_closure"] == 16

    assert validation["community_trust_cases_passed_pre_closure"] == 128

    assert validation["server_api_broad_cases_passed_pre_closure"] == 239

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

    assert validation["live_database_sha256_unchanged"] is True

    assert validation["live_database_write"] is False

    assert validation["live_schema_write"] is False

    assert validation["product_sqlite_handle_leak_fixed"] is True

    assert validation["test_fixture_sqlite_handle_leak_fixed"] is True

    assert validation["failure_masking"] is False

    assert validation["unlink_retry_added"] is False

    assert validation["windows_sleep_workaround_added"] is False

    assert validation["gc_workaround_added"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["validation_completed"] is True

    assert security["zero_trust"] is True

    assert security["least_privilege"] is True

    assert security["defense_in_depth"] is True

    assert security["data_minimization"] is True

    assert security["fail_closed"] is True

    assert security["authenticated_self_only_boundary_validated"] is True

    assert security["horizontal_idor_selector_present"] is False

    assert security["strict_read_only_runtime_repository_validated"] is True

    assert security["resource_lifecycle_explicit"] is True

    assert security["live_state_preserved"] is True

    assert security["existing_security_silently_weakened"] is False

    assert security["security_regression_detected"] is False

    assert security["secret_value_exposed"] is False

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_8f2_cases_after_closure"] == 17

    assert closure["expected_community_trust_cases_after_closure"] == 129

    assert closure["expected_community_trust_test_files_after_closure"] == 10

    assert closure["expected_server_api_broad_cases_after_closure"] == 240

    assert closure["expected_server_api_test_files_after_closure"] == 17

    assert closure["expected_community_moderation_cases_after_closure"] == 194

    assert closure["expected_public_mobile_cases_after_closure"] == 61

    assert closure["expected_backend_reporting_cases_after_closure"] == 70

    assert closure["8F1"] == "completed"

    assert closure["8F2"] == "completed"

    assert closure["8F3"] == "pending"
