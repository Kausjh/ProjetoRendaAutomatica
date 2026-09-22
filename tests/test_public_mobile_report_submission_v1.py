from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_public_app_report_submission_v1.json"


def _read(
    relative: str,
) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_8e11b_contract_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E11B-report-submission-surface"

    assert data["status"] == "completed"

    assert data["baseline_commit"] == "e63344d"

    assert data["source_stage"]["8E11A"] == "completed"


def test_report_route_is_registered():
    layout = _read("apps/public-mobile/app/_layout.tsx")

    assert 'name="report"' in layout

    assert layout.count('name="report"') == 1


def test_discovery_card_exposes_report_action():
    discover = _read("apps/public-mobile/app/discover.tsx")

    assert "Denunciar problema" in discover

    assert 'name="flag-outline"' in discover

    assert "onReport" in discover


def test_discovery_navigation_forwards_target_id():
    discover = _read("apps/public-mobile/app/discover.tsx")

    assert 'pathname: "/report"' in discover

    assert "targetId: item.id" in discover

    assert "targetLabel: hostLabel(item.url)" in discover


def test_report_screen_uses_auth_and_target_params():
    report = _read("apps/public-mobile/app/report.tsx")

    assert "useAuthSession" in report

    assert "useLocalSearchParams" in report

    assert "targetId" in report

    assert "targetLabel" in report

    assert '<Redirect href="/" />' in report


def test_report_reasons_are_exact():
    report = _read("apps/public-mobile/app/report.tsx")

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
        assert f'value: "{reason}"' in report


def test_submission_uses_8e11a_hook():
    report = _read("apps/public-mobile/app/report.tsx")

    assert "useCreateCommunityReport" in report

    assert "createReport.mutateAsync" in report

    assert "targetId," in report

    assert "reason," in report


def test_details_are_optional_and_bounded_in_ui():
    report = _read("apps/public-mobile/app/report.tsx")

    assert "details: details.trim() || null" in report

    assert "maxLength={1000}" in report

    assert "{details.length}/1000" in report


def test_submission_prevents_accidental_repeat():
    report = _read("apps/public-mobile/app/report.tsx")

    assert "createReport.isPending" in report

    assert "submitted" in report

    assert "setSubmitted(true)" in report

    assert "Denúncia enviada" in report


def test_8e11c_scope_is_not_implemented_here():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    boundary = data["scope_boundary"]

    assert boundary["report_history_ui"] is False

    assert boundary["report_status_ui"] is False

    assert boundary["report_detail_ui"] is False

    assert boundary["deferred_to_8E11C"] is True

    assert data["next_step"] == "8E11C-report-status-history-surface"


def test_8e11b_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E11C-report-status-history-surface"

    validation = data["validation"]

    assert validation["baseline_commit"] == "e63344d"

    assert validation["materialized_state_recovered"] is True

    assert validation["implementation_reapplied"] is False

    assert validation["structural_audit_passed"] is True

    assert validation["post_format_audit_passed"] is True

    assert validation["pre_commit_passed"] is True

    assert validation["public_app_typecheck_passed"] is True

    assert validation["isolated_8e11b_cases_passed_pre_closure"] == 10

    assert validation["public_mobile_test_files"] == 5

    assert validation["public_mobile_regression_cases_passed_pre_closure"] == 47

    assert validation["backend_reporting_cases_passed"] == 70

    assert validation["report_entry_surface"] == "/discover"

    assert validation["report_route"] == "/report"

    assert validation["discovery_card_report_action"] is True

    assert validation["user_session_required"] is True

    assert validation["report_reasons"] == 7

    assert validation["report_details_optional"] is True

    assert validation["create_hook"] == "useCreateCommunityReport"

    assert validation["idempotency_managed_by_client_layer"] is True

    assert validation["idempotency_key_exposed_to_ui"] is False

    assert validation["double_submit_pending_blocked"] is True

    assert validation["resubmit_after_success_blocked"] is True

    assert validation["report_is_allegation_only"] is True

    assert validation["report_confirms_abuse"] is False

    assert validation["report_removes_target"] is False

    assert validation["direct_trust_write"] is False

    assert validation["decision_write"] is False

    assert validation["report_history_ui"] is False

    assert validation["report_status_ui"] is False

    assert validation["report_detail_ui"] is False

    assert validation["backend_changed"] is False

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

    assert closure["expected_isolated_8e11b_cases_after_closure"] == 11

    assert closure["expected_public_mobile_regression_cases_after_closure"] == 48

    assert closure["expected_backend_reporting_cases_after_closure"] == 70

    assert closure["expected_public_mobile_test_files_after_closure"] == 5
