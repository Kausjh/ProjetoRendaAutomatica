from __future__ import annotations

import json
from pathlib import Path

from repositories.mission_repository import (
    MissionRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.mission_community_approved_wiring import (
    MissionCommunityApprovedWiring,
)
from services.mission_production_catalog import (
    criar_catalogo_missoes_producao_v1,
)
from services.mission_read_service import (
    MissionReadService,
)
from services.mission_service import (
    MissionService,
)
from services.user_identity_service import (
    UserIdentityService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "user_facing_api_missions_v1.json"


def contexto(tmp_path: Path):
    banco = tmp_path / "identity.sqlite3"

    identity_repository = UserIdentityRepository(banco)

    identity_service = UserIdentityService(identity_repository)

    conta = identity_service.criar_conta(
        email="missions-read@example.com",
        senha="uma-senha-forte-123",
    )

    catalogo = criar_catalogo_missoes_producao_v1()

    mission_service = MissionService(
        repository=MissionRepository(banco),
        identity_repository=identity_repository,
        ruleset=catalogo.ruleset,
    )

    read_service = MissionReadService(
        mission_service=mission_service,
        catalogo=catalogo,
    )

    return (
        conta,
        catalogo,
        mission_service,
        read_service,
    )


def por_codigo(leitura, codigo: str):
    return next(item for item in leitura.missoes if item.codigo == codigo)


def test_contract_define_read_only_route():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["missions_read_http_version"] == 1

    route = data["route"]

    assert route["method"] == "GET"
    assert route["path"] == "/api/v1/me/missions"
    assert route["requires_user_session"] is True
    assert route["identity_source"] == "X-User-Session"
    assert route["client_account_id_accepted"] is False
    assert route["writes_state"] is False


def test_conta_nova_recebe_catalogo_com_zero_progresso(
    tmp_path: Path,
):
    (
        conta,
        catalogo,
        _,
        read_service,
    ) = contexto(tmp_path)

    leitura = read_service.obter(conta.id)

    assert leitura.ruleset_version == catalogo.ruleset.versao

    assert leitura.instancia_chave == "lifetime"

    assert leitura.resumo.total == 3
    assert leitura.resumo.concluidas == 0
    assert leitura.resumo.em_andamento == 0
    assert leitura.resumo.nao_iniciadas == 3
    assert leitura.resumo.rewards_pending == 0
    assert leitura.resumo.rewards_granted == 0

    assert len(leitura.missoes) == 3

    for item in leitura.missoes:
        assert item.progresso_atual == 0
        assert item.percentual == 0.0
        assert item.concluida is False
        assert item.concluida_em is None
        assert item.atualizado_em is None
        assert item.recompensa.tipo == "xp"
        assert item.recompensa.status == "locked"
        assert item.recompensa.concedida_em is None


def test_aprovacao_expoe_progresso_e_pending(
    tmp_path: Path,
):
    (
        conta,
        catalogo,
        mission_service,
        read_service,
    ) = contexto(tmp_path)

    wiring = MissionCommunityApprovedWiring(
        mission_service=mission_service,
        catalogo=catalogo,
    )

    resultado = wiring.processar_aprovacao(
        descoberta_id="discovery-read-1",
        conta_id=conta.id,
        status="approved",
        ocorrido_em=("2026-09-20T16:00:00+00:00"),
    )

    assert resultado.sucesso is True

    leitura = read_service.obter(conta.id)

    primeira = por_codigo(
        leitura,
        "community_primeira_aprovada",
    )

    cinco = por_codigo(
        leitura,
        "community_cinco_aprovadas",
    )

    dez = por_codigo(
        leitura,
        "community_dez_aprovadas",
    )

    assert primeira.progresso_atual == 1
    assert primeira.progresso_alvo == 1
    assert primeira.percentual == 100.0
    assert primeira.concluida is True
    assert primeira.recompensa.quantidade == 20
    assert primeira.recompensa.status == "pending"

    assert cinco.progresso_atual == 1
    assert cinco.progresso_alvo == 5
    assert cinco.percentual == 20.0
    assert cinco.concluida is False
    assert cinco.recompensa.status == "locked"

    assert dez.progresso_atual == 1
    assert dez.progresso_alvo == 10
    assert dez.percentual == 10.0
    assert dez.concluida is False
    assert dez.recompensa.status == "locked"

    assert leitura.resumo.concluidas == 1
    assert leitura.resumo.em_andamento == 2
    assert leitura.resumo.nao_iniciadas == 0
    assert leitura.resumo.rewards_pending == 1
    assert leitura.resumo.rewards_granted == 0


def test_reward_granted_aparece_sem_expor_referencia(
    tmp_path: Path,
):
    (
        conta,
        catalogo,
        mission_service,
        read_service,
    ) = contexto(tmp_path)

    wiring = MissionCommunityApprovedWiring(
        mission_service=mission_service,
        catalogo=catalogo,
    )

    wiring.processar_aprovacao(
        descoberta_id="discovery-read-2",
        conta_id=conta.id,
        status="approved",
        ocorrido_em=("2026-09-20T16:10:00+00:00"),
    )

    recompensa = mission_service.obter_recompensa(
        conta_id=conta.id,
        missao_codigo=("community_primeira_aprovada"),
    )

    assert recompensa is not None

    mission_service.marcar_recompensa_concedida(
        recompensa_id=recompensa.id,
        referencia_concessao="gme_read_test",
    )

    leitura = read_service.obter(conta.id)

    primeira = por_codigo(
        leitura,
        "community_primeira_aprovada",
    )

    assert primeira.recompensa.status == "granted"

    assert primeira.recompensa.concedida_em is not None

    assert leitura.resumo.rewards_pending == 0

    assert leitura.resumo.rewards_granted == 1

    assert not hasattr(
        primeira.recompensa,
        "referencia_concessao",
    )

    assert not hasattr(
        primeira.recompensa,
        "id",
    )


def test_contract_preserva_fronteiras_7e():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    boundaries = data["boundaries"]

    assert boundaries["event_history_exposed"] is False

    assert boundaries["reward_grant_id_exposed"] is False

    assert boundaries["gamification_reference_exposed"] is False

    assert boundaries["write_api"] is False

    assert boundaries["public_app_integration"] is False

    assert boundaries["community_reputation"] is False

    assert boundaries["social_rankings"] is False
