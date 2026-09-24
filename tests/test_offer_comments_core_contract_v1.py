from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "offer_comments_core_v1.json"

DOC = ROOT / "docs" / "91-offer-comments-core-v1.md"

MODERATION = ROOT / "contracts" / "community_moderation_model_v1.json"

ABUSE = ROOT / "services" / "api_aplicacao" / "user_facing_abuse_controls.py"


def load() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_offer_comments_contract_identity():
    data = load()

    assert data["stage"] == "phase2-item9-offer-comments-core-v1"

    assert data["status"] == "contract-frozen-implementation-pending"

    assert data["baseline_commit"] == "8564bef"

    assert data["roadmap_item"] == 9


def test_contract_does_not_create_hidden_roadmap_levels():
    data = load()

    hierarchy = data["roadmap_hierarchy"]

    assert hierarchy["new_roadmap_sublevel_created"] is False

    assert hierarchy["hidden_sublevels_created"] is False

    assert hierarchy["contract_is_implementation_unit_only"] is True

    assert data["implementation_order_is_roadmap_sublevels"] is False


def test_v1_target_is_canonical_and_cross_db_safe():
    data = load()

    target = data["target"]

    assert target["v1_target_kind"] == "canonical_product"

    assert target["key_name"] == "canonical_key"

    assert target["source"] == "produtos_canonicos.chave_canonica"

    assert target["databases_are_separate"] is True

    assert target["cross_database_foreign_key"] is False

    assert target["existence_validation_required_server_side"] is True


def test_authority_is_server_derived_and_private():
    data = load()

    identity = data["identity"]

    assert identity["authentication_required_for_write"] is True

    assert identity["author_account_source"] == "contas_usuario.id"

    assert identity["author_account_is_server_derived"] is True

    assert identity["client_selects_author_account"] is False

    assert identity["internal_account_id_public"] is False

    assert identity["email_public"] is False


def test_threads_are_shallow_and_non_cyclic():
    data = load()

    threading = data["threading"]

    assert threading["root_comments"] is True

    assert threading["direct_replies"] is True

    assert threading["maximum_depth"] == 1

    assert threading["reply_to_reply"] is False

    assert threading["cycles_allowed"] is False

    assert threading["parent_must_share_same_canonical_key"] is True

    assert threading["parent_must_be_root"] is True


def test_content_is_bounded_plain_text():
    data = load()

    content = data["content"]

    assert content["format"] == "plain_text"

    assert content["maximum_chars"] == 1000

    assert content["html"] is False
    assert content["markdown"] is False
    assert content["rich_text"] is False

    assert content["automatic_link_rendering"] is False

    assert content["nul_character_allowed"] is False


def test_revision_history_is_append_only():
    data = load()

    persistence = data["persistence_design"]

    assert persistence["planned_tables"] == [
        "offer_comments",
        "offer_comment_revisions",
    ]

    assert persistence["revision_ledger_append_only"] is True

    assert persistence["edit_overwrites_prior_revision"] is False

    assert persistence["delete_is_soft_delete"] is True

    assert persistence["normal_public_hard_delete"] is False


def test_public_read_model_minimizes_identity():
    data = load()

    read_model = data["read_model"]

    assert read_model["pagination"] is True

    assert read_model["default_root_limit"] == 20

    assert read_model["maximum_root_limit"] == 100

    internal = set(read_model["internal_fields_not_public"])

    assert "author_account_id" in internal
    assert "email" in internal
    assert "revision_id" in internal
    assert "idempotency_key" in internal


def test_write_idempotency_is_required():
    data = load()

    idem = data["write_idempotency"]

    assert idem["required_for_create"] is True

    assert idem["required_for_edit"] is True

    assert idem["request_identifier_public_in_read_model"] is False

    assert idem["duplicate_retry_must_not_duplicate_comment"] is True


def test_public_write_is_gated_by_abuse_controls():
    data = load()

    gate = data["anti_abuse_gate"]

    assert gate["public_write_api_can_launch_now"] is False

    assert gate["current_abuse_controls_cover_comments"] is False

    assert gate["must_extend_user_facing_abuse_controls"] is True

    assert gate["per_account_bucket_required"] is True
    assert gate["per_client_bucket_required"] is True
    assert gate["retry_after_required"] is True

    assert gate["duplicate_content_window_required"] is True

    abuse = ABUSE.read_text(encoding="utf-8")

    assert "def avaliar_register(" in abuse
    assert "def avaliar_login(" in abuse
    assert "def avaliar_comment" not in abuse


def test_comment_moderation_is_reserved_but_not_live():
    data = load()

    gate = data["moderation_gate"]

    assert gate["comment_target_reserved_in_existing_contract"] is True

    assert gate["comment_target_live_supported_now"] is False

    assert gate["existing_live_supported_target"] == "community_discovery"

    assert gate["public_comment_write_launch_requires_comment_reporting"] is True

    assert gate["public_comment_write_launch_requires_comment_moderation"] is True

    moderation = json.loads(MODERATION.read_text(encoding="utf-8"))

    assert moderation["target"]["supported_types_v1"] == ["community_discovery"]

    assert "comment" in moderation["target"]["future_social_targets_reserved"]


def test_comments_do_not_gain_direct_trust_or_price_authority():
    data = load()

    trust = data["trust_and_gamification"]

    assert trust["comment_creation_directly_changes_trust"] is False

    assert trust["comment_creation_directly_changes_xp"] is False

    assert trust["client_can_write_trust"] is False

    price = data["price_and_offer_intelligence"]

    assert price["comment_can_override_price_intelligence"] is False

    assert price["comment_can_directly_expire_offer"] is False

    assert price["automatic_price_truth_from_comments"] is False


def test_aegis_and_contract_boundaries():
    data = load()

    security = data["security_review"]

    assert security["protocol"] == "AEGIS"

    assert security["zero_trust"] is True
    assert security["least_privilege"] is True
    assert security["defense_in_depth"] is True
    assert security["assume_breach"] is True
    assert security["data_minimization"] is True
    assert security["fail_closed"] is True

    assert security["moderation_required_before_launch"] is True

    assert security["rate_limiting_required_before_launch"] is True

    assert security["anti_spam_required_before_launch"] is True

    assert security["existing_security_silently_weakened"] is False

    for value in data["boundaries"].values():
        assert value is False


def test_contract_document_and_next_step():
    data = load()

    assert DOC.is_file()

    doc = DOC.read_text(encoding="utf-8")

    assert "CONTRATO CONGELADO. IMPLEMENTACAO PENDENTE." in doc

    assert "Implementar Offer Comments Model + Repository." in doc

    assert data["next_step"] == "implement-offer-comments-model-and-repository"
