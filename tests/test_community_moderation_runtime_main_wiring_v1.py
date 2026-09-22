from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import runtime as runtime_module

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_runtime_main_wiring_v1.json"

RUNTIME_PATH = ROOT / "runtime.py"

ENV_EXAMPLE = ROOT / ".env.example"

SCHEMA_CONTRACT = ROOT / "contracts" / "community_moderation_live_schema_activation_v1.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_contract_8e8a_boundaries():
    data = _contract()

    assert data["stage"] == "8E8A-runtime-main-wiring-behind-flag"

    assert data["status"] == "completed"

    assert data["activation"]["feature_flag_default_enabled"] is False

    assert data["activation"]["flag_off_returns_before_repository_construction"] is True

    assert data["activation"]["real_activation_this_stage"] is False

    assert data["boundaries"]["live_database_write"] is False

    assert data["boundaries"]["live_bridge_activation"] is False

    assert data["boundaries"]["live_reconciliation_execution"] is False


def test_runtime_imports_controlled_moderation_wiring():
    source = RUNTIME_PATH.read_text(encoding="utf-8")

    assert "from services.community_moderation_runtime import (" in source

    assert "ResultadoAtivacaoCommunityModeration" in source

    assert "ativar_community_moderation_runtime" in source

    assert "def _ativar_community_moderation_controlado(" in source


def test_helper_passes_exact_safe_activation_arguments(
    monkeypatch,
    tmp_path,
):
    calls = {}

    resultado = SimpleNamespace(
        ativo=False,
        erro="feature_flag_disabled",
        reconciliation_executada=False,
    )

    def fake_ativar(**kwargs):
        calls.update(kwargs)
        return resultado

    monkeypatch.setattr(
        runtime_module,
        "ativar_community_moderation_runtime",
        fake_ativar,
    )

    caminho = str(tmp_path / "user_identity.sqlite3")

    returned = runtime_module._ativar_community_moderation_controlado(
        caminho_banco=caminho,
    )

    assert returned is resultado

    assert calls == {
        "caminho_banco": caminho,
        "permitir_schema_activation": True,
        "executar_reconciliation": False,
    }


def test_helper_does_not_promote_disabled_result(
    monkeypatch,
):
    resultado = SimpleNamespace(
        ativo=False,
        erro="feature_flag_disabled",
        reconciliation_executada=False,
    )

    monkeypatch.setattr(
        runtime_module,
        "ativar_community_moderation_runtime",
        lambda **kwargs: resultado,
    )

    returned = runtime_module._ativar_community_moderation_controlado(
        caminho_banco="nao-usado.sqlite3",
    )

    assert returned.ativo is False
    assert returned.erro == "feature_flag_disabled"


def test_main_calls_controlled_wiring_once_before_public_api():
    source = RUNTIME_PATH.read_text(encoding="utf-8")

    tree = ast.parse(source)

    main = next(
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name == "main"
        )
    )

    moderation_calls = [
        node
        for node in ast.walk(main)
        if (
            isinstance(
                node,
                ast.Call,
            )
            and isinstance(
                node.func,
                ast.Name,
            )
            and node.func.id == "_ativar_community_moderation_controlado"
        )
    ]

    api_calls = [
        node
        for node in ast.walk(main)
        if (
            isinstance(
                node,
                ast.Call,
            )
            and isinstance(
                node.func,
                ast.Name,
            )
            and node.func.id == "ServidorApiAplicacao"
        )
    ]

    assert len(moderation_calls) == 1
    assert len(api_calls) == 1

    assert moderation_calls[0].lineno < api_calls[0].lineno


def test_env_example_keeps_moderation_flags_off():
    source = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "COMMUNITY_MODERATION_RUNTIME_ATIVO=0" in source

    assert "COMMUNITY_MODERATION_RECONCILIATION_STARTUP_ATIVA=0" in source


def test_8e7_is_completed_before_main_wiring():
    data = json.loads(SCHEMA_CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["activation"]["moderation_tables"] == [
        "community_moderation_decisions",
        "community_moderation_reports",
    ]

    assert data["activation"]["moderation_report_rows"] == 0

    assert data["activation"]["moderation_decision_rows"] == 0


def test_8e8a_does_not_wire_reconciliation_or_http_surface():
    data = _contract()

    assert data["reconciliation"]["explicit_override_in_main"] is True

    assert data["reconciliation"]["automatic_reconciliation_possible_in_8e8a"] is False

    assert data["boundaries"]["moderation_service_exposed_to_http"] is False

    assert data["boundaries"]["admin_http_integration"] is False

    assert data["boundaries"]["public_report_api_integration"] is False


def test_8e8a_closure_metadata():
    data = _contract()

    assert data["status"] == "completed"

    assert data["next_step"] == "8E8B-controlled-live-bridge-activation"

    reconciliation = data["reconciliation"]

    assert reconciliation["explicit_override_in_main"] is True

    assert reconciliation["explicit_override_value"] is False

    assert reconciliation["startup_environment_flag_can_trigger_reconciliation_from_main"] is False

    validation = data["validation"]

    assert validation["baseline"] == "43bc0bc"

    assert validation["isolated_tests_passed_pre_closure"] == 8

    assert validation["stage_8e_tests_passed_pre_closure"] == 93

    assert validation["trust_moderation_tests_passed_pre_closure"] == 142

    assert validation["main_controlled_call_count"] == 1

    assert validation["runtime_feature_flag_default_off"] is True

    assert validation["runtime_real_flag_off"] is True

    assert validation["reconciliation_real_flag_off"] is True

    assert validation["reconciliation_explicitly_disabled_in_main"] is True

    assert validation["reconciliation_explicit_override_value"] is False

    assert validation["runtime_restart"] is False

    assert validation["live_runtime_activation"] is False

    assert validation["live_trust_bridge_activation"] is False

    assert validation["live_reconciliation_execution"] is False

    assert validation["live_database_write"] is False
