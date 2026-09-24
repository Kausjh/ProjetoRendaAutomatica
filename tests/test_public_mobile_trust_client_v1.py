from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_trust_public_app_client_v1.json"

API_CLIENT = ROOT / "apps" / "public-mobile" / "src" / "api" / "public-api-client.ts"

TRUST_TYPES = ROOT / "apps" / "public-mobile" / "src" / "trust" / "trust-types.ts"

TRUST_PRESENTER = ROOT / "apps" / "public-mobile" / "src" / "trust" / "trust-presenter.ts"

TRUST_QUERIES = ROOT / "apps" / "public-mobile" / "src" / "trust" / "trust-queries.ts"

TRUST_INDEX = ROOT / "apps" / "public-mobile" / "src" / "trust" / "index.ts"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_8f4_contract_identity_tree_and_source():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8F4-public-app-trust-client"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "7583dae"

    assert data["source_stage"]["8F3"] == "completed"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "completed",
        "8F3": "completed",
        "8F4": "completed",
        "8F5": "public-app-trust-surface",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    assert data["next_step"] == "8F5-public-app-trust-surface"


def test_public_api_client_has_trust_profile_method():
    source = _text(API_CLIENT)

    assert "getCommunityTrustProfile" in source

    assert 'path: "/me/trust"' in source


def test_public_api_client_has_trust_history_method():
    source = _text(API_CLIENT)

    assert "listCommunityTrustEvidence" in source

    assert 'path: "/me/trust/evidence"' in source

    assert "query: pagination" in source


def test_public_api_trust_methods_require_session_and_envelope():
    source = _text(API_CLIENT)

    start = source.index("getCommunityTrustProfile")

    fragment = source[start:]

    assert fragment.count("requiresUserSession: true") >= 2

    assert fragment.count('responseMode: "user-facing-envelope"') >= 2


def test_trust_types_are_minimized():
    source = _text(TRUST_TYPES)

    for field in (
        "evidenceTotal",
        "positiveTotal",
        "negativeTotal",
        "neutralTotal",
        "updatedAt",
        "modelVersion",
        "numericScoreDefined",
        "type",
        "classification",
        "occurredAt",
    ):
        assert field in source

    for forbidden in (
        "accountId",
        "evidenceId",
        "idempotencyKey",
        "originId",
        "policyVersion",
        "moderatorActor",
        "rawMetadata",
    ):
        assert forbidden not in source


def test_trust_types_do_not_define_numeric_score():
    source = _text(TRUST_TYPES)

    assert "numericScoreDefined: false" in source

    assert "numericScore:" not in source

    assert "score:" not in source


def test_trust_presenter_maps_profile_and_history():
    source = _text(TRUST_PRESENTER)

    assert "presentCommunityTrustProfile" in source

    assert "presentCommunityTrustEvidenceHistory" in source

    for backend_field in (
        "evidencias_total",
        "positivas_total",
        "negativas_total",
        "neutras_total",
        "atualizado_em",
        "tipo_evidencia",
        "classificacao",
        "ocorrido_em",
        "quantidade",
    ):
        assert backend_field in source


def test_trust_presenter_is_fail_closed():
    source = _text(TRUST_PRESENTER)

    assert "CommunityTrustPayloadError" in source

    assert "score_numerico_definido" in source

    assert "value !== false" in source

    assert 'value !== "positive"' in source

    assert 'value !== "negative"' in source

    assert 'value !== "neutral"' in source

    assert "count !== items.length" in source


def test_trust_queries_have_profile_and_history_hooks():
    source = _text(TRUST_QUERIES)

    assert "useCommunityTrustProfile" in source

    assert "useCommunityTrustEvidenceHistory" in source

    assert "getCommunityTrustProfile" in source

    assert "listCommunityTrustEvidence" in source


def test_trust_query_pagination_is_bounded():
    source = _text(TRUST_QUERIES)

    assert "normalizeCommunityTrustEvidencePagination" in source

    assert "limit < 1" in source

    assert "limit > 100" in source

    assert "offset < 0" in source

    assert "limit = 20" in source

    assert "offset = 0" in source


