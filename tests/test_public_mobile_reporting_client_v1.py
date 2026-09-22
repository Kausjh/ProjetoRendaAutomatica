from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_public_app_reporting_client_v1.json"


def _read(
    relative: str,
) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_8e11a_contract_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E11A-public-app-reporting-client-read-model"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "520034c"

    assert data["recovery"]["partial_failure_recovered"] is True

    assert data["recovery"]["recovery_reapplied_api_types"] is False


def test_transport_has_narrow_idempotency_option():
    api_types = _read("apps/public-mobile/src/api/api-types.ts")

    transport = _read("apps/public-mobile/src/api/http-transport.ts")

    assert api_types.count("idempotencyKey?: string;") == 1

    assert 'headers["Idempotency-Key"]' in transport

    assert "options.idempotencyKey?.trim()" in transport

    assert "customHeaders" not in api_types


def test_public_api_client_exposes_report_methods():
    source = _read("apps/public-mobile/src/api/public-api-client.ts")

    for method in (
        "listCommunityReports",
        "getCommunityReport",
        "createCommunityReport",
    ):
        assert method in source

    assert 'path: "/me/reports"' in source

    assert "`/me/reports/${encodeURIComponent(reportId)}`" in source

    assert "idempotencyKey," in source


def test_reporting_module_files_exist():
    root = ROOT / "apps" / "public-mobile"

    for relative in (
        "src/reporting/index.ts",
        "src/reporting/reporting-types.ts",
        "src/reporting/reporting-presenter.ts",
        "src/reporting/reporting-queries.ts",
    ):
        assert (root / relative).is_file()


def test_reporting_reasons_are_exact():
    source = _read("apps/public-mobile/src/reporting/reporting-types.ts")

    expected = {
        "spam",
        "fraud",
        "malicious_link",
        "abuse",
        "off_topic",
        "duplicate",
        "other",
    }

    for reason in expected:
        assert f'"{reason}"' in source


def test_reporting_statuses_are_exact():
    source = _read("apps/public-mobile/src/reporting/reporting-types.ts")

    for status in (
        "received",
        "under_review",
        "resolved",
    ):
        assert f'"{status}"' in source


def test_read_model_does_not_model_private_fields():
    source = (
        _read("apps/public-mobile/src/reporting/reporting-types.ts")
        + "\n"
        + _read("apps/public-mobile/src/reporting/reporting-presenter.ts")
    )

    for forbidden in (
        "reporter_conta_id",
        "chave_idempotencia",
        "moderator_actor_id",
        "familia_abuso_confirmado",
        "justificativa",
        "authority_origin",
        "community_trust_evidence",
        "community_trust_profiles",
    ):
        assert forbidden not in source


def test_presenter_maps_backend_public_fields():
    source = _read("apps/public-mobile/src/reporting/reporting-presenter.ts")

    for backend_field in (
        '"target_type"',
        '"target_id"',
        '"motivo"',
        '"estado"',
        '"criado_em"',
        '"atualizado_em"',
        '"detalhes"',
    ):
        assert backend_field in source

    assert "presentCommunityReports" in source

    assert "presentCommunityReportDetail" in source

    assert "presentCommunityReportCreate" in source


def test_reporting_query_hooks_exist():
    source = _read("apps/public-mobile/src/reporting/reporting-queries.ts")

    for hook in (
        "useCommunityReports",
        "useCommunityReport",
        "useCreateCommunityReport",
    ):
        assert hook in source

    assert "communityReportQueryKeys" in source

    assert "invalidateQueries" in source

    assert "setQueryData" in source


def test_idempotency_key_generated_in_client_layer():
    source = _read("apps/public-mobile/src/reporting/reporting-queries.ts")

    assert 'import * as Crypto from "expo-crypto";' in source

    assert "Crypto.randomUUID()" in source

    assert "`mobile-${Crypto.randomUUID()}`" in source


def test_8e11a_does_not_add_ui():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["ui_boundary"]["screen_changed"] is False

    assert data["ui_boundary"]["route_changed"] is False

    assert data["ui_boundary"]["visual_surface_added"] is False


def test_backend_and_live_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    backend = data["backend_boundary"]

    assert backend["backend_code_changed"] is False

    assert backend["database_changed"] is False

    assert backend["schema_changed"] is False

    assert backend["runtime_restart"] is False

    assert backend["live_canary"] is False

    assert backend["live_database_write"] is False


def test_next_steps_are_only_8e11b_and_8e11c():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["planned_followups"] == {
        "8E11B": "report-submission-surface",
        "8E11C": "report-status-history-surface",
    }

    assert data["next_step"] == "8E11B-report-submission-surface"


def test_8e11a_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E11B-report-submission-surface"

    validation = data["validation"]

    assert validation["baseline_commit"] == "520034c"

    assert validation["partial_failure_recovered"] is True

    assert validation["api_types_reapplied"] is False

    assert validation["structural_audit_passed"] is True

    assert validation["pre_commit_passed"] is True

    assert validation["public_app_typecheck_passed"] is True

    assert validation["isolated_8e11a_cases_passed_pre_closure"] == 13

    assert validation["public_mobile_test_files"] == 4

    assert validation["public_mobile_regression_cases_passed_pre_closure"] == 36

    assert validation["backend_reporting_cases_passed"] == 70

    assert validation["http_transport_idempotency_header"] is True

    assert validation["public_api_list_reports"] is True

    assert validation["public_api_get_report"] is True

    assert validation["public_api_create_report"] is True

    assert validation["reporting_types"] is True

    assert validation["reporting_presenter"] is True

    assert validation["reporting_react_query"] is True

    assert validation["generic_custom_headers"] is False

    assert validation["idempotency_key_exposed_to_ui"] is False

    assert validation["reporter_id_modeled"] is False

    assert validation["moderator_actor_modeled"] is False

    assert validation["moderation_result_modeled"] is False

    assert validation["moderator_justification_modeled"] is False

    assert validation["trust_internal_data_modeled"] is False

    assert validation["public_app_screen_changed"] is False

    assert validation["public_app_route_changed"] is False

    assert validation["report_submission_ui"] is False

    assert validation["report_history_ui"] is False

    assert validation["backend_code_changed"] is False

    assert validation["database_changed"] is False

    assert validation["schema_changed"] is False

    assert validation["runtime_restart"] is False

    assert validation["live_canary"] is False

    assert validation["live_database_write"] is False

    assert validation["live_schema_write"] is False

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_8e11a_cases_after_closure"] == 14

    assert closure["expected_public_mobile_regression_cases_after_closure"] == 37

    assert closure["expected_backend_reporting_cases_after_closure"] == 70

    assert closure["expected_public_mobile_test_files_after_closure"] == 4
