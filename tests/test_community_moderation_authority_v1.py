from __future__ import annotations

import inspect
import json
import sqlite3
from pathlib import Path

import pytest

import services.community_moderation_authority as authority_module
from repositories.community_moderation_repository import (
    CommunityModerationRepository,
)
from services.community_moderation_authority import (
    AutoridadeModeracaoIndisponivel,
    AutorizacaoModeracaoNegada,
    CommunityModerationAuthorityV1,
)
from services.community_moderation_service import (
    CommunityModerationService,
    PoliticaModeracaoNegada,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_authority_v1.json"


TOKEN_ADMIN_TESTE = "token-admin-moderacao-teste"


def preparar(
    tmp_path: Path,
) -> tuple[
    Path,
    CommunityModerationRepository,
    CommunityModerationService,
]:
    banco = tmp_path / "identity.sqlite3"

    with sqlite3.connect(banco) as conn:

        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute("""
            CREATE TABLE contas_usuario (
                id TEXT PRIMARY KEY
            )
            """)

        conn.execute("""
            CREATE TABLE community_discoveries (
                id TEXT PRIMARY KEY,
                conta_id TEXT NOT NULL,
                FOREIGN KEY (conta_id)
                    REFERENCES contas_usuario(id)
            )
            """)

        for conta in (
            "contributor",
            "reporter",
        ):
            conn.execute(
                """
                INSERT INTO contas_usuario (id)
                VALUES (?)
                """,
                (conta,),
            )

        conn.execute(
            """
            INSERT INTO community_discoveries (
                id,
                conta_id
            )
            VALUES (?, ?)
            """,
            (
                "dsc-1",
                "contributor",
            ),
        )

    repository = CommunityModerationRepository(banco)

    authority = CommunityModerationAuthorityV1(token_administrativo=(TOKEN_ADMIN_TESTE))

    service = CommunityModerationService(
        repository=repository,
        authority=authority,
    )

    return (
        banco,
        repository,
        service,
    )


def criar_report(
    repository: CommunityModerationRepository,
    *,
    motivo: str = "spam",
):
    return repository.registrar_denuncia(
        reporter_conta_id="reporter",
        target_type="community_discovery",
        target_id="dsc-1",
        motivo=motivo,
        detalhes=None,
        agora="2026-09-22T12:00:00+00:00",
    ).denuncia


def bearer(
    token: str = TOKEN_ADMIN_TESTE,
) -> str:
    return f"Bearer {token}"


def test_authority_exige_token_configurado():
    with pytest.raises(AutoridadeModeracaoIndisponivel):
        CommunityModerationAuthorityV1(token_administrativo="")


def test_authority_from_environment_fail_closed(
    monkeypatch,
):
    monkeypatch.setattr(
        authority_module,
        "load_dotenv",
        lambda: None,
    )

    monkeypatch.delenv(
        "RADAR_ADMIN_TOKEN",
        raising=False,
    )

    with pytest.raises(AutoridadeModeracaoIndisponivel):
        (CommunityModerationAuthorityV1.from_environment())


def test_authority_from_environment_usa_admin_token(
    monkeypatch,
):
    monkeypatch.setattr(
        authority_module,
        "load_dotenv",
        lambda: None,
    )

    monkeypatch.setenv(
        "RADAR_ADMIN_TOKEN",
        TOKEN_ADMIN_TESTE,
    )

    authority = CommunityModerationAuthorityV1.from_environment()

    contexto = authority.autorizar(bearer())

    assert contexto.actor_id == "radar-admin-control-plane-v1"

    assert contexto.origem == "admin_control_plane"


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        "token-admin-moderacao-teste",
        "Basic token-admin-moderacao-teste",
        "Bearer token-errado",
    ],
)
def test_authority_rejeita_header_invalido(
    header: str | None,
):
    authority = CommunityModerationAuthorityV1(token_administrativo=(TOKEN_ADMIN_TESTE))

    with pytest.raises(AutorizacaoModeracaoNegada):
        authority.autorizar(header)


def test_authority_aceita_bearer_exato():
    authority = CommunityModerationAuthorityV1(token_administrativo=(TOKEN_ADMIN_TESTE))

    contexto = authority.autorizar(bearer())

    assert contexto.actor_id == "radar-admin-control-plane-v1"


