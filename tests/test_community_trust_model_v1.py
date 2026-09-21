from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_trust_model_v1.json"
GAMIFICATION_RULES = ROOT / "contracts" / "gamification_reputation_rules_v1.json"
DISCOVERY_CONTRACT = ROOT / "contracts" / "community_discovery_v1.json"
DISCOVERY_MODEL = ROOT / "models" / "community_discovery.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_8a_contract_identity_and_next_step():
    data = load(CONTRACT)

    assert data["community_trust_model_version"] == 1
    assert data["stage"] == "8A-community-trust-model-boundaries"
    assert data["status"] == "completed"
    assert data["next_step"] == "8B-community-trust-core-ledger"


def test_trust_has_its_own_authority():
    data = load(CONTRACT)

    authority = data["authority"]

    assert authority["source_of_truth"] == ("community_trust_evidence_ledger")

    assert authority["gamification_reputation_total_role"] == ("downstream_projection_reserved")

    assert authority["client_can_write_trust"] is False
    assert authority["public_write_api"] is False


def test_rejected_is_not_automatic_negative_evidence():
    data = load(CONTRACT)
    evidence = data["evidence"]

    assert evidence["eligible_terminal_statuses"] == [
        "approved",
        "rejected",
    ]

    assert evidence["rejected_is_automatic_negative"] is False

    assert evidence["rejected_requires_reason_classification"] is True

    assert evidence["technical_or_system_rejection_is_neutral_by_default"] is True


def test_discovery_domain_supports_required_evidence_fields():
    contract = load(DISCOVERY_CONTRACT)

    allowed = contract["status"]["allowed"]

    assert "approved" in allowed
    assert "rejected" in allowed

    model_source = DISCOVERY_MODEL.read_text(encoding="utf-8")

    assert "motivo_status" in model_source
    assert "conta_id" in model_source
    assert "status" in model_source


def test_scoring_is_not_defined_in_8a():
    data = load(CONTRACT)
    scoring = data["scoring"]

    assert scoring["numeric_policy_defined"] is False
    assert scoring["score_formula_defined"] is False

    assert scoring["negative_evidence_requires_classification"] is True

    assert scoring["terminal_status_alone_is_not_policy"] is True


def test_gamification_projection_is_reserved_not_active():
    data = load(CONTRACT)
    projection = data["gamification_projection"]

    assert projection["reputation_total_may_receive_projection_later"] is True

    assert projection["enabled_in_8a"] is False
    assert projection["direct_dual_write"] is False
    assert projection["projection_must_be_server_side"] is True
    assert projection["projection_must_be_idempotent"] is True


def test_existing_gamification_production_reputation_stays_zero():
    rules = load(GAMIFICATION_RULES)

    assert rules["reputation"]["community_reputation_reserved_for_stage_8"] is True

    assert rules["reputation"]["nonzero_delta_rules"] == 0

    for item in rules["rules"]["events"]:
        assert item["reputation"] == 0


def test_8a_preserves_product_boundaries():
    data = load(CONTRACT)
    boundaries = data["boundaries"]

    assert boundaries["runtime_wiring"] is False
    assert boundaries["database_schema_change"] is False
    assert boundaries["gamification_write"] is False
    assert boundaries["community_discovery_write"] is False
    assert boundaries["public_app"] is False
    assert boundaries["moderation_actions"] is False

    assert boundaries["social_reactions_as_objective_trust"] is False

    assert boundaries["offer_scoring_influence"] is False
    assert boundaries["price_intelligence_influence"] is False
