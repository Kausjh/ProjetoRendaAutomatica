from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from repositories.community_moderation_repository import (
    CommunityModerationRepository,
    ConflitoEstadoCommunityModeration,
    ConflitoIdempotenciaCommunityModeration,
    ReporterCommunityModerationNaoEncontrado,
    TargetCommunityModerationNaoEncontrado,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_core_v1.json"


def preparar_banco(
    tmp_path: Path,
) -> tuple[
    Path,
    CommunityModerationRepository,
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

        for conta_id in (
            "conta-contributor",
            "conta-reporter-a",
            "conta-reporter-b",
        ):
            conn.execute(
                """
                INSERT INTO contas_usuario (
                    id
                )
                VALUES (?)
                """,
                (conta_id,),
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
                "conta-contributor",
            ),
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
                "dsc-2",
                "conta-contributor",
            ),
        )

    return (
        banco,
        CommunityModerationRepository(banco),
    )


def criar_denuncia(
    repository: CommunityModerationRepository,
    *,
    reporter: str = "conta-reporter-a",
    target: str = "dsc-1",
    motivo: str = "spam",
    detalhes: str | None = "report teste",
    agora: str = "2026-09-22T12:00:00+00:00",
):
    return repository.registrar_denuncia(
        reporter_conta_id=reporter,
        target_type="community_discovery",
        target_id=target,
        motivo=motivo,
        detalhes=detalhes,
        agora=agora,
    )


