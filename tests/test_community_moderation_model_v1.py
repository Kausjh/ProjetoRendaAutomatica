from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from models.community_moderation import (
    ESTADOS_DENUNCIA_VALIDOS,
    FAMILIA_ABUSO_POR_MOTIVO_DENUNCIA,
    FAMILIAS_ABUSO_CONFIRMADO,
    MOTIVOS_DENUNCIA_VALIDOS,
    ORIGEM_TRUST_MODERACAO,
    RESULTADOS_MODERACAO_VALIDOS,
    TARGET_TYPES_VALIDOS,
    TIPO_EVIDENCIA_TRUST_MODERACAO,
    DecisaoCommunityModeration,
    DenunciaCommunityModeration,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_model_v1.json"

TRUST_POLICY = ROOT / "contracts" / "community_trust_policy_v1.json"

STAGE8D_CLOSURE = ROOT / "contracts" / "community_trust_stage8d_closure_v1.json"


def carregar_contrato() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_modelo_8e1_define_vocabulario_v1():
    assert TARGET_TYPES_VALIDOS == {
        "community_discovery",
    }

    assert MOTIVOS_DENUNCIA_VALIDOS == {
        "spam",
        "fraud",
        "malicious_link",
        "abuse",
        "off_topic",
        "duplicate",
        "other",
    }

    assert ESTADOS_DENUNCIA_VALIDOS == {
        "received",
        "under_review",
        "resolved",
    }

    assert RESULTADOS_MODERACAO_VALIDOS == {
        "confirmed_abuse",
        "dismissed",
        "keep_under_review",
    }


def test_familias_confirmadas_alinham_com_trust_policy():
    trust = json.loads(TRUST_POLICY.read_text(encoding="utf-8"))

    policy_families = set(trust["negative_policy"]["confirmed_abuse_reason_families"])

    assert FAMILIAS_ABUSO_CONFIRMADO == policy_families

    assert FAMILIA_ABUSO_POR_MOTIVO_DENUNCIA == {
        "spam": "spam_confirmado",
        "fraud": "fraude_confirmada",
        "malicious_link": ("link_malicioso_confirmado"),
        "abuse": "abuso_confirmado",
    }


def test_report_nao_e_autoridade_de_trust():
    data = carregar_contrato()

    authority = data["authority"]

    assert authority["report_is_allegation_only"] is True

    assert authority["report_is_objective_truth"] is False

    assert authority["report_count_is_authority"] is False

    assert authority["moderator_confirmation_required"] is True

    assert authority["public_user_can_confirm_abuse"] is False

    assert authority["automated_report_threshold_can_confirm_abuse"] is False

    assert authority["active_account_flag_is_moderator_role"] is False


def test_moderation_negative_e_aditiva_e_idempotente_por_target():
    data = carregar_contrato()

    bridge = data["trust_bridge_design"]

    assert bridge["existing_terminal_evidence_mutated"] is False

    assert bridge["existing_terminal_evidence_reclassified"] is False

    assert bridge["creates_separate_evidence"] is True

    assert bridge["classification"] == "negative"

    assert bridge["evidence_type"] == TIPO_EVIDENCIA_TRUST_MODERACAO

    assert bridge["origin"] == ORIGEM_TRUST_MODERACAO

    assert bridge["multiple_confirmed_reports_can_stack_negatives"] is False

    assert bridge["terminal_discovery_key_reused"] is False

    assert bridge["idempotency_template"] == (
        "v1:community-moderation:" "community-discovery:" "{discovery_id}:confirmed-abuse"
    )


def test_reason_nao_abusivo_nao_mapeia_negative():
    data = carregar_contrato()

    moderation = data["moderation"]

    assert moderation["off_topic_maps_to_negative_trust"] is False

    assert moderation["duplicate_maps_to_negative_trust"] is False

    assert moderation["other_maps_to_negative_trust"] is False

    assert moderation["dismissed_creates_negative_trust"] is False

    assert moderation["keep_under_review_creates_negative_trust"] is False


def test_dataclasses_de_moderacao_sao_imutaveis():
    report = DenunciaCommunityModeration(
        id="rpt-1",
        reporter_conta_id="conta-a",
        target_type="community_discovery",
        target_id="dsc-1",
        motivo="spam",
        detalhes=None,
        estado="received",
        criado_em="2026-09-22T00:00:00+00:00",
        atualizado_em="2026-09-22T00:00:00+00:00",
    )

    decision = DecisaoCommunityModeration(
        id="mod-1",
        denuncia_id="rpt-1",
        moderator_actor_id="moderator-a",
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("spam_confirmado"),
        justificativa=None,
        ocorrido_em="2026-09-22T01:00:00+00:00",
    )

    with pytest.raises(FrozenInstanceError):
        report.estado = "resolved"

    with pytest.raises(FrozenInstanceError):
        decision.resultado = "dismissed"


def test_8e1_respeita_closure_8d_e_boundaries():
    data = carregar_contrato()

    stage8d = json.loads(STAGE8D_CLOSURE.read_text(encoding="utf-8"))

    assert stage8d["next_step"] == "8E-moderation-reporting-foundation"

    assert data["stage"] == "8E1-moderation-reporting-model-boundaries"

    boundaries = data["boundaries"]

    assert boundaries["database_schema_change"] is False

    assert boundaries["live_database_write"] is False

    assert boundaries["trust_bridge_write"] is False

    assert boundaries["public_report_api"] is False

    assert boundaries["admin_moderation_api"] is False

    assert boundaries["account_suspension"] is False

    assert boundaries["content_takedown"] is False

    assert boundaries["gamification_write"] is False

    assert boundaries["reputation_total_write"] is False

    assert data["next_step"] == "8E2-moderation-reporting-core-ledger"


def test_contract_8e1_closure_metadata():
    data = carregar_contrato()

    assert data["status"] == "completed"

    assert data["next_step"] == "8E2-moderation-reporting-core-ledger"

    validation = data["validation"]

    assert validation["baseline"] == "371646d"

    assert validation["isolated_tests_passed_pre_closure"] == 7

    assert validation["trust_8e1_regression_tests_passed_pre_closure"] == 56

    assert validation["live_preflight_query_only"] is True

    assert validation["live_integrity_check"] == "ok"

    assert validation["live_foreign_key_errors"] == 0

    assert validation["live_existing_moderation_tables"] == 0

    assert validation["live_database_mutation"] is False

    assert validation["terminal_trust_evidence_mutated"] is False

    assert validation["report_is_allegation_only"] is True

    assert validation["moderator_confirmation_required"] is True

    assert validation["report_count_is_authority"] is False

    assert validation["automatic_confirmation"] is False

    assert validation["moderation_trust_evidence_separate_additive"] is True

    assert validation["max_negative_moderation_evidence_per_discovery"] == 1

    assert validation["trust_bridge_write"] is False

    assert validation["public_report_api"] is False

    assert validation["admin_moderation_api"] is False

    assert validation["gamification_write"] is False

    assert validation["reputation_total_write"] is False
