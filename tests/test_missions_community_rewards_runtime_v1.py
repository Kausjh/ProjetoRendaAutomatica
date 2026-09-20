from __future__ import annotations

import json
import sqlite3
import unicodedata
from pathlib import Path

import scrapers.community_discovery_scraper as community_scraper_module
from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from scrapers.community_discovery_scraper import (
    CommunityDiscoveryScraper,
)
from services.community_discovery_queue_service import (
    CommunityDiscoveryQueueService,
)
from services.community_discovery_service import (
    CommunityDiscoveryService,
)
from services.mission_runtime import (
    ativar_missoes_runtime,
)
from services.user_identity_service import (
    UserIdentityService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "missions_community_rewards_runtime_v1.json"


def ascii_fold(
    value: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        value,
    )

    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def contexto(
    tmp_path: Path,
):
    db = tmp_path / "user_identity.sqlite3"

    identity_repository = UserIdentityRepository(db)

    conta = UserIdentityService(identity_repository).criar_conta(
        email="runtime@example.com",
        senha="uma-senha-forte-123",
    )

    community_repository = CommunityDiscoveryRepository(db)

    community_service = CommunityDiscoveryService(community_repository)

    return {
        "db": db,
        "identity_repository": (identity_repository),
        "conta": conta,
        "community_repository": (community_repository),
        "community_service": (community_service),
    }


def registrar(
    c,
    *,
    numero: int,
):
    item, criado = c["community_service"].registrar(
        conta_id=c["conta"].id,
        url=(
            "https://www.mercadolivre.com.br/"
            f"produto-runtime-{numero}/p/"
            f"MLB{70000000 + numero}"
        ),
    )

    assert criado is True

    return item


def aprovar_sem_hook(
    c,
    *,
    numero: int,
):
    item = registrar(
        c,
        numero=numero,
    )

    queue = CommunityDiscoveryQueueService(c["community_repository"])

    reservados = queue.reservar(limite=20)

    reservado = next(atual for atual in reservados if atual.id == item.id)

    assert reservado.status == "processing"

    aprovada = queue.aprovar(
        reservado.id,
        canonical_key=(f"runtime_produto_{numero}"),
        motivo="oferta_validada",
    )

    assert aprovada.status == "approved"

    return aprovada


def test_runtime_reconcilia_historico_antes_do_live(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    aprovar_sem_hook(
        c,
        numero=1,
    )

    resultado = ativar_missoes_runtime(
        caminho_banco=c["db"],
        user_identity_repository=(c["identity_repository"]),
    )

    assert resultado.ativo is True
    assert resultado.erro is None
    assert resultado.service is not None
    assert resultado.wiring is not None
    assert resultado.reconciliacao is not None

    reconciliacao = resultado.reconciliacao

    assert reconciliacao.descobertas_processadas == 1

    assert reconciliacao.eventos_criados == 3

    assert reconciliacao.eventos_idempotentes == 0

    assert reconciliacao.missoes_concluidas_agora == 1

    assert reconciliacao.recompensas_criadas == 1

    pendentes = resultado.service.listar_recompensas_pendentes()

    assert len(pendentes) == 1
    assert pendentes[0].status == "pending"
    assert pendentes[0].quantidade == 20

    with sqlite3.connect(c["db"]) as conn:
        tabelas = {
            str(row[0])
            for row in conn.execute(
                "SELECT name " "FROM sqlite_master " "WHERE type = 'table'"
            ).fetchall()
        }

    assert {
        "mission_progress_events",
        "mission_progress",
        "mission_reward_grants",
    }.issubset(tabelas)


def test_segunda_ativacao_e_idempotente(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    aprovar_sem_hook(
        c,
        numero=1,
    )

    primeira = ativar_missoes_runtime(
        caminho_banco=c["db"],
        user_identity_repository=(c["identity_repository"]),
    )

    segunda = ativar_missoes_runtime(
        caminho_banco=c["db"],
        user_identity_repository=(c["identity_repository"]),
    )

    assert primeira.ativo is True
    assert segunda.ativo is True
    assert segunda.reconciliacao is not None
    assert segunda.service is not None

    assert segunda.reconciliacao.eventos_criados == 0

    assert segunda.reconciliacao.eventos_idempotentes == 3

    assert segunda.reconciliacao.recompensas_criadas == 0

    assert len(segunda.service.listar_recompensas_pendentes()) == 1


def test_live_hook_processa_novo_approved(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    ativacao = ativar_missoes_runtime(
        caminho_banco=c["db"],
        user_identity_repository=(c["identity_repository"]),
    )

    assert ativacao.ativo is True
    assert ativacao.wiring is not None
    assert ativacao.service is not None

    item = registrar(
        c,
        numero=1,
    )

    queue = CommunityDiscoveryQueueService(
        c["community_repository"],
        approval_hook=ativacao.wiring,
    )

    reservados = queue.reservar(limite=20)

    reservado = next(atual for atual in reservados if atual.id == item.id)

    aprovada = queue.aprovar(
        reservado.id,
        canonical_key="runtime_live_1",
        motivo="oferta_validada",
    )

    assert aprovada.status == "approved"

    pendentes = ativacao.service.listar_recompensas_pendentes()

    assert len(pendentes) == 1
    assert pendentes[0].quantidade == 20


def test_hook_failure_nao_reverte_approved(
    tmp_path: Path,
):
    c = contexto(tmp_path)

    class HookQueFalha:
        def processar_aprovacao(
            self,
            **kwargs,
        ):
            raise RuntimeError("falha proposital")

    item = registrar(
        c,
        numero=1,
    )

    queue = CommunityDiscoveryQueueService(
        c["community_repository"],
        approval_hook=HookQueFalha(),
    )

    reservados = queue.reservar(limite=20)

    reservado = next(atual for atual in reservados if atual.id == item.id)

    aprovada = queue.aprovar(
        reservado.id,
        canonical_key="runtime_fail_open",
        motivo="oferta_validada",
    )

    assert aprovada.status == "approved"

    persistida = c["community_repository"].obter_por_id(aprovada.id)

    assert persistida is not None
    assert persistida.status == "approved"


def test_scraper_compoe_live_hook_quando_env_ativo(
    tmp_path: Path,
    monkeypatch,
):
    marker = object()

    monkeypatch.setenv(
        "MISSIONS_COMMUNITY_RUNTIME_ATIVO",
        "1",
    )

    monkeypatch.setattr(
        community_scraper_module,
        "criar_wiring_missoes_live",
        lambda **kwargs: marker,
    )

    scraper = CommunityDiscoveryScraper(
        caminho_banco=str(tmp_path / "identity.sqlite3"),
    )

    assert scraper.queue_service.approval_hook is marker


def test_scraper_nao_compoe_hook_quando_env_inativo(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setenv(
        "MISSIONS_COMMUNITY_RUNTIME_ATIVO",
        "0",
    )

    def nao_deveria_chamar(
        **kwargs,
    ):
        raise AssertionError("factory nao deveria ser chamada")

    monkeypatch.setattr(
        community_scraper_module,
        "criar_wiring_missoes_live",
        nao_deveria_chamar,
    )

    scraper = CommunityDiscoveryScraper(
        caminho_banco=str(tmp_path / "identity.sqlite3"),
    )

    assert scraper.queue_service.approval_hook is None


def test_runtime_habilita_flag_antes_do_orquestrador():
    source = (ROOT / "runtime.py").read_text(encoding="utf-8")

    activation = source.index("mission_runtime = " "ativar_missoes_runtime(")

    flag = source.index('"MISSIONS_COMMUNITY_RUNTIME_ATIVO"')

    personalized = source.index("personalized_feed_service = " "PersonalizedFeedService(")

    orchestrator = source.index("orquestrador.executar()")

    assert activation < flag
    assert flag < personalized
    assert personalized < orchestrator


def test_queue_persiste_approved_antes_do_hook():
    source = (ROOT / "services" / "community_discovery_queue_service.py").read_text(
        encoding="utf-8"
    )

    method_start = source.index("    def aprovar(")

    method_end = source.index(
        "\n    def ",
        method_start + 1,
    )

    method = source[method_start:method_end]

    persist = method.index("marcar_aprovada(")

    reread = method.index("_obter_obrigatoria(")

    hook = method.index(".processar_aprovacao(")

    assert persist < reread < hook
    assert "except Exception:" in method


def test_contract_e_roadmap_7c2():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == ("7C2-controlled-runtime-activation")

    assert data["runtime"]["reconciliation_before_live_wiring"] is True

    assert data["runtime"]["live_wiring_enabled_only_after_success"] is True

    assert data["runtime"]["production_activation_run"] is True

    assert data["live_wiring"]["approval_persisted_before_hook"] is True

    assert data["live_wiring"]["hook_failure_reverts_approval"] is False

    assert data["gamification_boundary"]["reward_settlement"] is False

    roadmap = (ROOT / "docs" / "17-roadmap-fase-2.md").read_text(encoding="utf-8")

    roadmap_fold = ascii_fold(roadmap)

    assert "status: em execucao" in roadmap_fold

    assert "7a, 7b, 7c1 e 7c2" in roadmap_fold

    assert "comentarios vinculados" in roadmap_fold

    assert "perfil publico opcional" in roadmap_fold

    assert "public app experience / visual polish" in roadmap_fold

    assert "rankings" in roadmap_fold

    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    readme_fold = ascii_fold(readme)

    assert "etapa 7" in readme_fold
    assert "em execucao" in readme_fold
    assert "visual polish" in readme_fold


def test_operational_validation_7c2():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    validation = data["operational_validation"]

    assert data["runtime"]["production_activation_run"] is True

    assert validation["backup_pre_activation_validated"] is True

    assert validation["supervisor_preserved"] is True

    assert validation["runtime_recreated"] is True

    assert validation["health_after_restart"] == "HEALTHY"

    assert validation["cdp_preserved_online"] is True

    assert validation["sqlite_integrity"] == "ok"

    assert validation["foreign_key_errors"] == 0

    assert validation["approved_rows"] == 1

    assert validation["mission_tables"] == 3

    assert validation["mission_progress_events"] == 3

    assert validation["mission_progress_rows"] == 3

    assert validation["mission_reward_grants"] == 1

    assert validation["pending_rewards"] == 1

    assert validation["pending_reward_xp"] == 20

    assert validation["second_reconciliation_created"] == 0

    assert validation["second_reconciliation_idempotent"] == 3

    assert validation["second_reconciliation_rewards_created"] == 0

    assert validation["second_reconciliation_failures"] == 0

    assert validation["gamification_xp"] == 140

    assert validation["gamification_events"] == 7

    assert validation["community_reputation"] == 0

    assert data["next_step"] == ("7D-reward-settlement-to-gamification")
