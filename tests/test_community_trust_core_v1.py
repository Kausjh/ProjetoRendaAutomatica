from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from repositories.community_trust_repository import (
    CommunityTrustRepository,
    ConflitoIdempotenciaCommunityTrust,
)

ROOT = Path(__file__).resolve().parents[1]
CORE_CONTRACT = ROOT / "contracts" / "community_trust_core_v1.json"


def preparar_banco(tmp_path: Path) -> tuple[Path, CommunityTrustRepository]:
    db = tmp_path / "identity.sqlite3"

    with sqlite3.connect(db) as conexao:
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.execute("""
            CREATE TABLE contas_usuario (
                id TEXT PRIMARY KEY
            )
            """)
        conexao.executemany(
            """
            INSERT INTO contas_usuario (id)
            VALUES (?)
            """,
            [
                ("conta-a",),
                ("conta-b",),
            ],
        )

    return db, CommunityTrustRepository(db)


def registrar(
    repository: CommunityTrustRepository,
    *,
    conta_id: str = "conta-a",
    chave: str = "trust:discovery:1",
    classificacao: str = "positive",
    tipo: str = "community_discovery_approved",
    origem_id: str = "discovery-1",
    motivo: str | None = None,
    metadados: dict | None = None,
):
    return repository.registrar_evidencia(
        conta_id=conta_id,
        chave_idempotencia=chave,
        tipo_evidencia=tipo,
        classificacao=classificacao,
        origem="community_discovery_v1",
        origem_id=origem_id,
        motivo=motivo,
        politica_versao=None,
        metadados=metadados or {"status": "approved"},
        ocorrido_em="2026-09-20T20:00:00+00:00",
    )


