from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.community_discovery import (
    DescobertaComunitaria,
)
from services.community_trust_policy import (
    CommunityTrustPolicyV1,
)

ROOT = Path(__file__).resolve().parents[1]

POLICY_CONTRACT = ROOT / "contracts" / "community_trust_policy_v1.json"

DISCOVERY_CONTRACT = ROOT / "contracts" / "community_discovery_v1.json"

GAMIFICATION_RULES = ROOT / "contracts" / "gamification_reputation_rules_v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def descoberta(
    *,
    status: str,
    motivo: str | None,
    identificador: str = "dsc_policy_1",
    canonical_key: str | None = "produto_teste",
    tentativas: int = 1,
) -> DescobertaComunitaria:
    return DescobertaComunitaria(
        id=identificador,
        conta_id="conta-a",
        url="https://example.com/oferta",
        url_normalizada="https://example.com/oferta",
        marketplace="mercado_livre",
        status=status,
        tentativas=tentativas,
        disponivel_em="2026-09-21T20:00:00+00:00",
        processando_desde=None,
        motivo_status=motivo,
        canonical_key=canonical_key,
        criado_em="2026-09-21T19:00:00+00:00",
        atualizado_em="2026-09-21T20:00:00+00:00",
    )


def test_contract_identity_and_numeric_policy():
    data = load(POLICY_CONTRACT)

    assert data["community_trust_policy_version"] == 1
    assert data["policy_version"] == ("community-trust-production-v1")
    assert data["stage"] == ("8C-production-trust-policy-anti-abuse")

    numeric = data["numeric_policy"]

    assert numeric["defined"] is True

    assert numeric["impact_units"] == {
        "positive": 1,
        "neutral": 0,
        "negative": -1,
    }

    assert numeric["aggregate_score_formula_defined"] is False

    assert numeric["trust_score_field_added"] is False

    assert numeric["gamification_reputation_projection"] is False


def test_upstream_controls_are_preserved():
    policy = load(POLICY_CONTRACT)
    discovery = load(DISCOVERY_CONTRACT)

    assert discovery["submission"]["per_account_hourly_limit"] == 30

    assert discovery["submission"]["same_account_same_normalized_url_idempotent"] is True

    upstream = policy["upstream_controls"]

    assert upstream["community_discovery_hourly_submission_limit"] == 30

    assert upstream["same_account_same_normalized_url_idempotent"] is True

    assert upstream["upstream_limit_replaces_trust_policy_cap"] is False


def test_positive_window_reuses_existing_10_day_pattern():
    policy = load(POLICY_CONTRACT)
    rules = load(GAMIFICATION_RULES)

    window = policy["positive_policy"]["rolling_window"]

    assert window["limit"] == 10
    assert window["window_seconds"] == 86400

    existing = [
        item
        for item in rules["rules"]["events"]
        if (item.get("window_limit") == 10 and item.get("window_seconds") == 86400)
    ]

    assert existing


@pytest.mark.parametrize(
    "status",
    [
        "received",
        "processing",
        "retry",
    ],
)
def test_non_terminal_status_does_not_create_evidence(
    status,
):
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status=status,
            motivo=None,
        )
    )

    assert result.elegivel is False
    assert result.classificacao is None
    assert result.impacto_unidades == 0
    assert result.chave_idempotencia is None
    assert result.motivo_politica == "status_nao_terminal"


def test_pipeline_processed_is_positive_under_cap():
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="approved",
            motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
        ),
        positivas_na_janela=9,
    )

    assert result.elegivel is True
    assert result.classificacao == "positive"
    assert result.impacto_unidades == 1
    assert result.motivo_politica == "approved_pipeline_processed"


def test_positive_window_cap_turns_next_positive_neutral():
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="approved",
            motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
        ),
        positivas_na_janela=10,
    )

    assert result.elegivel is True
    assert result.classificacao == "neutral"
    assert result.impacto_unidades == 0
    assert result.motivo_politica == "positive_window_cap_exceeded"