def test_service_nao_expoe_actor_ou_family_para_caller():
    assinatura = inspect.signature(CommunityModerationService.registrar_decisao_autorizada)

    parametros = set(assinatura.parameters)

    assert "moderator_actor_id" not in parametros

    assert "familia_abuso_confirmado" not in parametros


def test_token_invalido_falha_antes_de_persistir(
    tmp_path: Path,
):
    banco, repository, service = preparar(tmp_path)

    report = criar_report(repository)

    with pytest.raises(AutorizacaoModeracaoNegada):
        service.registrar_decisao_autorizada(
            authorization_header=("Bearer token-usuario-comum"),
            denuncia_id=report.id,
            acao_idempotencia="acao-1",
            resultado="dismissed",
            justificativa=None,
            ocorrido_em=("2026-09-22T12:10:00+00:00"),
        )

    with sqlite3.connect(banco) as conn:

        total = int(conn.execute("""
                SELECT COUNT(*)
                FROM community_moderation_decisions
                """).fetchone()[0])

    assert total == 0


@pytest.mark.parametrize(
    (
        "motivo",
        "familia_esperada",
    ),
    [
        (
            "spam",
            "spam_confirmado",
        ),
        (
            "fraud",
            "fraude_confirmada",
        ),
        (
            "malicious_link",
            "link_malicioso_confirmado",
        ),
        (
            "abuse",
            "abuso_confirmado",
        ),
    ],
)
def test_confirmed_abuse_deriva_family_server_side(
    tmp_path: Path,
    motivo: str,
    familia_esperada: str,
):
    _banco, repository, service = preparar(tmp_path)

    report = criar_report(
        repository,
        motivo=motivo,
    )

    resultado = service.registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia=("confirm-" + motivo),
        resultado="confirmed_abuse",
        justificativa="Confirmado.",
        ocorrido_em=("2026-09-22T12:10:00+00:00"),
    )

    assert resultado.criado is True

    assert resultado.decisao.resultado == "confirmed_abuse"

    assert resultado.decisao.familia_abuso_confirmado == familia_esperada

    assert resultado.decisao.moderator_actor_id == "radar-admin-control-plane-v1"


@pytest.mark.parametrize(
    "motivo",
    [
        "off_topic",
        "duplicate",
        "other",
    ],
)
def test_motivo_ambiguo_nao_pode_confirmar_abuso(
    tmp_path: Path,
    motivo: str,
):
    banco, repository, service = preparar(tmp_path)

    report = criar_report(
        repository,
        motivo=motivo,
    )

    with pytest.raises(PoliticaModeracaoNegada):
        service.registrar_decisao_autorizada(
            authorization_header=bearer(),
            denuncia_id=report.id,
            acao_idempotencia=("confirm-invalid-" + motivo),
            resultado="confirmed_abuse",
            justificativa=None,
            ocorrido_em=("2026-09-22T12:10:00+00:00"),
        )

    with sqlite3.connect(banco) as conn:

        decision_total = int(conn.execute("""
                SELECT COUNT(*)
                FROM community_moderation_decisions
                """).fetchone()[0])

        estado = str(
            conn.execute(
                """
                SELECT estado
                FROM community_moderation_reports
                WHERE id = ?
                """,
                (report.id,),
            ).fetchone()[0]
        )

    assert decision_total == 0
    assert estado == "received"


def test_dismissed_funciona_para_reason_nao_abusivo(
    tmp_path: Path,
):
    _banco, repository, service = preparar(tmp_path)

    report = criar_report(
        repository,
        motivo="off_topic",
    )

    resultado = service.registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia="dismiss-1",
        resultado="dismissed",
        justificativa="Sem abuso.",
        ocorrido_em=("2026-09-22T12:10:00+00:00"),
    )

    assert resultado.criado is True

    assert resultado.denuncia.estado == "resolved"

    assert resultado.decisao.familia_abuso_confirmado is None


def test_keep_under_review_funciona_com_authority(
    tmp_path: Path,
):
    _banco, repository, service = preparar(tmp_path)

    report = criar_report(
        repository,
        motivo="other",
    )

    resultado = service.registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia="review-1",
        resultado="keep_under_review",
        justificativa="Precisa revisar.",
        ocorrido_em=("2026-09-22T12:10:00+00:00"),
    )

    assert resultado.denuncia.estado == "under_review"