def test_trust_query_keys_do_not_contain_account_selector():
    source = _text(TRUST_QUERIES)

    assert 'all: ["community-trust"]' in source

    assert "accountId" not in source

    assert "contaId" not in source

    assert "conta_id" not in source


def test_trust_barrel_exports_all_client_layers():
    source = _text(TRUST_INDEX)

    assert "trust-presenter" in source

    assert "trust-queries" in source

    assert "trust-types" in source


def test_8f4_aegis_and_scope_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    boundaries = data["boundaries"]

    assert boundaries["public_app_client_changed"] is True

    assert boundaries["public_app_ui_changed"] is False

    assert boundaries["navigation_changed"] is False

    assert boundaries["screen_added"] is False

    assert boundaries["server_changed"] is False

    assert boundaries["server_endpoint_added"] is False

    assert boundaries["database_write"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["existing_http_transport_reused"] is True

    assert security["existing_session_storage_reused"] is True

    assert security["no_account_selector_added"] is True

    assert security["no_internal_evidence_identifiers_modeled"] is True

    assert security["no_internal_evidence_context_modeled"] is True

    assert security["no_numeric_score_invented"] is True

    assert security["new_write_path"] is False

    assert security["new_persistent_attack_surface"] is False

    assert security["existing_security_silently_weakened"] is False


def test_8f4_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8F5-public-app-trust-surface"

    assert data["8F_tree"] == {
        "8F1": "completed",
        "8F2": "completed",
        "8F3": "completed",
        "8F4": "completed",
        "8F5": "public-app-trust-surface",
        "8F6": "final-closure",
        "hidden_sublevels": False,
    }

    validation = data["validation"]

    assert validation["implementation_harness_missing_import_ast"] is True

    assert validation["implementation_harness_failure_functional"] is False

    assert validation["product_reapplied_after_harness_failure"] is False

    assert validation["public_mobile_discovery_harness_mismatch"] is True

    assert validation["public_mobile_discovery_harness_failure_functional"] is False

    assert validation["pre_commit_passed"] is True

    assert validation["public_app_typecheck_passed"] is True

    assert validation["isolated_8f4_cases_passed_pre_closure"] == 13

    assert validation["public_mobile_legacy_test_files"] == 6

    assert validation["public_mobile_legacy_cases_passed"] == 61

    assert validation["public_mobile_combined_test_files"] == 7

    assert validation["public_mobile_combined_cases_passed_pre_closure"] == 74

    assert validation["community_trust_backend_test_files"] == 11

    assert validation["community_trust_backend_cases_passed"] == 149

    assert validation["live_database_sha256_unchanged"] is True

    assert validation["database_write"] is False

    assert validation["trust_write"] is False

    assert validation["runtime_main_still_running"] is True

    assert validation["health_monitor_still_enabled"] is True

    assert validation["runtime_restart"] is False

    assert validation["functional_failure_detected"] is False

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["validation_completed"] is True

    assert security["existing_transport_reuse_validated"] is True

    assert security["existing_session_reuse_validated"] is True

    assert security["existing_infrastructure_auth_reuse_validated"] is True

    assert security["strict_presenter_validation_validated"] is True

    assert security["bounded_client_pagination_validated"] is True

    assert security["account_selector_absence_validated"] is True

    assert security["numeric_score_not_invented_validated"] is True

    assert security["internal_context_non_modeling_validated"] is True

    assert security["runtime_state_preserved"] is True

    assert security["live_database_state_preserved"] is True

    assert security["security_regression_detected"] is False

    assert security["existing_security_silently_weakened"] is False

    closure = data["closure"]

    assert closure["expected_isolated_8f4_cases_after_closure"] == 14

    assert closure["expected_public_mobile_legacy_test_files_after_closure"] == 6

    assert closure["expected_public_mobile_legacy_cases_after_closure"] == 61

    assert closure["expected_public_mobile_combined_test_files_after_closure"] == 7

    assert closure["expected_public_mobile_combined_cases_after_closure"] == 75

    assert closure["expected_community_trust_backend_test_files_after_closure"] == 11

    assert closure["expected_community_trust_backend_cases_after_closure"] == 149

    assert closure["8F4"] == "completed"

    assert closure["8F5"] == "pending"
