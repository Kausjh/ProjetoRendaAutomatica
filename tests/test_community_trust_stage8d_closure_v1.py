from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLOSURE = ROOT / "contracts" / "community_trust_stage8d_closure_v1.json"


def test_stage8d_final_closure_contract():
    data = json.loads(CLOSURE.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["stage"] == "8D-community-trust-wiring-reconciliation-runtime"

    scope = data["scope"]

    assert scope["8D1_atomic_decision_and_ledger_write"] is True

    assert scope["8D2_terminal_hook"] is True
    assert scope["8D3_reconciliation_core"] is True

    assert scope["8D3_historical_live_backfill"] is True

    assert scope["8D4_real_runtime_activation"] is True

    backfill = data["historical_backfill_8D3B"]

    assert backfill["executed"] is True
    assert backfill["candidates_processed"] == 2
    assert backfill["evidences_created"] == 2
    assert backfill["failures"] == 0
    assert backfill["second_run_noop"] is True

    live = data["live_state_at_closure"]

    assert live["query_only"] is True
    assert live["integrity_check"] == "ok"
    assert live["foreign_key_errors"] == 0
    assert live["backfill_candidates"] == 0

    assert live["terminals_with_evidence"] == live["terminal_total"]

    assert live["duplicate_idempotency_keys"] == 0

    assert live["orphan_origins"] == 0
    assert live["profile_ledger_mismatch"] == 0

    assert live["evidence_total"] >= 2
    assert live["profile_total"] >= 1

    runtime = data["runtime"]

    assert runtime["real_scraper_wiring_active"] is True

    assert runtime["terminal_hook_injected"] is True

    assert runtime["mission_approval_hook_preserved"] is True

    assert runtime["mission_and_trust_hooks_separate"] is True

    assert runtime["composition_failure_mode"] == "fail-open"

    assert runtime["reconciliation_recovery_path"] is True

    boundaries = data["safety_boundaries"]

    assert boundaries["moderation_authority"] is False

    assert boundaries["confirmed_abuse_authority"] is False

    assert boundaries["gamification_write"] is False

    assert boundaries["reputation_total_write"] is False

    assert data["next_step"] == "8E-moderation-reporting-foundation"