def test_schema_creates_ledger_profile_and_foreign_keys(tmp_path):
    db, _ = preparar_banco(tmp_path)

    with sqlite3.connect(db) as conexao:
        tables = {row[0] for row in conexao.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """)}

        assert "community_trust_evidence" in tables
        assert "community_trust_profiles" in tables

        evidence_fk = conexao.execute(
            "PRAGMA foreign_key_list(community_trust_evidence)"
        ).fetchall()

        profile_fk = conexao.execute("PRAGMA foreign_key_list(community_trust_profiles)").fetchall()

        assert any(row[2] == "contas_usuario" for row in evidence_fk)
        assert any(row[2] == "contas_usuario" for row in profile_fk)


def test_positive_evidence_materializes_profile(tmp_path):
    _, repository = preparar_banco(tmp_path)

    result = registrar(repository)

    assert result.criado is True
    assert result.evidencia.classificacao == "positive"
    assert result.perfil.evidencias_total == 1
    assert result.perfil.positivas_total == 1
    assert result.perfil.negativas_total == 0
    assert result.perfil.neutras_total == 0


@pytest.mark.parametrize(
    ("classificacao", "positivas", "negativas", "neutras"),
    [
        ("positive", 1, 0, 0),
        ("negative", 0, 1, 0),
        ("neutral", 0, 0, 1),
    ],
)
def test_all_core_classifications_are_counted(
    tmp_path,
    classificacao,
    positivas,
    negativas,
    neutras,
):
    _, repository = preparar_banco(tmp_path)

    result = registrar(
        repository,
        classificacao=classificacao,
    )

    assert result.perfil.evidencias_total == 1
    assert result.perfil.positivas_total == positivas
    assert result.perfil.negativas_total == negativas
    assert result.perfil.neutras_total == neutras


def test_idempotent_retry_does_not_increment_profile(tmp_path):
    _, repository = preparar_banco(tmp_path)

    first = registrar(repository)
    second = registrar(repository)

    assert first.criado is True
    assert second.criado is False
    assert second.evidencia.id == first.evidencia.id
    assert second.perfil.evidencias_total == 1
    assert second.perfil.positivas_total == 1

    events = repository.listar_evidencias(conta_id="conta-a")

    assert len(events) == 1


def test_idempotency_collision_fails_closed(tmp_path):
    _, repository = preparar_banco(tmp_path)

    registrar(repository)

    with pytest.raises(ConflitoIdempotenciaCommunityTrust):
        registrar(
            repository,
            classificacao="neutral",
        )


def test_metadata_is_canonical_for_idempotency(tmp_path):
    _, repository = preparar_banco(tmp_path)

    first = registrar(
        repository,
        metadados={
            "status": "approved",
            "marketplace": "ml",
        },
    )

    second = registrar(
        repository,
        metadados={
            "marketplace": "ml",
            "status": "approved",
        },
    )

    assert first.criado is True
    assert second.criado is False


def test_accounts_are_isolated(tmp_path):
    _, repository = preparar_banco(tmp_path)

    registrar(repository)

    registrar(
        repository,
        conta_id="conta-b",
        chave="trust:discovery:2",
        origem_id="discovery-2",
    )

    a = repository.listar_evidencias(conta_id="conta-a")
    b = repository.listar_evidencias(conta_id="conta-b")

    assert len(a) == 1
    assert len(b) == 1
    assert a[0].conta_id == "conta-a"
    assert b[0].conta_id == "conta-b"


def test_missing_account_fails_foreign_key(tmp_path):
    _, repository = preparar_banco(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        registrar(
            repository,
            conta_id="nao-existe",
        )


def test_reason_and_origin_trace_are_preserved(tmp_path):
    _, repository = preparar_banco(tmp_path)

    result = registrar(
        repository,
        classificacao="neutral",
        tipo="community_discovery_rejected",
        motivo="technical_failure",
        metadados={
            "status": "rejected",
        },
    )

    evidence = result.evidencia

    assert evidence.origem == "community_discovery_v1"
    assert evidence.origem_id == "discovery-1"
    assert evidence.motivo == "technical_failure"
    assert evidence.metadados == {
        "status": "rejected",
    }


def test_profile_has_counts_but_no_numeric_trust_score(tmp_path):
    _, repository = preparar_banco(tmp_path)

    registrar(repository)

    profile = repository.obter_perfil("conta-a")

    assert profile.evidencias_total == 1
    assert not hasattr(profile, "score")
    assert not hasattr(profile, "trust_score")
    assert not hasattr(profile, "reputacao_total")


def test_invalid_classification_is_rejected(tmp_path):
    _, repository = preparar_banco(tmp_path)

    with pytest.raises(
        ValueError,
        match="classificacao invalida",
    ):
        registrar(
            repository,
            classificacao="unknown",
        )


def test_core_contract_freezes_8b_boundaries():
    data = json.loads(CORE_CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == ("8B-community-trust-core-ledger")
    assert data["status"] == "completed"
    assert data["next_step"] == ("8C-production-trust-policy-anti-abuse")

    validation = data["validation"]

    assert validation["targeted_tests_passed"] == 16
    assert validation["live_schema_initialized"] is True
    assert validation["live_schema_second_init_idempotent"] is True
    assert validation["live_evidence_total_after_init"] == 0
    assert validation["live_profile_total_after_init"] == 0
    assert validation["integrity_check"] == "ok"
    assert validation["foreign_key_errors"] == 0
    assert validation["preexisting_schema_preserved"] is True
    assert validation["backup_validated"] is True

    assert data["profile"]["rebuildable_from_ledger"] is True

    assert data["profile"]["trust_score_field"] is False

    boundaries = data["boundaries"]

    assert boundaries["production_numeric_policy"] is False
    assert boundaries["community_discovery_wiring"] is False
    assert boundaries["runtime_wiring"] is False
    assert boundaries["gamification_projection"] is False
    assert boundaries["reputation_total_write"] is False
    assert boundaries["public_api"] is False
    assert boundaries["public_app"] is False
    assert boundaries["offer_scoring_influence"] is False
    assert boundaries["price_intelligence_influence"] is False


def test_rebuild_profile_repairs_projection_from_ledger(
    tmp_path,
):
    db, repository = preparar_banco(tmp_path)

    registrar(repository)

    registrar(
        repository,
        chave="trust:discovery:2",
        classificacao="neutral",
        origem_id="discovery-2",
        metadados={
            "status": "rejected",
        },
    )

    with sqlite3.connect(db) as conexao:
        conexao.execute("""
            UPDATE community_trust_profiles
            SET
                evidencias_total = 9,
                positivas_total = 9,
                negativas_total = 0,
                neutras_total = 0
            WHERE conta_id = 'conta-a'
            """)

    reconstruido = repository.reconstruir_perfil("conta-a")

    assert reconstruido.evidencias_total == 2
    assert reconstruido.positivas_total == 1
    assert reconstruido.negativas_total == 0
    assert reconstruido.neutras_total == 1


def test_registration_rolls_back_if_profile_write_fails(
    tmp_path,
):
    db, repository = preparar_banco(tmp_path)

    with sqlite3.connect(db) as conexao:
        conexao.execute("""
            CREATE TRIGGER
                fail_community_trust_profile_insert
            BEFORE INSERT
            ON community_trust_profiles
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'forced_profile_failure'
                );
            END
            """)

    with pytest.raises(sqlite3.IntegrityError):
        registrar(repository)

    with sqlite3.connect(db) as conexao:
        evidence_total = conexao.execute("""
            SELECT COUNT(*)
            FROM community_trust_evidence
            """).fetchone()[0]

        profile_total = conexao.execute("""
            SELECT COUNT(*)
            FROM community_trust_profiles
            """).fetchone()[0]

    assert evidence_total == 0
    assert profile_total == 0