def test_downstream_duplicate_is_neutral():
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="approved",
            motivo=("coletor_duplicada:" "link_duplicado_no_coletor"),
        )
    )

    assert result.elegivel is True
    assert result.classificacao == "neutral"
    assert result.impacto_unidades == 0
    assert result.motivo_politica == "approved_duplicate_downstream"


def test_unknown_approved_reason_fails_closed_to_neutral():
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="approved",
            motivo="oferta_validada",
        )
    )

    assert result.classificacao == "neutral"
    assert result.impacto_unidades == 0
    assert result.motivo_politica == "approved_reason_not_positive"


@pytest.mark.parametrize(
    "motivo",
    [
        "limite_tentativas:falha persistente",
        "erro_api_catalogo_mercado_livre:rate_limit",
        "community_discovery_adapter_exception:RuntimeError",
        "processing_timeout",
    ],
)
def test_technical_rejections_are_neutral(
    motivo,
):
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="rejected",
            motivo=motivo,
        )
    )

    assert result.classificacao == "neutral"
    assert result.impacto_unidades == 0
    assert result.motivo_politica == "technical_or_system_rejection"


@pytest.mark.parametrize(
    "motivo",
    [
        "amazon_sem_processador_de_produto",
        "marketplace_comunitario_nao_suportado",
        "mercado_livre_sem_product_id_catalogo",
        ("titulo_oficial_ausente_para_" "community_discovery_link_only"),
    ],
)
def test_unsupported_capability_rejections_are_neutral(
    motivo,
):
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="rejected",
            motivo=motivo,
        )
    )

    assert result.classificacao == "neutral"
    assert result.impacto_unidades == 0
    assert result.motivo_politica == "unsupported_capability_rejection"


@pytest.mark.parametrize(
    "motivo",
    [
        ("mercado_livre_sem_publicacao_" "catalogo_com_preco_valido"),
        "produto_shopee_nao_resolvido",
        "produto_kabum_indisponivel",
        "preco_oficial_aliexpress_invalido",
        "coletor_fora_nicho:fora_do_nicho",
    ],
)
def test_market_or_quality_rejections_are_neutral(
    motivo,
):
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="rejected",
            motivo=motivo,
        )
    )

    assert result.classificacao == "neutral"
    assert result.impacto_unidades == 0
    assert result.motivo_politica == "market_or_quality_rejection"


@pytest.mark.parametrize(
    "motivo",
    [
        "abuso_confirmado:manual",
        "spam_confirmado:manual",
        "fraude_confirmada:manual",
        "link_malicioso_confirmado:manual",
    ],
)
def test_only_explicit_confirmed_abuse_is_negative(
    motivo,
):
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="rejected",
            motivo=motivo,
        ),
        abuso_confirmado_autoritativamente=True,
    )

    assert result.classificacao == "negative"
    assert result.impacto_unidades == -1
    assert result.motivo_politica == "confirmed_abuse"
    assert result.metadados["confirmed_abuse_authority"] is True


def test_unknown_rejection_fails_closed_to_neutral():
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="rejected",
            motivo="motivo_novo_desconhecido",
        )
    )

    assert result.classificacao == "neutral"
    assert result.impacto_unidades == 0
    assert result.motivo_politica == "rejection_reason_unclassified"


def test_source_object_has_stable_idempotency_key():
    item = descoberta(
        status="approved",
        motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
        identificador="dsc_abc123",
    )

    first = CommunityTrustPolicyV1.avaliar(item)

    second = CommunityTrustPolicyV1.avaliar(item)

    assert first.chave_idempotencia == ("v1:community-discovery:dsc_abc123")

    assert second.chave_idempotencia == first.chave_idempotencia


def test_policy_preserves_audit_context():
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="approved",
            motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
            tentativas=3,
        ),
        positivas_na_janela=4,
    )

    metadata = result.metadados

    assert result.politica_versao == "community-trust-production-v1"

    assert metadata["source_domain"] == ("community_discovery")

    assert metadata["source_status"] == "approved"
    assert metadata["tentativas"] == 3
    assert metadata["positive_count_before"] == 4
    assert metadata["positive_window_limit"] == 10
    assert metadata["positive_window_seconds"] == 86400
    assert metadata["positive_window_atomic_enforcement_required"] is True


