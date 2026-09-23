from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_public_app_report_status_history_v1.json"


def _read(
    relative: str,
) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_8e11c_contract_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E11C-report-status-history-surface"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "1b8d54e"

    assert data["source_stage"]["8E11B"] == "completed"


def test_history_and_detail_routes_are_registered():
    layout = _read("apps/public-mobile/app/_layout.tsx")

    assert layout.count('name="reports"') == 1

    assert layout.count('name="report-status"') == 1


def test_account_exposes_report_history_entry():
    account = _read("apps/public-mobile/app/account.tsx")

    assert "Minhas denúncias" in account

    assert 'router.push("/reports" as never)' in account

    assert 'name="flag-outline"' in account


def test_history_uses_authenticated_reporting_hook():
    history = _read("apps/public-mobile/app/reports.tsx")

    assert "useAuthSession" in history

    assert "useCommunityReports" in history

    assert "snapshot.status === " '"authenticated"' in history

    assert '<Redirect href="/" />' in history


def test_history_requests_up_to_one_hundred_reports():
    history = _read("apps/public-mobile/app/reports.tsx")

    assert "const reports = useCommunityReports(" in history

    assert "    100," in history

    assert "    0," in history

    assert "RefreshControl" in history

    assert "reports.refetch()" in history


def test_history_maps_public_status_and_reason():
    history = _read("apps/public-mobile/app/reports.tsx")

    for status in (
        "received",
        "under_review",
        "resolved",
    ):
        assert f"{status}:" in history

    for reason in (
        "spam",
        "fraud",
        "malicious_link",
        "abuse",
        "off_topic",
        "duplicate",
        "other",
    ):
        assert f"{reason}:" in history


def test_history_navigates_to_owned_report_detail():
    history = _read("apps/public-mobile/app/reports.tsx")

    assert 'pathname: "/report-status"' in history

    assert "reportId: item.id" in history


def test_detail_uses_authenticated_single_report_hook():
    detail = _read("apps/public-mobile/app/report-status.tsx")

    assert "useAuthSession" in detail

    assert "useLocalSearchParams" in detail

    assert "useCommunityReport" in detail

    assert "reportId" in detail

    assert '<Redirect href="/" />' in detail


def test_detail_status_labels_are_exact():
    detail = _read("apps/public-mobile/app/report-status.tsx")

    assert 'received: "Recebida"' in detail

    assert 'under_review: "Em análise"' in detail

    assert 'resolved: "Concluída"' in detail


def test_detail_shows_original_details_without_internal_fields():
    detail = _read("apps/public-mobile/app/report-status.tsx")

    assert "item.details" in detail

    forbidden = (
        "reporter_conta_id",
        "chave_idempotencia",
        "moderator_actor_id",
        "familia_abuso_confirmado",
        "authority_origin",
        "community_trust_evidence",
        "community_trust_profiles",
    )

    for marker in forbidden:
        assert marker not in detail


def test_resolved_is_not_presented_as_abuse_confirmation():
    detail = _read("apps/public-mobile/app/report-status.tsx")

    assert "Este status não informa, por si só, " "se houve confirmação de abuso." in detail

    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["public_statuses"]["resolved_is_not_presented_as_abuse_confirmation"] is True


def test_8e11c_is_read_only_and_completes_8e11_surface():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    boundary = data["read_only_boundary"]

    assert boundary["report_creation_changed"] is False

    assert boundary["report_submission_ui_changed"] is False

    assert boundary["backend_changed"] is False

    assert boundary["database_changed"] is False

    assert boundary["schema_changed"] is False

    assert boundary["live_database_write"] is False

    assert data["stage_completion"]["completes_8E11_public_app_reporting_surface"] is True

    assert data["next_step"] == "8E12A-operational-closure"


def test_8e11c_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E12A-operational-closure"

    validation = data["validation"]

    assert validation["baseline_commit"] == "1b8d54e"

    assert validation["structural_audit_passed"] is True

    assert validation["pre_commit_passed"] is True

    assert validation["public_app_typecheck_passed"] is True

    assert validation["isolated_8e11c_cases_passed_pre_closure"] == 12

    assert validation["public_mobile_test_files"] == 6

    assert validation["public_mobile_regression_cases_passed_pre_closure"] == 60

    assert validation["backend_reporting_cases_passed"] == 70

    assert validation["account_history_entry"] is True

    assert validation["report_history_route"] == "/reports"

    assert validation["report_detail_route"] == "/report-status"

    assert validation["history_hook"] == "useCommunityReports"

    assert validation["detail_hook"] == "useCommunityReport"

    assert validation["report_history_limit"] == 100

    assert validation["pull_to_refresh"] is True

    assert validation["resolved_means_abuse_confirmed"] is False

    assert validation["original_user_details_visible"] is True

    assert validation["reporter_id_exposed"] is False

    assert validation["idempotency_key_exposed"] is False

    assert validation["moderator_actor_exposed"] is False

    assert validation["moderation_result_exposed"] is False

    assert validation["moderator_justification_exposed"] is False

    assert validation["authority_origin_exposed"] is False

    assert validation["trust_internal_data_exposed"] is False

    assert validation["report_creation_changed"] is False

    assert validation["report_submission_ui_changed"] is False

    assert validation["backend_changed"] is False

    assert validation["database_changed"] is False

    assert validation["schema_changed"] is False

    assert validation["runtime_restart"] is False

    assert validation["live_canary"] is False

    assert validation["live_database_write"] is False

    assert validation["live_schema_write"] is False

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0

    assert validation["completes_8e11_public_app_reporting_surface"] is True

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_8e11c_cases_after_closure"] == 13

    assert closure["expected_public_mobile_regression_cases_after_closure"] == 61

    assert closure["expected_backend_reporting_cases_after_closure"] == 70

    assert closure["expected_public_mobile_test_files_after_closure"] == 6

    assert closure["8E11A"] == "completed"
    assert closure["8E11B"] == "completed"
    assert closure["8E11C"] == "completed"
    assert closure["8E11"] == "completed"