def test_service_preserva_idempotencia_repository(
    tmp_path: Path,
):
    _banco, repository, service = preparar(tmp_path)

    report = criar_report(
        repository,
        motivo="spam",
    )

    first = service.registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia="confirm-1",
        resultado="confirmed_abuse",
        justificativa="Confirmado.",
        ocorrido_em=("2026-09-22T12:10:00+00:00"),
    )

    retry = service.registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia="confirm-1",
        resultado="confirmed_abuse",
        justificativa="Confirmado.",
        ocorrido_em=("2026-09-22T12:10:00+00:00"),
    )

    assert first.criado is True
    assert retry.criado is False

    assert first.decisao.id == retry.decisao.id


def test_8e3_nao_cria_trust(
    tmp_path: Path,
):
    banco, repository, service = preparar(tmp_path)

    report = criar_report(
        repository,
        motivo="spam",
    )

    service.registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia="confirm-1",
        resultado="confirmed_abuse",
        justificativa="Confirmado.",
        ocorrido_em=("2026-09-22T12:10:00+00:00"),
    )

    with sqlite3.connect(banco) as conn:

        tables = {str(row[0]) for row in conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """)}

    assert "community_trust_evidence" not in tables

    assert "community_trust_profiles" not in tables


def test_contract_8e3_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E3-authoritative-moderation-policy-service"

    authority = data["authority"]

    assert authority["environment_variable"] == "RADAR_ADMIN_TOKEN"

    assert authority["constant_time_compare"] is True

    assert authority["fail_closed_without_configured_token"] is True

    assert authority["loopback_bypass"] is False

    assert authority["end_user_session_is_authority"] is False

    assert authority["shared_principal"] is True

    assert authority["unique_human_identity_claimed"] is False

    service = data["service"]

    assert service["caller_can_supply_moderator_actor_id"] is False

    assert service["caller_can_supply_confirmed_abuse_family"] is False

    assert service["confirmed_abuse_family_derived_server_side"] is True

    trust = data["trust"]

    assert trust["bridge_implemented"] is False

    assert trust["ledger_write"] is False

    assert trust["negative_evidence_write"] is False

    runtime = data["runtime"]

    assert runtime["admin_http_route_integration"] is False

    assert runtime["live_schema_activation"] is False

    boundaries = data["validation_boundaries"]

    assert boundaries["real_admin_token_read_by_tests"] is False

    assert boundaries["live_database_write"] is False

    assert data["next_step"] == "8E4-moderation-trust-bridge-core"


def test_contract_8e3_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E4-moderation-trust-bridge-core"

    validation = data["validation"]

    assert validation["baseline"] == "05c8ac0"

    assert validation["isolated_tests_passed_pre_closure"] == 23

    assert validation["stage_8e_tests_passed_pre_closure"] == 43

    assert validation["trust_moderation_tests_passed_pre_closure"] == 92

    assert validation["authority_source"] == "RADAR_ADMIN_TOKEN"

    assert validation["authorization_scheme"] == "Bearer"

    assert validation["constant_time_compare"] is True

    assert validation["fail_closed_without_configured_token"] is True

    assert validation["loopback_bypass"] is False

    assert validation["end_user_session_is_authority"] is False

    assert validation["shared_technical_principal"] is True

    assert validation["unique_human_identity_claimed"] is False

    assert validation["caller_supplies_moderator_actor"] is False

    assert validation["caller_supplies_abuse_family"] is False

    assert validation["abuse_family_derived_server_side"] is True

    assert validation["ambiguous_reason_can_confirm_abuse"] is False

    assert validation["trust_bridge_write"] is False

    assert validation["terminal_trust_evidence_mutated"] is False

    assert validation["admin_http_route_integration"] is False

    assert validation["live_schema_activation"] is False

    assert validation["live_database_query_only"] is True

    assert validation["live_integrity_check"] == "ok"

    assert validation["live_foreign_key_errors"] == 0

    assert validation["live_moderation_tables"] == 0

    assert validation["live_trust_evidence_total"] == 2

    assert validation["live_trust_profile_total"] == 1

    assert validation["live_database_write"] is False

    assert validation["real_admin_token_read_by_tests"] is False