def test_negative_window_input_is_rejected():
    with pytest.raises(
        ValueError,
        match="nao pode ser negativo",
    ):
        CommunityTrustPolicyV1.avaliar(
            descoberta(
                status="approved",
                motivo="pipeline_processada:ok",
            ),
            positivas_na_janela=-1,
        )


def test_boolean_window_input_is_rejected():
    with pytest.raises(
        ValueError,
        match="positivas_na_janela invalido",
    ):
        CommunityTrustPolicyV1.avaliar(
            descoberta(
                status="approved",
                motivo="pipeline_processada:ok",
            ),
            positivas_na_janela=True,
        )


def test_8c_boundaries_remain_closed():
    data = load(POLICY_CONTRACT)
    boundaries = data["boundaries"]

    assert boundaries["community_discovery_runtime_wiring"] is False

    assert boundaries["trust_ledger_write"] is False
    assert boundaries["database_schema_change"] is False
    assert boundaries["gamification_write"] is False
    assert boundaries["reputation_total_write"] is False
    assert boundaries["public_api"] is False
    assert boundaries["public_app"] is False
    assert boundaries["moderation_action"] is False
    assert boundaries["offer_scoring_influence"] is False
    assert boundaries["price_intelligence_influence"] is False


def test_confirmed_abuse_reason_without_authority_is_neutral():
    result = CommunityTrustPolicyV1.avaliar(
        descoberta(
            status="rejected",
            motivo="spam_confirmado:manual",
        )
    )

    assert result.elegivel is True
    assert result.classificacao == "neutral"
    assert result.impacto_unidades == 0
    assert result.motivo_politica == "confirmed_abuse_missing_authority"
    assert result.metadados["confirmed_abuse_authority"] is False


@pytest.mark.parametrize(
    "valor",
    [
        9.5,
        "9",
    ],
)
def test_positive_window_rejects_non_integer_context(
    valor,
):
    with pytest.raises(
        ValueError,
        match="precisa ser int",
    ):
        CommunityTrustPolicyV1.avaliar(
            descoberta(
                status="approved",
                motivo="pipeline_processada:ok",
            ),
            positivas_na_janela=valor,
        )


def test_abuse_authority_context_must_be_boolean():
    with pytest.raises(
        ValueError,
        match="precisa ser bool",
    ):
        CommunityTrustPolicyV1.avaliar(
            descoberta(
                status="rejected",
                motivo="spam_confirmado:manual",
            ),
            abuso_confirmado_autoritativamente=1,
        )


def test_contract_requires_atomic_runtime_window_enforcement():
    data = load(POLICY_CONTRACT)

    window = data["positive_policy"]["rolling_window"]

    assert window["runtime_count_source"] == "community_trust_evidence_server_side"

    assert window["runtime_enforcement_must_be_atomic_with_write"] is True

    assert window["policy_function_input_is_not_runtime_authority"] is True

    requirements = data["anti_abuse_runtime_requirements"]

    assert requirements["account_scope"] is True
    assert requirements["server_side_only"] is True

    assert requirements["positive_window_count_from_ledger"] is True

    assert requirements["positive_window_count_and_write_atomic"] is True

    assert requirements["concurrent_positive_overrun_must_fail_closed"] is True

    assert requirements["caller_supplied_count_not_authoritative"] is True


def test_contract_requires_negative_authority():
    data = load(POLICY_CONTRACT)

    negative = data["negative_policy"]

    assert negative["reason_text_alone_is_authority"] is False

    assert negative["requires_authoritative_confirmation_context"] is True

    assert negative["missing_authority_on_confirmed_reason"] == "neutral"

    assert data["anti_abuse_runtime_requirements"]["negative_requires_reason_and_authority"] is True

    assert data["audit"]["authoritative_abuse_confirmation_preserved"] is True
