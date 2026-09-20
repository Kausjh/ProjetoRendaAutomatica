from __future__ import annotations

from pathlib import Path

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.mission_community_reconciliation_repository import (
    MissionCommunityReconciliationRepository,
)
from repositories.mission_repository import (
    MissionRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.community_discovery_queue_service import (
    CommunityDiscoveryQueueService,
)
from services.community_discovery_service import (
    CommunityDiscoveryService,
)
from services.mission_community_approved_wiring import (
    MissionCommunityApprovedWiring,
)
from services.mission_community_reconciliation_service import (
    MissionCommunityReconciliationService,
)
from services.mission_production_catalog import (
    criar_catalogo_missoes_producao_v1,
)
from services.mission_service import (
    MissionService,
)
from services.user_identity_service import (
    UserIdentityService,
)


def contexto(
    tmp_path: Path,
):
    banco = tmp_path / "user_identity.sqlite3"

    identity_repository = UserIdentityRepository(banco)

    identity_service = UserIdentityService(identity_repository)

    conta = identity_service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )

    community_repository = CommunityDiscoveryRepository(banco)

    community_service = CommunityDiscoveryService(community_repository)

    queue_service = CommunityDiscoveryQueueService(community_repository)

    catalogo = criar_catalogo_missoes_producao_v1()

    mission_repository = MissionRepository(banco)

    mission_service = MissionService(
        repository=mission_repository,
        identity_repository=(identity_repository),
        ruleset=catalogo.ruleset,
    )

    wiring = MissionCommunityApprovedWiring(
        mission_service=mission_service,
        catalogo=catalogo,
    )

    reconciliation_repository = MissionCommunityReconciliationRepository(banco)

    reconciliation_service = MissionCommunityReconciliationService(
        repository=(reconciliation_repository),
        wiring=wiring,
        tamanho_lote=2,
    )

    return {
        "banco": banco,
        "identity_service": (identity_service),
        "conta": conta,
        "community_repository": (community_repository),
        "community_service": (community_service),
        "queue_service": queue_service,
        "catalogo": catalogo,
        "mission_repository": (mission_repository),
        "mission_service": mission_service,
        "wiring": wiring,
        "reconciliation_repository": (reconciliation_repository),
        "reconciliation_service": (reconciliation_service),
    }


def registrar(
    contexto,
    *,
    numero: int,
):
    item, criado = contexto["community_service"].registrar(
        conta_id=(contexto["conta"].id),
        url=(
            "https://www.mercadolivre.com.br/"
            f"produto-teste-{numero}/p/"
            f"MLB{10000000 + numero}"
        ),
    )

    assert criado is True

    return item


def aprovar(
    contexto,
    *,
    numero: int,
):
    item = registrar(
        contexto,
        numero=numero,
    )

    reservados = contexto["queue_service"].reservar(limite=20)

    reservado = next(atual for atual in reservados if atual.id == item.id)

    assert reservado.status == "processing"

    aprovada = contexto["queue_service"].aprovar(
        reservado.id,
        canonical_key=(f"produto_{numero}"),
        motivo="oferta_validada",
    )

    assert aprovada.status == "approved"

    return aprovada


