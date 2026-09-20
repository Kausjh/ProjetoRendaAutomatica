from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from repositories.gamification_repository import (
    GamificationRepository,
)
from repositories.mission_repository import (
    MissionRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.gamification_production_rules import (
    criar_ruleset_producao_v1,
)
from services.gamification_service import (
    ConflitoEventoGamificacao,
    GamificationService,
)
from services.mission_production_catalog import (
    criar_catalogo_missoes_producao_v1,
)
from services.mission_reward_settlement_service import (
    SETTLEMENT_KEY_PREFIX,
    SETTLEMENT_ORIGIN,
    SETTLEMENT_RULESET_VERSION,
    MissionRewardSettlementService,
    criar_ruleset_gamificacao_com_rewards_missoes_v1,
)
from services.mission_service import (
    MissionService,
)
from services.user_identity_service import (
    UserIdentityService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "missions_community_rewards_settlement_v1.json"


def criar_contexto(
    tmp_path: Path,
):
    banco = tmp_path / "user_identity.sqlite3"

    identity_repository = UserIdentityRepository(banco)

    conta = UserIdentityService(identity_repository).criar_conta(
        email=("settlement@example.com"),
        senha=("senha-segura-123"),
    )

    catalogo = criar_catalogo_missoes_producao_v1()

    mission_service = MissionService(
        MissionRepository(banco),
        identity_repository,
        catalogo.ruleset,
    )

    settlement_ruleset = criar_ruleset_gamificacao_com_rewards_missoes_v1(catalogo)

    gamification_service = GamificationService(
        GamificationRepository(banco),
        identity_repository,
        settlement_ruleset,
    )

    settlement = MissionRewardSettlementService(
        mission_service=(mission_service),
        gamification_service=(gamification_service),
        catalogo=catalogo,
    )

    return (
        banco,
        conta,
        catalogo,
        mission_service,
        gamification_service,
        settlement,
    )


def criar_reward_primeira_aprovada(
    *,
    conta_id: str,
    catalogo,
    mission_service: MissionService,
    discovery_id: str = "cd_settlement_1",
):
    codigo = "community_primeira_aprovada"

    resultado = mission_service.registrar_evento(
        conta_id=conta_id,
        missao_codigo=codigo,
        tipo_evento=("community_discovery_approved"),
        origem=("community_discovery_v1"),
        origem_id=discovery_id,
        chave_idempotencia=(catalogo.chave_idempotencia_aprovacao(discovery_id)),
        instancia_chave=(catalogo.derivar_instancia_chave(codigo)),
        metadados={
            "status": "approved",
        },
    )

    assert resultado.recompensa is not None
    assert resultado.recompensa.status == "pending"

    return resultado.recompensa


def test_ruleset_settlement_preserva_base_e_adiciona_rewards():
    catalogo = criar_catalogo_missoes_producao_v1()

    base = criar_ruleset_producao_v1()

    settlement = criar_ruleset_gamificacao_com_rewards_missoes_v1(catalogo)

    assert settlement.versao == SETTLEMENT_RULESET_VERSION

    assert settlement.niveis_xp == base.niveis_xp

    assert len(settlement.regras) == (len(base.regras) + len(catalogo.recompensas))

    for regra in base.regras:
        equivalente = settlement.obter_regra(regra.tipo_evento)

        assert equivalente == regra

    for politica in catalogo.recompensas:
        regra = settlement.obter_regra(politica.evento_gamificacao)

        assert regra is not None
        assert regra.xp_delta == politica.xp
        assert regra.reputacao_delta == 0
        assert regra.limite_por_janela is None
        assert regra.janela_segundos is None


def test_primeiro_settlement_grava_xp_e_marca_reward(
    tmp_path: Path,
):
    (
        _,
        conta,
        catalogo,
        mission_service,
        gamification_service,
        settlement,
    ) = criar_contexto(tmp_path)

    reward = criar_reward_primeira_aprovada(
        conta_id=conta.id,
        catalogo=catalogo,
        mission_service=(mission_service),
    )

    resultado = settlement.liquidar_recompensa(reward)

    assert resultado.evento_criado is True
    assert resultado.recompensa_marcada is True
    assert resultado.xp == 20

    assert mission_service.listar_recompensas_pendentes() == []

    perfil = gamification_service.obter_perfil(conta.id)

    assert perfil.xp_total == 20
    assert perfil.reputacao_total == 0
    assert perfil.eventos_total == 1

    eventos = gamification_service.listar_eventos(conta.id)

    assert len(eventos) == 1

    evento = eventos[0]

    assert evento.chave_idempotencia == (SETTLEMENT_KEY_PREFIX + reward.id)

    assert evento.tipo_evento == ("mission_reward_" "community_primeira_aprovada")

    assert evento.origem == SETTLEMENT_ORIGIN
    assert evento.origem_id == reward.id
    assert evento.xp_delta == 20
    assert evento.reputacao_delta == 0
    assert evento.regra_versao == SETTLEMENT_RULESET_VERSION

    assert resultado.gamification_event_id == evento.id


def test_replay_nao_duplica_xp_nem_reward(
    tmp_path: Path,
):
    (
        _,
        conta,
        catalogo,
        mission_service,
        gamification_service,
        settlement,
    ) = criar_contexto(tmp_path)

    reward = criar_reward_primeira_aprovada(
        conta_id=conta.id,
        catalogo=catalogo,
        mission_service=(mission_service),
    )

    primeiro = settlement.liquidar_recompensa(reward)

    segundo = settlement.liquidar_recompensa(reward)

    assert primeiro.evento_criado is True
    assert primeiro.recompensa_marcada is True

    assert segundo.evento_criado is False
    assert segundo.recompensa_marcada is False

    assert segundo.gamification_event_id == primeiro.gamification_event_id

    perfil = gamification_service.obter_perfil(conta.id)

    assert perfil.xp_total == 20
    assert perfil.eventos_total == 1
    assert perfil.reputacao_total == 0

    assert mission_service.listar_recompensas_pendentes() == []


def test_crash_entre_ledgers_e_recuperavel(
    tmp_path: Path,
    monkeypatch,
):
    (
        _,
        conta,
        catalogo,
        mission_service,
        gamification_service,
        settlement,
    ) = criar_contexto(tmp_path)

    reward = criar_reward_primeira_aprovada(
        conta_id=conta.id,
        catalogo=catalogo,
        mission_service=(mission_service),
    )

    metodo_real = mission_service.marcar_recompensa_concedida

    def falhar_apos_gamification(
        **_,
    ):
        raise RuntimeError("simulated-crash-after-gamification")

    monkeypatch.setattr(
        mission_service,
        "marcar_recompensa_concedida",
        falhar_apos_gamification,
    )

    with pytest.raises(
        RuntimeError,
        match=("simulated-crash-after-gamification"),
    ):
        settlement.liquidar_recompensa(reward)

    perfil_apos_falha = gamification_service.obter_perfil(conta.id)

    assert perfil_apos_falha.xp_total == 20
    assert perfil_apos_falha.eventos_total == 1

    pendentes = mission_service.listar_recompensas_pendentes()

    assert len(pendentes) == 1
    assert pendentes[0].id == reward.id

    monkeypatch.setattr(
        mission_service,
        "marcar_recompensa_concedida",
        metodo_real,
    )

    retry = settlement.liquidar_recompensa(pendentes[0])

    assert retry.evento_criado is False
    assert retry.recompensa_marcada is True

    perfil_final = gamification_service.obter_perfil(conta.id)

    assert perfil_final.xp_total == 20
    assert perfil_final.eventos_total == 1
    assert perfil_final.reputacao_total == 0

    assert mission_service.listar_recompensas_pendentes() == []


def test_colisao_semantica_falha_fechado_e_preserva_pending(
    tmp_path: Path,
):
    (
        _,
        conta,
        catalogo,
        mission_service,
        gamification_service,
        settlement,
    ) = criar_contexto(tmp_path)

    reward = criar_reward_primeira_aprovada(
        conta_id=conta.id,
        catalogo=catalogo,
        mission_service=(mission_service),
    )

    politica = catalogo.recompensa_para(reward.missao_codigo)

    gamification_service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=(settlement.chave_idempotencia(reward.id)),
        tipo_evento=(politica.evento_gamificacao),
        origem="colisao-intencional",
        origem_id=reward.id,
        metadados={
            "collision": True,
        },
    )

    with pytest.raises(ConflitoEventoGamificacao):
        settlement.liquidar_recompensa(reward)

    pendentes = mission_service.listar_recompensas_pendentes()

    assert len(pendentes) == 1
    assert pendentes[0].id == reward.id

    perfil = gamification_service.obter_perfil(conta.id)

    assert perfil.xp_total == 20
    assert perfil.eventos_total == 1


def test_reward_inconsistente_falha_antes_de_escrever_gamification(
    tmp_path: Path,
):
    (
        _,
        conta,
        catalogo,
        mission_service,
        gamification_service,
        settlement,
    ) = criar_contexto(tmp_path)

    reward = criar_reward_primeira_aprovada(
        conta_id=conta.id,
        catalogo=catalogo,
        mission_service=(mission_service),
    )

    invalidas = (
        replace(
            reward,
            quantidade=21,
        ),
        replace(
            reward,
            tipo_recompensa="reputation",
        ),
        replace(
            reward,
            regra_versao="ruleset-invalido",
        ),
        replace(
            reward,
            instancia_chave="daily:2026-09-20",
        ),
    )

    for invalida in invalidas:
        with pytest.raises(ValueError):
            settlement.liquidar_recompensa(invalida)

    perfil = gamification_service.obter_perfil(conta.id)

    assert perfil.xp_total == 0
    assert perfil.eventos_total == 0
    assert perfil.reputacao_total == 0

    assert len(mission_service.listar_recompensas_pendentes()) == 1


def test_liquidar_pendentes_processa_lote(
    tmp_path: Path,
):
    (
        _,
        conta,
        catalogo,
        mission_service,
        gamification_service,
        settlement,
    ) = criar_contexto(tmp_path)

    criar_reward_primeira_aprovada(
        conta_id=conta.id,
        catalogo=catalogo,
        mission_service=mission_service,
        discovery_id="cd_primeira",
    )

    codigo_cinco = "community_cinco_aprovadas"

    for indice in range(5):
        discovery_id = f"cd_cinco_{indice}"

        mission_service.registrar_evento(
            conta_id=conta.id,
            missao_codigo=codigo_cinco,
            tipo_evento=("community_discovery_approved"),
            origem=("community_discovery_v1"),
            origem_id=discovery_id,
            chave_idempotencia=(catalogo.chave_idempotencia_aprovacao(discovery_id)),
            instancia_chave=(catalogo.derivar_instancia_chave(codigo_cinco)),
            metadados={
                "status": "approved",
            },
        )

    pendentes = mission_service.listar_recompensas_pendentes()

    assert len(pendentes) == 2

    resultado = settlement.liquidar_pendentes()

    assert resultado.recompensas_encontradas == 2
    assert resultado.eventos_criados == 2
    assert resultado.eventos_idempotentes == 0
    assert resultado.recompensas_marcadas == 2
    assert resultado.recompensas_idempotentes == 0
    assert resultado.falhas == ()

    perfil = gamification_service.obter_perfil(conta.id)

    assert perfil.xp_total == 70
    assert perfil.eventos_total == 2
    assert perfil.reputacao_total == 0

    assert mission_service.listar_recompensas_pendentes() == []


def test_contract_7d1_preserva_fronteiras():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "7D1-reward-settlement-core"

    assert data["strategy"]["mode"] == "recoverable-two-step"

    assert data["strategy"]["gamification_event_first"] is True

    assert data["strategy"]["mission_grant_mark_second"] is True

    assert data["strategy"]["crash_window_recoverable"] is True

    assert data["idempotency"]["gamification_key_source"] == "reward_grant_id"

    assert data["rules"]["reputation_delta"] == 0

    boundaries = data["boundaries"]

    assert boundaries["runtime_wiring"] is False
    assert boundaries["production_settlement_run"] is False

    assert boundaries["real_database_mutation"] is False

    assert boundaries["public_api"] is False
    assert boundaries["public_app"] is False

    assert boundaries["community_reputation"] is False

    assert boundaries["offer_scoring_change"] is False

    assert boundaries["price_intelligence_change"] is False

    assert data["next_step"] == ("7D2-runtime-settlement-" "reconciliation")
