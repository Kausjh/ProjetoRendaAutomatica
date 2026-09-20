from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
MISSIONS = APP / "src" / "missions"

CLIENT = APP / "src" / "api" / "public-api-client.ts"
TYPES = MISSIONS / "mission-types.ts"
PRESENTER = MISSIONS / "mission-presenter.ts"
QUERIES = MISSIONS / "mission-queries.ts"
INDEX = MISSIONS / "index.ts"
PANEL = MISSIONS / "mission-panel.tsx"
ACCOUNT = APP / "app" / "account.tsx"

CONTRACT = ROOT / "contracts" / "public_app_missions_surface_v1.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_missions_source_files_exist():
    expected = (
        TYPES,
        PRESENTER,
        QUERIES,
        PANEL,
        INDEX,
    )

    assert all(path.exists() for path in expected)


def test_public_api_client_exposes_authenticated_missions_read():
    source = read(CLIENT)

    assert "getMissions" in source
    assert 'path: "/me/missions"' in source
    assert "requiresUserSession: true" in source
    assert 'responseMode: "user-facing-envelope"' in source


def test_mission_query_uses_public_api_client():
    source = read(QUERIES)

    assert "createPublicApiClient" in source
    assert 'me: ["missions", "me"] as const' in source
    assert "useMissions" in source
    assert "await api.getMissions()" in source
    assert "presentMissions" in source


def test_presenter_maps_server_fields_without_client_authority():
    source = read(PRESENTER)

    expected = (
        "ruleset_version",
        "instancia_chave",
        "resumo",
        "missoes",
        "codigo",
        "titulo",
        "descricao",
        "progresso_atual",
        "progresso_alvo",
        "percentual",
        "concluida",
        "concluida_em",
        "atualizado_em",
        "recompensa",
        "tipo",
        "quantidade",
        "status",
        "concedida_em",
    )

    for value in expected:
        assert value in source


def test_reward_status_is_fail_closed_to_locked():
    source = read(PRESENTER)

    assert '"locked"' in source
    assert 'rawStatus === "pending"' in source
    assert 'rawStatus === "granted"' in source
    assert ': "locked"' in source


def test_types_cover_mission_read_model():
    source = read(TYPES)

    expected = (
        "MissionRewardStatus",
        "MissionReward",
        "MissionItem",
        "MissionsSummary",
        "MissionsSnapshot",
        "currentProgress",
        "targetProgress",
        "percent",
        "completed",
        "reward",
        "rewardsPending",
        "rewardsGranted",
        "rulesetVersion",
        "instanceKey",
    )

    for value in expected:
        assert value in source


def test_missions_layer_does_not_handle_transport_secrets_or_identity():
    combined = "\n".join(
        (
            read(TYPES),
            read(PRESENTER),
            read(QUERIES),
            read(INDEX),
        )
    )

    forbidden = (
        "X-User-Session",
        "Authorization",
        "Bearer ",
        "API_APLICACAO_TOKEN",
        "infrastructureToken",
        "conta_id",
    )

    for value in forbidden:
        assert value not in combined


def test_contract_is_read_only_and_server_authoritative():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["public_app_missions_surface_version"] == 1
    assert data["phase"] == "7F3"
    assert data["status"] == "completed"
    assert data["next_step"] == "7G-operational-close"

    assert data["backend"]["path"] == "/api/v1/me/missions"

    assert data["backend"]["requires_user_session"] is True

    assert data["backend"]["writes_state"] is False

    assert data["architecture"]["dedicated_route"] is False

    assert data["architecture"]["bottom_nav_entry"] is False

    assert data["architecture"]["ui_panel_in_7f2"] is True

    assert data["source_of_truth"]["client_recalculates_progress"] is False

    assert data["source_of_truth"]["client_grants_rewards"] is False

    assert data["supported_reward_statuses"] == [
        "locked",
        "pending",
        "granted",
    ]

    boundaries = data["boundaries"]

    assert boundaries["xp_write"] is False
    assert boundaries["mission_write"] is False
    assert boundaries["reward_settlement"] is False
    assert boundaries["community_reputation"] is False
    assert boundaries["offer_scoring_change"] is False


def test_missions_panel_uses_read_model_and_server_progress():
    source = read(PANEL)

    expected = (
        "MissionsPanel",
        "useMissions",
        "data.summary.completed",
        "data.summary.inProgress",
        "data.summary.rewardsGranted",
        "data.missions.map",
        "mission.currentProgress",
        "mission.targetProgress",
        "mission.percent",
        "mission.reward.status",
        "missions.refetch",
    )

    for value in expected:
        assert value in source


def test_missions_panel_exposes_all_reward_states():
    source = read(PANEL)

    assert "recebido" in source
    assert "pendente" in source
    assert "bloqueado" in source


def test_missions_panel_is_exported():
    source = read(INDEX)

    assert 'export * from "@/src/missions/mission-panel";' in source


def test_account_integrates_missions_panel():
    source = read(ACCOUNT)

    assert 'import { MissionsPanel } from "@/src/missions";' in source

    assert "<MissionsPanel enabled={authenticated} />" in source

    assert source.index("<GamificationPanel") < source.index("<MissionsPanel")


def test_missions_ui_does_not_handle_transport_or_identity():
    combined = "\n".join(
        (
            read(PANEL),
            read(ACCOUNT),
        )
    )

    forbidden = (
        "X-User-Session",
        "Authorization",
        "Bearer ",
        "API_APLICACAO_TOKEN",
        "infrastructureToken",
        "conta_id",
    )

    for value in forbidden:
        assert value not in combined


def test_contract_preserves_7f2_account_panel_in_7f3():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    architecture = data["architecture"]
    ui = data["ui"]

    assert data["phase"] == "7F3"

    assert architecture["panel_component"] == "MissionsPanel"

    assert architecture["integrated_surface"] == "account"

    assert architecture["dedicated_route"] is False
    assert architecture["bottom_nav_entry"] is False

    assert ui["summary_metrics"] is True
    assert ui["mission_progress_bar"] is True

    assert ui["mission_progress_source"] == "server"

    assert ui["reward_status_visible"] is True
    assert ui["manual_refresh"] is True
    assert ui["loading_state"] is True
    assert ui["error_retry_state"] is True


def test_contract_records_7f3_real_android_validation():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["phase"] == "7F3"
    assert data["status"] == "completed"
    assert data["next_step"] == "7G-operational-close"

    validation = data["real_validation"]

    assert validation["validated"] is True
    assert validation["android_version"] == "13"
    assert validation["package"] == "com.rendaautomatica.app"
    assert validation["development_client"] is True
    assert validation["metro_transport"] == "adb-reverse"
    assert validation["api_transport"] == "adb-reverse"
    assert validation["api_health"] == "ok"
    assert validation["runtime_errors_observed"] is False

    assert validation["observed_summary"] == {
        "completed": 1,
        "in_progress": 2,
        "rewards_granted": 1,
    }

    missions = {item["code"]: item for item in validation["observed_missions"]}

    assert missions["community_primeira_aprovada"]["progress"] == "1/1"
    assert missions["community_primeira_aprovada"]["reward_status"] == "granted"

    assert missions["community_cinco_aprovadas"]["progress"] == "1/5"
    assert missions["community_cinco_aprovadas"]["reward_status"] == "locked"

    assert missions["community_dez_aprovadas"]["progress"] == "1/10"
    assert missions["community_dez_aprovadas"]["reward_status"] == "locked"
