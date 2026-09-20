from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from repositories.mission_repository import (
    MissionRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.gamification_service import (
    GamificationService,
)
from services.mission_production_catalog import (
    criar_catalogo_missoes_producao_v1,
)
from services.mission_reward_settlement_runtime import (
    ResultadoAtivacaoRewardSettlement,
    ativar_reward_settlement_runtime,
)
from services.mission_service import (
    MissionService,
)
from services.user_identity_service import (
    UserIdentityService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "missions_community_rewards_settlement_runtime_v1.json"


def criar_contexto(
    tmp_path: Path,
):
    banco = tmp_path / "user_identity.sqlite3"

    identity_repository = UserIdentityRepository(banco)

    conta = UserIdentityService(identity_repository).criar_conta(
        email=("settlement-runtime@example.com"),
        senha=("senha-segura-123"),
    )

    catalogo = criar_catalogo_missoes_producao_v1()

    mission_service = MissionService(
        MissionRepository(banco),
        identity_repository,
        catalogo.ruleset,
    )

    return (
        banco,
        identity_repository,
        conta,
        catalogo,
        mission_service,
    )


def criar_reward(
    *,
    conta_id: str,
    catalogo,
    mission_service: MissionService,
):
    codigo = "community_primeira_aprovada"

    discovery_id = "cd_runtime_settlement_1"

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


def test_runtime_settlement_liquida_pending(
    tmp_path: Path,
):
    (
        banco,
        identity_repository,
        conta,
        catalogo,
        mission_service,
    ) = criar_contexto(tmp_path)

    reward = criar_reward(
        conta_id=conta.id,
        catalogo=catalogo,
        mission_service=mission_service,
    )

    resultado = ativar_reward_settlement_runtime(
        caminho_banco=banco,
        user_identity_repository=(identity_repository),
        mission_service=(mission_service),
    )

    assert isinstance(
        resultado,
        ResultadoAtivacaoRewardSettlement,
    )

    assert resultado.ativo is True
    assert resultado.erro is None
    assert resultado.reconciliacao is not None
    assert resultado.settlement_service is not None
    assert resultado.gamification_service is not None

    reconciliacao = resultado.reconciliacao

    assert reconciliacao.recompensas_encontradas == 1
    assert reconciliacao.eventos_criados == 1
    assert reconciliacao.eventos_idempotentes == 0
    assert reconciliacao.recompensas_marcadas == 1
    assert reconciliacao.recompensas_idempotentes == 0
    assert reconciliacao.falhas == ()

    assert mission_service.listar_recompensas_pendentes() == []

    gamification_service = resultado.gamification_service

    assert isinstance(
        gamification_service,
        GamificationService,
    )

    perfil = gamification_service.obter_perfil(conta.id)

    assert perfil.xp_total == 20
    assert perfil.reputacao_total == 0
    assert perfil.eventos_total == 1

    eventos = gamification_service.listar_eventos(conta.id)

    assert len(eventos) == 1
    assert eventos[0].origem_id == reward.id


def test_segunda_ativacao_sem_pending_e_neutra(
    tmp_path: Path,
):
    (
        banco,
        identity_repository,
        conta,
        catalogo,
        mission_service,
    ) = criar_contexto(tmp_path)

    criar_reward(
        conta_id=conta.id,
        catalogo=catalogo,
        mission_service=mission_service,
    )

    primeira = ativar_reward_settlement_runtime(
        caminho_banco=banco,
        user_identity_repository=(identity_repository),
        mission_service=(mission_service),
    )

    segunda = ativar_reward_settlement_runtime(
        caminho_banco=banco,
        user_identity_repository=(identity_repository),
        mission_service=(mission_service),
    )

    assert primeira.ativo is True
    assert segunda.ativo is True
    assert segunda.erro is None
    assert segunda.reconciliacao is not None

    r = segunda.reconciliacao

    assert r.recompensas_encontradas == 0
    assert r.eventos_criados == 0
    assert r.eventos_idempotentes == 0
    assert r.recompensas_marcadas == 0
    assert r.recompensas_idempotentes == 0
    assert r.falhas == ()

    assert segunda.gamification_service is not None

    perfil = segunda.gamification_service.obter_perfil(conta.id)

    assert perfil.xp_total == 20
    assert perfil.eventos_total == 1
    assert perfil.reputacao_total == 0


def test_runtime_reporta_falha_sem_esconder_lote(
    tmp_path: Path,
):
    (
        banco,
        identity_repository,
        conta,
        catalogo,
        mission_service,
    ) = criar_contexto(tmp_path)

    reward = criar_reward(
        conta_id=conta.id,
        catalogo=catalogo,
        mission_service=mission_service,
    )

    conn = sqlite3.connect(banco)

    try:
        conn.execute(
            """
            UPDATE mission_reward_grants
            SET quantidade = 21
            WHERE id = ?
            """,
            (reward.id,),
        )

        conn.commit()

    finally:
        conn.close()

    resultado = ativar_reward_settlement_runtime(
        caminho_banco=banco,
        user_identity_repository=(identity_repository),
        mission_service=(mission_service),
    )

    assert resultado.ativo is False
    assert resultado.reconciliacao is not None
    assert resultado.erro is not None

    r = resultado.reconciliacao

    assert r.recompensas_encontradas == 1
    assert r.eventos_criados == 0
    assert r.eventos_idempotentes == 0
    assert r.recompensas_marcadas == 0
    assert r.recompensas_idempotentes == 0
    assert len(r.falhas) == 1

    assert "ValueError" in r.falhas[0]

    assert len(mission_service.listar_recompensas_pendentes()) == 1

    assert resultado.gamification_service is not None

    perfil = resultado.gamification_service.obter_perfil(conta.id)

    assert perfil.xp_total == 0
    assert perfil.eventos_total == 0
    assert perfil.reputacao_total == 0


def test_excecao_de_bootstrap_retorna_inativo(
    tmp_path: Path,
    monkeypatch,
):
    import services.mission_reward_settlement_runtime as settlement_runtime_module

    banco = tmp_path / "user_identity.sqlite3"

    identity_repository = UserIdentityRepository(banco)

    catalogo = criar_catalogo_missoes_producao_v1()

    mission_service = MissionService(
        MissionRepository(banco),
        identity_repository,
        catalogo.ruleset,
    )

    def falhar_repository(
        *_,
        **__,
    ):
        raise RuntimeError("simulated-bootstrap-failure")

    monkeypatch.setattr(
        settlement_runtime_module,
        "GamificationRepository",
        falhar_repository,
    )

    resultado = ativar_reward_settlement_runtime(
        caminho_banco=banco,
        user_identity_repository=(identity_repository),
        mission_service=(mission_service),
    )

    assert resultado.ativo is False

    assert resultado.settlement_service is None

    assert resultado.gamification_service is None

    assert resultado.reconciliacao is None

    assert resultado.erro == ("RuntimeError: " "simulated-bootstrap-failure")


def test_7d2_registra_boundary_historico_sem_wiring():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == ("7D2-runtime-settlement-" "reconciliation")

    ordering = data["ordering_contract"]

    assert ordering["runtime_py_wiring_currently_present"] is False

    boundaries = data["boundaries"]

    assert boundaries["runtime_py_modified"] is False

    assert boundaries["production_activation_run"] is False

    assert boundaries["production_database_mutation"] is False

    assert boundaries["real_reward_settled"] is False

    assert data["next_step"] == "7D3-controlled-runtime-wiring"


def test_contract_7d2_preserva_activation_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == ("7D2-runtime-settlement-" "reconciliation")

    component = data["runtime_component"]

    assert component["mission_service_injected"] is True

    assert component["dedicated_gamification_service"] is True

    assert component["compound_ruleset"] is True

    ordering = data["ordering_contract"]

    assert ordering["gamification_reconciliation_first"] is True

    assert ordering["mission_reconciliation_second"] is True

    assert ordering["reward_settlement_third"] is True

    assert ordering["personalized_feed_after_settlement"] is True

    assert ordering["runtime_py_wiring_currently_present"] is False

    boundaries = data["boundaries"]

    assert boundaries["runtime_py_modified"] is False

    assert boundaries["production_activation_run"] is False

    assert boundaries["production_database_mutation"] is False

    assert boundaries["real_reward_settled"] is False

    assert data["next_step"] == "7D3-controlled-runtime-wiring"