def test_schema_core_moderation(
    tmp_path: Path,
):
    banco, _repository = preparar_banco(tmp_path)

    with sqlite3.connect(banco) as conn:

        tables = {str(row[0]) for row in conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """)}

        assert "community_moderation_reports" in tables

        assert "community_moderation_decisions" in tables

        assert "community_trust_evidence" not in tables

        assert "community_trust_profiles" not in tables

        report_fks = {
            (
                str(row[2]),
                str(row[3]),
                str(row[4]),
                str(row[6]),
            )
            for row in conn.execute("""
                PRAGMA foreign_key_list(
                    community_moderation_reports
                )
                """)
        }

        assert (
            "contas_usuario",
            "reporter_conta_id",
            "id",
            "RESTRICT",
        ) in report_fks

        assert (
            "community_discoveries",
            "target_id",
            "id",
            "RESTRICT",
        ) in report_fks

        decision_fks = {
            (
                str(row[2]),
                str(row[3]),
                str(row[4]),
                str(row[6]),
            )
            for row in conn.execute("""
                PRAGMA foreign_key_list(
                    community_moderation_decisions
                )
                """)
        }

        assert (
            "community_moderation_reports",
            "denuncia_id",
            "id",
            "RESTRICT",
        ) in decision_fks


def test_denuncia_cria_e_retry_e_idempotente(
    tmp_path: Path,
):
    _banco, repository = preparar_banco(tmp_path)

    first = criar_denuncia(repository)

    second = criar_denuncia(
        repository,
        agora="2026-09-22T13:00:00+00:00",
    )

    assert first.criado is True
    assert second.criado is False

    assert first.denuncia.id == second.denuncia.id

    assert first.denuncia.estado == "received"

    pendentes = repository.listar_pendentes()

    assert len(pendentes) == 1


def test_denuncia_idempotente_conflita_se_detalhes_mudam(
    tmp_path: Path,
):
    _banco, repository = preparar_banco(tmp_path)

    criar_denuncia(
        repository,
        detalhes="detalhe original",
    )

    with pytest.raises(ConflitoIdempotenciaCommunityModeration):
        criar_denuncia(
            repository,
            detalhes="detalhe diferente",
            agora="2026-09-22T13:00:00+00:00",
        )


def test_reporters_e_motivos_distintos_nao_colapsam(
    tmp_path: Path,
):
    _banco, repository = preparar_banco(tmp_path)

    criar_denuncia(
        repository,
        reporter="conta-reporter-a",
        motivo="spam",
    )

    criar_denuncia(
        repository,
        reporter="conta-reporter-b",
        motivo="spam",
    )

    criar_denuncia(
        repository,
        reporter="conta-reporter-a",
        motivo="fraud",
    )

    reports = repository.listar_denuncias_target(
        target_id="dsc-1",
        limite=10,
    )

    assert len(reports) == 3

    assert {
        (
            item.reporter_conta_id,
            item.motivo,
        )
        for item in reports
    } == {
        (
            "conta-reporter-a",
            "spam",
        ),
        (
            "conta-reporter-b",
            "spam",
        ),
        (
            "conta-reporter-a",
            "fraud",
        ),
    }


def test_reporter_e_target_precisam_existir(
    tmp_path: Path,
):
    _banco, repository = preparar_banco(tmp_path)

    with pytest.raises(ReporterCommunityModerationNaoEncontrado):
        criar_denuncia(
            repository,
            reporter="conta-inexistente",
        )

    with pytest.raises(TargetCommunityModerationNaoEncontrado):
        criar_denuncia(
            repository,
            target="dsc-inexistente",
        )


def test_keep_under_review_e_retry_da_decisao(
    tmp_path: Path,
):
    _banco, repository = preparar_banco(tmp_path)

    report = criar_denuncia(repository).denuncia

    first = repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="acao-review-1",
        moderator_actor_id="moderator-local-1",
        resultado="keep_under_review",
        familia_abuso_confirmado=None,
        justificativa="Analise em andamento.",
        ocorrido_em="2026-09-22T12:10:00+00:00",
    )

    assert first.criado is True

    assert first.denuncia.estado == "under_review"

    retry = repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="acao-review-1",
        moderator_actor_id="moderator-local-1",
        resultado="keep_under_review",
        familia_abuso_confirmado=None,
        justificativa="Analise em andamento.",
        ocorrido_em="2026-09-22T12:10:00+00:00",
    )

    assert retry.criado is False

    assert retry.decisao.id == first.decisao.id

    decisoes = repository.listar_decisoes(denuncia_id=report.id)

    assert len(decisoes) == 1


def test_confirmed_abuse_resolve_e_exige_familia(
    tmp_path: Path,
):
    _banco, repository = preparar_banco(tmp_path)

    report = criar_denuncia(repository).denuncia

    with pytest.raises(ValueError):
        repository.registrar_decisao(
            denuncia_id=report.id,
            acao_idempotencia="acao-invalida",
            moderator_actor_id="moderator-local-1",
            resultado="confirmed_abuse",
            familia_abuso_confirmado=None,
            justificativa=None,
            ocorrido_em="2026-09-22T12:10:00+00:00",
        )

    result = repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="acao-confirm-1",
        moderator_actor_id="moderator-local-1",
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("spam_confirmado"),
        justificativa="Spam confirmado.",
        ocorrido_em="2026-09-22T12:20:00+00:00",
    )

    assert result.criado is True

    assert result.denuncia.estado == "resolved"

    assert result.decisao.resultado == "confirmed_abuse"

    assert result.decisao.familia_abuso_confirmado == "spam_confirmado"


def test_outcome_nao_confirmatorio_proibe_familia(
    tmp_path: Path,
):
    _banco, repository = preparar_banco(tmp_path)

    report = criar_denuncia(repository).denuncia

    with pytest.raises(ValueError):
        repository.registrar_decisao(
            denuncia_id=report.id,
            acao_idempotencia="acao-dismiss-invalid",
            moderator_actor_id="moderator-local-1",
            resultado="dismissed",
            familia_abuso_confirmado=("spam_confirmado"),
            justificativa=None,
            ocorrido_em="2026-09-22T12:10:00+00:00",
        )


def test_resolved_bloqueia_nova_decisao_mas_retry_idempotente_funciona(
    tmp_path: Path,
):
    _banco, repository = preparar_banco(tmp_path)

    report = criar_denuncia(repository).denuncia

    first = repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="acao-dismiss-1",
        moderator_actor_id="moderator-local-1",
        resultado="dismissed",
        familia_abuso_confirmado=None,
        justificativa="Nao confirmado.",
        ocorrido_em="2026-09-22T12:10:00+00:00",
    )

    assert first.denuncia.estado == "resolved"

    retry = repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="acao-dismiss-1",
        moderator_actor_id="moderator-local-1",
        resultado="dismissed",
        familia_abuso_confirmado=None,
        justificativa="Nao confirmado.",
        ocorrido_em="2026-09-22T12:10:00+00:00",
    )

    assert retry.criado is False

    with pytest.raises(ConflitoEstadoCommunityModeration):
        repository.registrar_decisao(
            denuncia_id=report.id,
            acao_idempotencia="acao-extra",
            moderator_actor_id="moderator-local-1",
            resultado="keep_under_review",
            familia_abuso_confirmado=None,
            justificativa=None,
            ocorrido_em="2026-09-22T12:20:00+00:00",
        )


def test_decisions_sao_append_only_e_ordenadas(
    tmp_path: Path,
):
    banco, repository = preparar_banco(tmp_path)

    report = criar_denuncia(repository).denuncia

    repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="acao-review",
        moderator_actor_id="moderator-local-1",
        resultado="keep_under_review",
        familia_abuso_confirmado=None,
        justificativa=None,
        ocorrido_em="2026-09-22T12:10:00+00:00",
    )

    repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="acao-confirm",
        moderator_actor_id="moderator-local-1",
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("spam_confirmado"),
        justificativa=None,
        ocorrido_em="2026-09-22T12:20:00+00:00",
    )

    decisoes = repository.listar_decisoes(denuncia_id=report.id)

    assert [item.resultado for item in decisoes] == [
        "keep_under_review",
        "confirmed_abuse",
    ]

    with sqlite3.connect(banco) as conn:
        total = int(conn.execute("""
                SELECT COUNT(*)
                FROM community_moderation_decisions
                """).fetchone()[0])

    assert total == 2


def test_contract_8e2_core_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E2-moderation-reporting-core-ledger"

    assert data["source_contract"] == "contracts/community_moderation_model_v1.json"

    reports = data["reports_ledger"]

    assert reports["idempotency"]["same_reporter_target_reason_once"] is True

    assert reports["idempotency"]["semantic_conflict_fails_closed"] is True

    decisions = data["decision_ledger"]

    assert decisions["append_only_rows"] is True

    assert decisions["moderator_authority_validated_by_repository"] is False

    assert decisions["moderator_authority_reserved_for_service"] is True

    assert decisions["idempotent_replay_after_resolution"] is True

    trust = data["trust"]

    assert trust["ledger_write"] is False

    assert trust["terminal_evidence_mutation"] is False

    assert trust["negative_evidence_write"] is False

    assert trust["bridge_implemented"] is False

    boundaries = data["validation_boundaries"]

    assert boundaries["tests_use_temporary_databases_only"] is True

    assert boundaries["live_database_schema_change"] is False

    assert boundaries["live_database_write"] is False

    assert data["next_step"] == "8E3-authoritative-moderation-policy-service"


def test_contract_8e2_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E3-authoritative-moderation-policy-service"

    validation = data["validation"]

    assert validation["baseline"] == "45883a6"

    assert validation["isolated_tests_passed_pre_closure"] == 11

    assert validation["stage_8e_tests_passed_pre_closure"] == 19

    assert validation["trust_moderation_tests_passed_pre_closure"] == 68

    assert validation["temporary_sqlite_integrity"] == "ok"

    assert validation["temporary_sqlite_foreign_key_errors"] == 0

    assert validation["temporary_reports"] == 2

    assert validation["temporary_decisions"] == 2

    assert validation["temporary_duplicate_report_keys"] == 0

    assert validation["temporary_duplicate_decision_keys"] == 0

    assert validation["temporary_trust_tables_created"] == 0

    assert validation["report_idempotency_validated"] is True

    assert validation["decision_idempotency_validated"] is True

    assert validation["decision_state_machine_validated"] is True

    assert validation["moderator_authority_implemented"] is False

    assert validation["trust_bridge_write"] is False

    assert validation["terminal_trust_evidence_mutated"] is False

    assert validation["live_schema_activation"] is False

    assert validation["live_database_query_only"] is True

    assert validation["live_integrity_check"] == "ok"

    assert validation["live_foreign_key_errors"] == 0

    assert validation["live_moderation_tables"] == 0

    assert validation["live_trust_evidence_total"] == 2

    assert validation["live_trust_profile_total"] == 1

    assert validation["live_database_write"] is False

    assert validation["public_report_api"] is False

    assert validation["admin_moderation_api"] is False
