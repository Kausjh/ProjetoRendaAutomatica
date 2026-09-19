from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.gamification import (
    PerfilGamificacao,
)
from services.gamification_achievements import (
    CONQUISTAS_PRODUCAO_V1,
    avaliar_conquistas,
)
from services.gamification_production_rules import (
    NIVEIS_XP_PRODUCAO_V1,
    POLITICAS_EVENTOS_PRODUCAO_V1,
    VERSAO_RULESET_PRODUCAO_V1,
    PoliticaEventoProducao,
    criar_ruleset_producao_v1,
    obter_politica_producao_v1,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "gamification_reputation_rules_v1.json"

DOC = ROOT / "docs" / "49-gamification-reputation-rules-v1.md"


def perfil(
    *,
    xp: int = 0,
    nivel: int = 1,
) -> PerfilGamificacao:
    return PerfilGamificacao(
        conta_id="usr_test",
        xp_total=xp,
        reputacao_total=0,
        nivel=nivel,
        eventos_total=0,
        atualizado_em=None,
    )


def estados_por_codigo(
    *,
    perfil_atual: PerfilGamificacao,
    contagens: dict[str, int],
):
    return {
        item.codigo: item
        for item in avaliar_conquistas(
            perfil=perfil_atual,
            contagens_eventos=contagens,
        )
    }


def test_ruleset_producao_v1_tem_cinco_eventos():
    ruleset = criar_ruleset_producao_v1()

    assert ruleset.versao == VERSAO_RULESET_PRODUCAO_V1

    assert len(ruleset.regras) == 5

    assert {regra.tipo_evento for regra in ruleset.regras} == {
        "onboarding_conta_criada",
        "onboarding_dispositivo_vinculado",
        "onboarding_preferencias_definidas",
        "watchlist_produto_adicionado",
        "watchlist_preco_alvo_definido",
    }


def test_reputacao_permanece_zero_em_todas_as_regras():
    assert all(politica.reputacao_delta == 0 for politica in POLITICAS_EVENTOS_PRODUCAO_V1)

    with pytest.raises(ValueError):
        PoliticaEventoProducao(
            tipo_evento="indevido",
            descricao="Nao permitido.",
            xp_delta=10,
            reputacao_delta=1,
            escopo_idempotencia=("account_lifetime"),
        )


def test_valores_de_xp_v1_sao_exatos():
    assert obter_politica_producao_v1("onboarding_conta_criada").xp_delta == 40

    assert obter_politica_producao_v1("onboarding_dispositivo_vinculado").xp_delta == 20

    assert obter_politica_producao_v1("onboarding_preferencias_definidas").xp_delta == 20

    assert obter_politica_producao_v1("watchlist_produto_adicionado").xp_delta == 20

    assert obter_politica_producao_v1("watchlist_preco_alvo_definido").xp_delta == 10


def test_watchlist_tem_limite_diario_anti_farming():
    produto = obter_politica_producao_v1("watchlist_produto_adicionado")

    alvo = obter_politica_producao_v1("watchlist_preco_alvo_definido")

    assert produto is not None
    assert alvo is not None

    assert produto.limite_por_janela == 10
    assert produto.janela_segundos == 86400

    assert alvo.limite_por_janela == 10
    assert alvo.janela_segundos == 86400


def test_escopos_de_idempotencia_sao_explicitos():
    por_tipo = {
        item.tipo_evento: (item.escopo_idempotencia) for item in POLITICAS_EVENTOS_PRODUCAO_V1
    }

    assert por_tipo["onboarding_conta_criada"] == "account_lifetime"

    assert por_tipo["onboarding_dispositivo_vinculado"] == "account_lifetime"

    assert por_tipo["onboarding_preferencias_definidas"] == "account_lifetime"

    assert por_tipo["watchlist_produto_adicionado"] == "account_canonical_key_lifetime"

    assert por_tipo["watchlist_preco_alvo_definido"] == "account_canonical_key_lifetime"


def test_thresholds_de_nivel_v1_sao_exatos():
    assert NIVEIS_XP_PRODUCAO_V1 == (
        0,
        100,
        250,
        450,
        700,
        1000,
        1400,
        1900,
        2500,
        3200,
    )


def test_calculo_de_nivel_respeita_thresholds_v1():
    ruleset = criar_ruleset_producao_v1()

    assert ruleset.calcular_nivel(0) == 1
    assert ruleset.calcular_nivel(99) == 1
    assert ruleset.calcular_nivel(100) == 2
    assert ruleset.calcular_nivel(249) == 2
    assert ruleset.calcular_nivel(250) == 3
    assert ruleset.calcular_nivel(699) == 4
    assert ruleset.calcular_nivel(700) == 5
    assert ruleset.calcular_nivel(3199) == 9
    assert ruleset.calcular_nivel(3200) == 10
    assert ruleset.calcular_nivel(999999) == 10


def test_primeiro_item_desbloqueia_radar_ligado():
    estados = estados_por_codigo(
        perfil_atual=perfil(),
        contagens={"watchlist_produto_adicionado": 1},
    )

    assert estados["radar_ligado"].desbloqueada is True

    assert estados["lista_5"].desbloqueada is False


def test_cinco_e_dez_itens_desbloqueiam_marcos():
    estados_5 = estados_por_codigo(
        perfil_atual=perfil(),
        contagens={"watchlist_produto_adicionado": 5},
    )

    assert estados_5["lista_5"].desbloqueada is True

    assert estados_5["lista_10"].desbloqueada is False

    estados_10 = estados_por_codigo(
        perfil_atual=perfil(),
        contagens={"watchlist_produto_adicionado": 10},
    )

    assert estados_10["lista_10"].desbloqueada is True


def test_setup_completo_exige_quatro_marcos():
    incompleto = estados_por_codigo(
        perfil_atual=perfil(),
        contagens={
            "onboarding_conta_criada": 1,
            "onboarding_dispositivo_vinculado": 1,
            "onboarding_preferencias_definidas": 1,
        },
    )

    assert incompleto["setup_completo"].desbloqueada is False

    completo = estados_por_codigo(
        perfil_atual=perfil(),
        contagens={
            "onboarding_conta_criada": 1,
            "onboarding_dispositivo_vinculado": 1,
            "onboarding_preferencias_definidas": 1,
            "watchlist_produto_adicionado": 1,
        },
    )

    assert completo["setup_completo"].desbloqueada is True


def test_nivel_cinco_desbloqueia_badge():
    antes = estados_por_codigo(
        perfil_atual=perfil(
            xp=699,
            nivel=4,
        ),
        contagens={},
    )

    assert antes["nivel_5"].desbloqueada is False

    depois = estados_por_codigo(
        perfil_atual=perfil(
            xp=700,
            nivel=5,
        ),
        contagens={},
    )

    assert depois["nivel_5"].desbloqueada is True


def test_codigos_de_conquista_sao_unicos():
    codigos = [item.codigo for item in CONQUISTAS_PRODUCAO_V1]

    assert len(codigos) == len(set(codigos))


def test_contract_preserva_fronteiras_6b():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "production-rules-and-achievements"

    assert data["rules"]["production_rules_defined"] is True

    assert data["reputation"]["nonzero_delta_rules"] == 0

    assert data["reputation"]["community_reputation_reserved_for_stage_8"] is True

    assert data["boundaries"]["runtime_wiring"] is False

    assert data["boundaries"]["public_api"] is False

    assert data["boundaries"]["public_app"] is False

    assert data["boundaries"]["missions"] is False

    assert data["boundaries"]["community_reputation"] is False


def test_contract_nao_pontua_community_discovery():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    tipos = {item["type"] for item in data["rules"]["events"]}

    assert all("community" not in tipo for tipo in tipos)

    assert "community_discovery_submit" in data["excluded_events"]


def test_documentacao_separa_xp_de_reputacao():
    source = DOC.read_text(encoding="utf-8")

    assert "XP representa progressao de uso." in source

    assert "Reputacao nao e um segundo " "nome para XP." in source

    assert "Etapa 7" in source
    assert "Etapa 8" in source
