from __future__ import annotations

import ast
import json
from pathlib import Path

import services.runtime.orquestrador as runtime_config_module
from services.runtime.orquestrador import (
    ConfiguracoesRuntime,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "missions_community_rewards_settlement_wiring_v1.json"

FLAG = "RUNTIME_MISSION_REWARD_SETTLEMENT_ATIVO"


def test_config_settlement_fail_closed_por_padrao(
    monkeypatch,
):
    monkeypatch.setattr(
        runtime_config_module,
        "load_dotenv",
        lambda *args, **kwargs: False,
    )

    monkeypatch.delenv(
        FLAG,
        raising=False,
    )

    config = ConfiguracoesRuntime.carregar()

    assert config.mission_reward_settlement_ativo is False


def test_config_settlement_pode_ser_habilitado(
    monkeypatch,
):
    monkeypatch.setattr(
        runtime_config_module,
        "load_dotenv",
        lambda *args, **kwargs: False,
    )

    monkeypatch.setenv(
        FLAG,
        "true",
    )

    config = ConfiguracoesRuntime.carregar()

    assert config.mission_reward_settlement_ativo is True


def test_runtime_importa_settlement_e_preserva_ordem():
    text = (ROOT / "runtime.py").read_text(encoding="utf-8")

    assert "from services." "mission_reward_settlement_runtime import" in text

    gamification_pos = text.index("gamification_runtime = " "ativar_gamificacao_runtime(")

    missions_pos = text.index("mission_runtime = " "ativar_missoes_runtime(")

    settlement_pos = text.index("reward_settlement_runtime = None")

    feed_pos = text.index("personalized_feed_service " "= PersonalizedFeedService(")

    assert gamification_pos < missions_pos < settlement_pos < feed_pos


def test_runtime_settlement_tem_flag_e_preconditions():
    text = (ROOT / "runtime.py").read_text(encoding="utf-8")

    assert "if configuracoes." "mission_reward_settlement_ativo:" in text

    assert "gamification_runtime.ativo" in text

    assert "mission_runtime.ativo" in text

    assert "mission_runtime.service is not None" in text

    assert "Mission reward settlement " "desativado por feature flag." in text

    assert "Mission reward settlement bloqueado" in text


def test_runtime_main_possui_uma_chamada_settlement():
    tree = ast.parse((ROOT / "runtime.py").read_text(encoding="utf-8"))

    calls = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        func = node.func

        if isinstance(func, ast.Name):
            if func.id == "ativar_reward_settlement_runtime":
                calls.append(node)

    assert len(calls) == 1


def test_contract_7d3_preserva_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "7D3-controlled-runtime-wiring"

    feature = data["feature_flag"]

    assert feature["name"] == FLAG

    assert feature["default"] is False
    assert feature["fail_closed"] is True

    ordering = data["ordering"]

    assert ordering["gamification_first"] is True
    assert ordering["missions_second"] is True

    assert ordering["reward_settlement_third"] is True

    assert ordering["personalized_feed_after"] is True

    boundaries = data["boundaries"]

    assert boundaries["runtime_py_wiring_present"] is True

    assert boundaries["runtime_configuration_present"] is True

    assert boundaries["feature_flag_enabled_in_production"] is False

    assert boundaries["production_activation_run"] is False

    assert boundaries["production_database_mutation"] is False

    assert boundaries["real_reward_settled"] is False

    assert boundaries["runtime_restart_performed"] is False

    expected = data["expected_first_controlled_activation"]

    assert expected["gamification_xp_after"] == 160

    assert expected["gamification_events_after"] == 8

    assert expected["community_reputation_after"] == 0

    assert data["next_step"] == "7D4-controlled-production-activation"