def test_reconciliation_repository_lista_so_approved(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    aprovada = aprovar(
        c,
        numero=1,
    )

    recebida = registrar(
        c,
        numero=2,
    )

    assert recebida.status == "received"

    itens = c["reconciliation_repository"].listar_aprovadas()

    assert [item.id for item in itens] == [aprovada.id]

    assert itens[0].conta_id == (c["conta"].id)

    assert itens[0].status == "approved"


def test_wiring_de_um_approved_alimenta_tres_missoes(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    aprovada = aprovar(
        c,
        numero=1,
    )

    resultado = c["wiring"].processar_aprovacao(
        descoberta_id=aprovada.id,
        conta_id=aprovada.conta_id,
        status=aprovada.status,
        ocorrido_em=(aprovada.atualizado_em),
    )

    assert resultado.sucesso is True
    assert resultado.eventos_criados == 3
    assert resultado.eventos_idempotentes == 0
    assert resultado.eventos_completados == 0
    assert resultado.missoes_concluidas_agora == 1
    assert resultado.recompensas_criadas == 1
    assert resultado.falhas == ()

    pendentes = c["mission_service"].listar_recompensas_pendentes()

    assert len(pendentes) == 1
    assert pendentes[0].quantidade == 20

    catalogo = c["catalogo"]

    primeira = c["mission_service"].obter_progresso(
        conta_id=c["conta"].id,
        missao_codigo=("community_primeira_aprovada"),
        instancia_chave=(catalogo.instancia_chave),
    )

    cinco = c["mission_service"].obter_progresso(
        conta_id=c["conta"].id,
        missao_codigo=("community_cinco_aprovadas"),
        instancia_chave=(catalogo.instancia_chave),
    )

    dez = c["mission_service"].obter_progresso(
        conta_id=c["conta"].id,
        missao_codigo=("community_dez_aprovadas"),
        instancia_chave=(catalogo.instancia_chave),
    )

    assert primeira is not None
    assert cinco is not None
    assert dez is not None

    assert primeira.progresso_total == 1
    assert primeira.concluida is True

    assert cinco.progresso_total == 1
    assert cinco.concluida is False

    assert dez.progresso_total == 1
    assert dez.concluida is False


def test_wiring_replay_e_idempotente(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    aprovada = aprovar(
        c,
        numero=1,
    )

    kwargs = {
        "descoberta_id": aprovada.id,
        "conta_id": aprovada.conta_id,
        "status": aprovada.status,
        "ocorrido_em": (aprovada.atualizado_em),
    }

    primeiro = c["wiring"].processar_aprovacao(**kwargs)

    segundo = c["wiring"].processar_aprovacao(**kwargs)

    assert primeiro.eventos_criados == 3
    assert segundo.sucesso is True
    assert segundo.eventos_criados == 0
    assert segundo.eventos_idempotentes == 3
    assert segundo.recompensas_criadas == 0

    assert len(c["mission_service"].listar_recompensas_pendentes()) == 1


def test_wiring_nao_aceita_received(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    recebida = registrar(
        c,
        numero=1,
    )

    resultado = c["wiring"].processar_aprovacao(
        descoberta_id=recebida.id,
        conta_id=recebida.conta_id,
        status=recebida.status,
        ocorrido_em=(recebida.atualizado_em),
    )

    assert resultado.sucesso is False
    assert resultado.eventos_criados == 0
    assert "status_nao_aprovado" in resultado.falhas

    assert (
        c["mission_repository"].listar_eventos(
            conta_id=c["conta"].id,
        )
        == []
    )


def test_reconciliacao_historica_primeira_execucao(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    aprovar(
        c,
        numero=1,
    )

    resultado = c["reconciliation_service"].reconciliar()

    assert resultado.sucesso is True
    assert resultado.descobertas_processadas == 1
    assert resultado.eventos_criados == 3
    assert resultado.eventos_idempotentes == 0
    assert resultado.missoes_concluidas_agora == 1
    assert resultado.recompensas_criadas == 1
    assert resultado.falhas == ()

    pendentes = c["mission_service"].listar_recompensas_pendentes()

    assert len(pendentes) == 1
    assert pendentes[0].quantidade == 20


def test_segunda_reconciliacao_e_idempotente(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    aprovar(
        c,
        numero=1,
    )

    primeiro = c["reconciliation_service"].reconciliar()

    segundo = c["reconciliation_service"].reconciliar()

    assert primeiro.sucesso is True
    assert segundo.sucesso is True

    assert segundo.eventos_criados == 0

    assert segundo.eventos_idempotentes == 3

    assert segundo.recompensas_criadas == 0

    assert len(c["mission_service"].listar_recompensas_pendentes()) == 1


def test_cinco_approved_concluem_primeira_e_cinco(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    for numero in range(1, 6):
        aprovar(
            c,
            numero=numero,
        )

    resultado = c["reconciliation_service"].reconciliar()

    assert resultado.sucesso is True
    assert resultado.descobertas_processadas == 5

    pendentes = c["mission_service"].listar_recompensas_pendentes()

    assert sorted(item.quantidade for item in pendentes) == [
        20,
        50,
    ]

    cinco = c["mission_service"].obter_progresso(
        conta_id=c["conta"].id,
        missao_codigo=("community_cinco_aprovadas"),
    )

    dez = c["mission_service"].obter_progresso(
        conta_id=c["conta"].id,
        missao_codigo=("community_dez_aprovadas"),
    )

    assert cinco is not None
    assert dez is not None

    assert cinco.progresso_total == 5
    assert cinco.concluida is True

    assert dez.progresso_total == 5
    assert dez.concluida is False


def test_reconciliacao_sem_approved_e_noop(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    registrar(
        c,
        numero=1,
    )

    resultado = c["reconciliation_service"].reconciliar()

    assert resultado.sucesso is True
    assert resultado.descobertas_processadas == 0
    assert resultado.eventos_criados == 0
    assert resultado.eventos_idempotentes == 0
    assert resultado.recompensas_criadas == 0


def test_live_queue_ainda_nao_foi_modificada():
    root = Path(__file__).resolve().parents[1]

    source = (root / "services" / "community_discovery_queue_service.py").read_text(
        encoding="utf-8"
    )

    assert "MissionCommunityApprovedWiring" not in source

    assert "mission_wiring" not in source


def test_runtime_ainda_nao_ativa_missoes():
    root = Path(__file__).resolve().parents[1]

    source = (root / "runtime.py").read_text(encoding="utf-8")

    assert "MissionRepository" not in source
    assert "MissionService" not in source

    assert "MissionCommunityReconciliationService" not in source


def test_contract_preserva_fronteiras_7c1():
    import json

    root = Path(__file__).resolve().parents[1]

    data = json.loads(
        (root / "contracts" / "missions_community_rewards_wiring_v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert data["stage"] == ("7C1-community-approved-wiring-" "reconciliation-service")

    assert data["source_event"]["required_status"] == "approved"

    assert data["wiring"]["missions_per_approved"] == 3

    assert data["wiring"]["live_queue_injection"] is False

    assert data["reconciliation"]["idempotent_replay"] is True

    assert data["reconciliation"]["must_succeed_before_live_wiring"] is True

    assert data["expected_single_approved"]["mission_events_created_first_run"] == 3

    assert data["expected_single_approved"]["mission_events_idempotent_second_run"] == 3

    boundaries = data["boundaries"]

    assert boundaries["production_database_mutation"] is False

    assert boundaries["community_queue_modified"] is False

    assert boundaries["live_wiring"] is False

    assert boundaries["runtime_wiring"] is False

    assert boundaries["reward_settlement"] is False

    assert boundaries["community_reputation"] is False

    assert data["next_step"] == ("7C2-controlled-runtime-activation")
