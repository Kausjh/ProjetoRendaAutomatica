from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.gamification_production_rules import (
    criar_ruleset_producao_v1,
)
from services.mission_production_catalog import (
    COMMUNITY_APPROVED_EVENT,
    INSTANCE_KEY,
    INSTANCE_POLICY,
    MAX_LIFETIME_REWARD_XP,
    MISSION_RULESET_VERSION,
    criar_catalogo_missoes_producao_v1,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "missions_community_rewards_catalog_v1.json"

DOC = ROOT / "docs" / "56-missions-community-rewards-catalog-v1.md"


def test_catalogo_producao_exato():
    catalogo = criar_catalogo_missoes_producao_v1()

    assert catalogo.ruleset.versao == MISSION_RULESET_VERSION

    assert [
        (
            missao.codigo,
            missao.alvo,
            missao.recompensa_xp,
        )
        for missao in catalogo.ruleset.missoes
    ] == [
        (
            "community_primeira_aprovada",
            1,
            20,
        ),
        (
            "community_cinco_aprovadas",
            5,
            50,
        ),
        (
            "community_dez_aprovadas",
            10,
            100,
        ),
    ]


def test_apenas_approved_alimenta_catalogo():
    catalogo = criar_catalogo_missoes_producao_v1()

    assert all(
        missao.tipo_evento == COMMUNITY_APPROVED_EVENT for missao in catalogo.ruleset.missoes
    )

    assert catalogo.ruleset.listar_por_evento("community_discovery_received") == ()

    assert catalogo.ruleset.listar_por_evento("community_discovery_retry") == ()

    assert catalogo.ruleset.listar_por_evento("community_discovery_rejected") == ()


def test_politica_de_instancia_e_lifetime():
    catalogo = criar_catalogo_missoes_producao_v1()

    assert catalogo.politica_instancia == INSTANCE_POLICY

    assert INSTANCE_POLICY == ("account_lifetime")

    assert catalogo.instancia_chave == (INSTANCE_KEY)

    assert INSTANCE_KEY == "lifetime"

    for missao in catalogo.ruleset.missoes:
        assert catalogo.derivar_instancia_chave(missao.codigo) == "lifetime"

    with pytest.raises(ValueError):
        catalogo.derivar_instancia_chave("missao_inexistente")


def test_teto_total_de_xp_e_170():
    catalogo = criar_catalogo_missoes_producao_v1()

    assert catalogo.xp_total_lifetime == 170

    assert catalogo.xp_total_lifetime == MAX_LIFETIME_REWARD_XP


def test_reward_policy_bate_com_missoes():
    catalogo = criar_catalogo_missoes_producao_v1()

    event_types = []

    for missao in catalogo.ruleset.missoes:
        reward = catalogo.recompensa_para(missao.codigo)

        assert reward.xp == missao.recompensa_xp

        assert reward.evento_gamificacao == ("mission_reward_" + missao.codigo)

        event_types.append(reward.evento_gamificacao)

    assert len(event_types) == len(set(event_types))


def test_chave_idempotencia_de_aprovacao():
    catalogo = criar_catalogo_missoes_producao_v1()

    assert catalogo.chave_idempotencia_aprovacao("cd_123") == "v1:community-approved:cd_123"

    with pytest.raises(ValueError):
        catalogo.chave_idempotencia_aprovacao("")


def test_economia_nao_cria_farm_ilimitado():
    catalogo = criar_catalogo_missoes_producao_v1()

    gamification = criar_ruleset_producao_v1()

    xp_inicial = 140

    xp_final = xp_inicial + catalogo.xp_total_lifetime

    assert xp_final == 310

    assert gamification.calcular_nivel(xp_inicial) == 2

    assert gamification.calcular_nivel(xp_final) == 3


def test_contract_define_politica_7b():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == ("7B-production-mission-catalog-" "reward-policy")

    assert data["instance_policy"]["scope"] == "account_lifetime"

    assert data["instance_policy"]["recurring"] is False

    assert data["community_event_policy"]["count_status"] == "approved"

    assert data["community_event_policy"]["count_received"] is False

    assert data["community_event_policy"]["count_retry"] is False

    assert data["community_event_policy"]["count_rejected"] is False

    assert data["reward_policy"]["lifetime_cap_xp"] == 170

    assert data["reward_policy"]["reputation"] == 0

    assert data["reward_policy"]["settlement_to_gamification"] is False

    assert data["reconciliation_policy"]["existing_approved"] is True

    boundaries = data["boundaries"]

    assert boundaries["community_discovery_wiring"] is False

    assert boundaries["gamification_rules_extended"] is False

    assert boundaries["runtime_wiring"] is False

    assert boundaries["community_reputation"] is False

    assert boundaries["contributor_trust"] is False

    assert data["next_step"] == ("7C-community-approved-wiring-" "reconciliation")


def test_documentacao_preserva_boundary():
    source = DOC.read_text(encoding="utf-8")

    assert "community_discovery_approved" in source

    assert "instancia_chave = lifetime" in source

    assert "170 XP" in source

    assert "nao liquida" in source

    assert "7C - Community Approved Wiring" in source
