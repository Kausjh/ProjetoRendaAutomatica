from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.community_trust import (
    PerfilCommunityTrust,
)
from models.user_identity import (
    ContaUsuario,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
)
from services.api_aplicacao.user_facing_trust import (
    UserFacingCommunityTrustController,
)
from services.community_trust_read_service import (
    PUBLIC_TRUST_READ_MODEL_VERSION,
    CommunityTrustReadService,
    LeituraCommunityTrustUsuario,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_trust_public_read_model_v1.json"


def _conta(
    conta_id: str = "usr_a",
    *,
    ativa: bool = True,
) -> ContaUsuario:
    return ContaUsuario(
        id=conta_id,
        email=f"{conta_id}@example.com",
        criado_em="2026-09-22T12:00:00+00:00",
        ativa=ativa,
    )


def _perfil(
    *,
    conta_id: str = "usr_a",
    total: int = 6,
    positivas: int = 3,
    negativas: int = 2,
    neutras: int = 1,
    atualizado_em: str | None = ("2026-09-22T13:00:00+00:00"),
) -> PerfilCommunityTrust:
    return PerfilCommunityTrust(
        conta_id=conta_id,
        evidencias_total=total,
        positivas_total=positivas,
        negativas_total=negativas,
        neutras_total=neutras,
        atualizado_em=atualizado_em,
    )


class FakeTrustRepository:
    def __init__(
        self,
        perfil: PerfilCommunityTrust | None = None,
    ) -> None:
        self.perfil = perfil if perfil is not None else _perfil()

        self.calls: list[str] = []

    def obter_perfil(
        self,
        conta_id: str,
    ) -> PerfilCommunityTrust:
        self.calls.append(conta_id)

        return self.perfil


def _service(
    repository: FakeTrustRepository | None = None,
) -> CommunityTrustReadService:
    return CommunityTrustReadService(
        repository if repository is not None else FakeTrustRepository()
    )  # type: ignore[arg-type]


def _controller(
    repository: FakeTrustRepository | None = None,
) -> UserFacingCommunityTrustController:
    return UserFacingCommunityTrustController(_service(repository))


def test_8f1_contract_identity_tree_and_source():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8F1-trust-public-read-model"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "94fecd2"

    assert data["source_stage"]["8E12C"] == "completed"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "authenticated-trust-profile-api",
        "8F3": "trust-evidence-history-api",
        "8F4": "public-app-trust-client",
        "8F5": "public-app-trust-surface",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    assert data["next_step"] == "8F2-authenticated-trust-profile-api"


def test_read_service_uses_requested_account():
    repository = FakeTrustRepository()

    leitura = _service(repository).obter("usr_exact")

    assert repository.calls == ["usr_exact"]

    assert leitura.read_model_version == PUBLIC_TRUST_READ_MODEL_VERSION


def test_read_service_rejects_empty_account_id():
    service = _service()

    with pytest.raises(ValueError):
        service.obter("   ")


def test_controller_returns_limited_profile_projection():
    status, body = _controller().obter(_conta())

    assert status == 200

    assert body == {
        "perfil": {
            "evidencias_total": 6,
            "positivas_total": 3,
            "negativas_total": 2,
            "neutras_total": 1,
            "atualizado_em": "2026-09-22T13:00:00+00:00",
        },
        "modelo": {
            "versao": 1,
            "score_numerico_definido": False,
        },
    }


def test_controller_does_not_expose_account_id():
    _, body = _controller().obter(_conta("usr_private"))

    rendered = json.dumps(
        body,
        ensure_ascii=False,
    )

    assert "usr_private" not in rendered
    assert "conta_id" not in rendered


def test_controller_does_not_invent_numeric_score():
    _, body = _controller().obter(_conta())

    model = body["modelo"]

    assert isinstance(
        model,
        dict,
    )

    assert model["score_numerico_definido"] is False

    assert "score" not in body
    assert "trust_score" not in body
    assert "pontuacao" not in body


def test_controller_fails_closed_without_service():
    controller = UserFacingCommunityTrustController(None)

    with pytest.raises(ErroHttpUserFacing) as captured:
        controller.obter(_conta())

    assert captured.value.status == 503

    assert captured.value.codigo == "trust_comunitario_indisponivel"


def test_controller_rejects_inactive_account():
    controller = _controller()

    with pytest.raises(ErroHttpUserFacing) as captured:
        controller.obter(_conta(ativa=False))

    assert captured.value.status == 401

    assert captured.value.codigo == "sessao_usuario_invalida"


def test_real_repository_zero_state(
    tmp_path: Path,
):
    database = tmp_path / "trust-zero.sqlite3"

    repository = CommunityTrustRepository(database)

    service = CommunityTrustReadService(repository)

    leitura = service.obter("usr_zero")

    perfil = leitura.perfil

    assert perfil.conta_id == "usr_zero"

    assert perfil.evidencias_total == 0

    assert perfil.positivas_total == 0

    assert perfil.negativas_total == 0

    assert perfil.neutras_total == 0

    assert perfil.atualizado_em is None


def test_real_repository_profile_projection(
    tmp_path: Path,
):
    database = tmp_path / "trust-profile.sqlite3"

    identities = UserIdentityRepository(database)

    account = identities.criar_conta(
        conta_id="usr_real",
        email_normalizado=("real@example.com"),
        email_exibicao=("real@example.com"),
        senha_salt=b"salt",
        senha_hash=b"hash",
        criado_em=("2026-09-22T12:00:00+00:00"),
    )

    repository = CommunityTrustRepository(database)

    repository.registrar_evidencia(
        conta_id=account.id,
        chave_idempotencia=("trust-real-positive"),
        tipo_evidencia=("test_positive"),
        classificacao="positive",
        origem="test",
        origem_id="source-positive",
        motivo="valid_test",
        politica_versao="test-v1",
        metadados={
            "private_marker": "must-not-leak",
        },
        ocorrido_em=("2026-09-22T12:10:00+00:00"),
    )

    repository.registrar_evidencia(
        conta_id=account.id,
        chave_idempotencia=("trust-real-negative"),
        tipo_evidencia=("test_negative"),
        classificacao="negative",
        origem="test",
        origem_id="source-negative",
        motivo="valid_test",
        politica_versao="test-v1",
        metadados={
            "private_marker": "must-not-leak",
        },
        ocorrido_em=("2026-09-22T12:11:00+00:00"),
    )

    controller = UserFacingCommunityTrustController(CommunityTrustReadService(repository))

    status, body = controller.obter(account)

    assert status == 200

    assert body["perfil"] == {
        "evidencias_total": 2,
        "positivas_total": 1,
        "negativas_total": 1,
        "neutras_total": 0,
        "atualizado_em": body["perfil"]["atualizado_em"],
    }


def test_aegis_projection_excludes_internal_trust_fields():
    leitura = LeituraCommunityTrustUsuario(
        perfil=_perfil(),
        read_model_version=1,
    )

    body = UserFacingCommunityTrustController._serializar(leitura)

    rendered = json.dumps(
        body,
        ensure_ascii=False,
    )

    for restricted in (
        "chave_idempotencia",
        "origem_id",
        "metadados",
        "moderator_actor_id",
        "familia_abuso_confirmado",
        "justificativa",
        "politica_versao",
        "deduplication_scope",
    ):
        assert restricted not in rendered


def test_8f1_contract_security_and_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    projection = data["public_projection"]

    assert projection["account_id_exposed"] is False

    assert projection["evidence_history_exposed"] is False

    assert projection["raw_metadata_exposed"] is False

    assert projection["idempotency_key_exposed"] is False

    assert projection["numeric_score_defined"] is False

    boundaries = data["boundaries"]

    assert boundaries["http_route_added"] is False

    assert boundaries["server_wiring_changed"] is False

    assert boundaries["database_schema_changed"] is False

    assert boundaries["database_write"] is False

    assert boundaries["public_app_changed"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["fail_closed_if_service_unavailable"] is True

    assert security["new_public_endpoint"] is False

    assert security["new_secret"] is False

    assert security["new_dependency"] is False

    assert security["persistent_attack_surface_increase"] is False

    assert security["internal_fields_exposed"] is False


def test_8f1_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8F2-authenticated-trust-profile-api"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "authenticated-trust-profile-api",
        "8F3": "trust-evidence-history-api",
        "8F4": "public-app-trust-client",
        "8F5": "public-app-trust-surface",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    validation = data["validation"]

    assert validation["baseline_commit"] == "94fecd2"

    assert validation["isolated_8f1_cases_passed_pre_closure"] == 12

    assert validation["community_trust_test_files"] == 9

    assert validation["community_trust_cases_passed_pre_closure"] == 111

    assert validation["community_moderation_cases_passed"] == 194

    assert validation["public_mobile_cases_passed"] == 61

    assert validation["backend_reporting_cases_passed"] == 70

    assert validation["live_integrity_check"] == "ok"

    assert validation["live_foreign_key_errors"] == 0

    assert validation["live_moderation_report_rows"] == 0

    assert validation["live_moderation_decision_rows"] == 0

    assert validation["live_trust_evidence_total"] == 2

    assert validation["live_trust_profile_total"] == 1

    assert validation["live_database_write"] is False

    assert validation["live_schema_write"] is False

    assert validation["http_route_added"] is False

    assert validation["server_wiring_changed"] is False

    assert validation["public_app_changed"] is False

    assert validation["database_schema_changed"] is False

    assert validation["numeric_trust_score_defined"] is False

    assert validation["numeric_trust_score_invented"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["security_first_class"] is True

    assert security["secure_by_design"] is True

    assert security["least_privilege"] is True

    assert security["data_minimization"] is True

    assert security["fail_closed_if_service_unavailable"] is True

    assert security["existing_security_silently_weakened"] is False

    assert security["security_regression_detected"] is False

    assert security["secret_value_exposed"] is False

    assert security["public_projection_minimized"] is True

    assert security["numeric_score_invented"] is False

    assert security["authorization_boundary_deferred_to_8F2"] is True

    assert security["persistent_attack_surface_increase"] is False

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_8f1_cases_after_closure"] == 13

    assert closure["expected_community_trust_cases_after_closure"] == 112

    assert closure["expected_community_trust_test_files_after_closure"] == 9

    assert closure["expected_community_moderation_cases_after_closure"] == 194

    assert closure["expected_public_mobile_cases_after_closure"] == 61

    assert closure["expected_backend_reporting_cases_after_closure"] == 70

    assert closure["8F1"] == "completed"

    assert closure["8F2"] == "pending"
