from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.community_trust_reconciliation_repository import (
    CommunityTrustReconciliationRepository,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)
from services.community_discovery_queue_service import (
    CommunityDiscoveryQueueService,
)
from services.community_trust_discovery_wiring import (
    CommunityTrustDiscoveryWiring,
)
from services.community_trust_reconciliation_service import (
    CommunityTrustReconciliationService,
)
from services.community_trust_terminal_hook import (
    CommunityTrustTerminalHook,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_trust_reconciliation_v1.json"


def preparar_contexto(
    tmp_path: Path,
):
    banco = tmp_path / "identity.sqlite3"

    with sqlite3.connect(banco) as conexao:
        conexao.execute("""
            CREATE TABLE contas_usuario (
                id TEXT PRIMARY KEY
            )
            """)

        conexao.execute(
            """
            INSERT INTO contas_usuario (id)
            VALUES (?)
            """,
            ("conta-a",),
        )

    discovery_repository = CommunityDiscoveryRepository(banco)

    trust_repository = CommunityTrustRepository(banco)

    trust_wiring = CommunityTrustDiscoveryWiring(trust_repository)

    terminal_hook = CommunityTrustTerminalHook(
        discovery_repository,
        trust_wiring,
    )

    reconciliation_repository = CommunityTrustReconciliationRepository(banco)

    reconciliation_service = CommunityTrustReconciliationService(
        repository=(reconciliation_repository),
        terminal_hook=terminal_hook,
    )

    relogio = [
        datetime(
            2026,
            9,
            17,
            0,
            0,
            tzinfo=UTC,
        )
    ]

    queue = CommunityDiscoveryQueueService(
        discovery_repository,
        agora_provider=lambda: relogio[0],
    )

    return (
        banco,
        discovery_repository,
        trust_repository,
        terminal_hook,
        reconciliation_repository,
        reconciliation_service,
        queue,
        relogio,
    )


def criar_terminal_historico(
    repository: CommunityDiscoveryRepository,
    queue: CommunityDiscoveryQueueService,
    relogio: list[datetime],
    *,
    discovery_id: str,
    status: str,
):
    url = "https://example.com/" + discovery_id

    repository.registrar(
        descoberta_id=discovery_id,
        conta_id="conta-a",
        url=url,
        url_normalizada=url,
        url_hash=("hash-" + discovery_id),
        marketplace="mercado_livre",
        agora=relogio[0].isoformat(),
    )

    reservadas = queue.reservar(limite=1)

    assert len(reservadas) == 1
    assert reservadas[0].id == discovery_id

    relogio[0] += timedelta(minutes=1)

    if status == "approved":
        return queue.aprovar(
            discovery_id,
            canonical_key=("canonical-" + discovery_id),
            motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
        )

    if status == "rejected":
        return queue.rejeitar(
            discovery_id,
            motivo=("coletor_fora_nicho:" "produto fora do nicho"),
        )

    raise ValueError("status terminal invalido no teste.")


def criar_nao_terminal(
    repository: CommunityDiscoveryRepository,
    *,
    discovery_id: str,
    agora: datetime,
):
    url = "https://example.com/" + discovery_id

    item, criada = repository.registrar(
        descoberta_id=discovery_id,
        conta_id="conta-a",
        url=url,
        url_normalizada=url,
        url_hash=("hash-" + discovery_id),
        marketplace="mercado_livre",
        agora=agora.isoformat(),
    )

    assert criada is True

    return item


def test_repository_lista_apenas_terminais_sem_evidencia_em_ordem(
    tmp_path: Path,
):
    (
        _banco,
        discovery_repository,
        _trust_repository,
        _terminal_hook,
        reconciliation_repository,
        _reconciliation_service,
        queue,
        relogio,
    ) = preparar_contexto(tmp_path)

    primeiro = criar_terminal_historico(
        discovery_repository,
        queue,
        relogio,
        discovery_id="dsc-002",
        status="rejected",
    )

    relogio[0] += timedelta(minutes=1)

    segundo = criar_terminal_historico(
        discovery_repository,
        queue,
        relogio,
        discovery_id="dsc-001",
        status="approved",
    )

    criar_nao_terminal(
        discovery_repository,
        discovery_id="dsc-received",
        agora=relogio[0],
    )

    candidatos = reconciliation_repository.listar_terminais_sem_evidencia(limite=10)

    assert [item.id for item in candidatos] == [
        primeiro.id,
        segundo.id,
    ]

    assert reconciliation_repository.contar_terminais_sem_evidencia() == 2


def test_reconciliation_backfill_aprovado_e_rejeitado(
    tmp_path: Path,
):
    (
        _banco,
        discovery_repository,
        trust_repository,
        _terminal_hook,
        reconciliation_repository,
        reconciliation_service,
        queue,
        relogio,
    ) = preparar_contexto(tmp_path)

    criar_terminal_historico(
        discovery_repository,
        queue,
        relogio,
        discovery_id="dsc-rejected",
        status="rejected",
    )

    relogio[0] += timedelta(minutes=1)

    criar_terminal_historico(
        discovery_repository,
        queue,
        relogio,
        discovery_id="dsc-approved",
        status="approved",
    )

    assert reconciliation_repository.contar_terminais_sem_evidencia() == 2

    resultado = reconciliation_service.reconciliar_lote(limite=10)

    assert resultado.candidatos == 2
    assert resultado.processados == 2
    assert resultado.criados == 2
    assert resultado.idempotentes == 0
    assert resultado.falhas == 0
    assert resultado.falhas_detalhes == ()

    assert reconciliation_repository.contar_terminais_sem_evidencia() == 0

    evidencias = trust_repository.listar_evidencias(
        conta_id="conta-a",
        limite=20,
    )

    assert len(evidencias) == 2

    classificacoes = sorted(item.classificacao for item in evidencias)

    assert classificacoes == [
        "neutral",
        "positive",
    ]

    perfil = trust_repository.obter_perfil("conta-a")

    assert perfil.evidencias_total == 2
    assert perfil.positivas_total == 1
    assert perfil.negativas_total == 0
    assert perfil.neutras_total == 1


def test_reconciliation_segunda_execucao_nao_tem_candidatos(
    tmp_path: Path,
):
    (
        _banco,
        discovery_repository,
        _trust_repository,
        _terminal_hook,
        reconciliation_repository,
        reconciliation_service,
        queue,
        relogio,
    ) = preparar_contexto(tmp_path)

    criar_terminal_historico(
        discovery_repository,
        queue,
        relogio,
        discovery_id="dsc-idempotent",
        status="approved",
    )

    primeiro = reconciliation_service.reconciliar_lote()

    segundo = reconciliation_service.reconciliar_lote()

    assert primeiro.candidatos == 1
    assert primeiro.criados == 1
    assert primeiro.falhas == 0

    assert segundo.candidatos == 0
    assert segundo.processados == 0
    assert segundo.criados == 0
    assert segundo.idempotentes == 0
    assert segundo.falhas == 0

    assert reconciliation_repository.contar_terminais_sem_evidencia() == 0


def test_evidencia_preexistente_exclui_candidato(
    tmp_path: Path,
):
    (
        _banco,
        discovery_repository,
        _trust_repository,
        terminal_hook,
        reconciliation_repository,
        _reconciliation_service,
        queue,
        relogio,
    ) = preparar_contexto(tmp_path)

    terminal = criar_terminal_historico(
        discovery_repository,
        queue,
        relogio,
        discovery_id="dsc-existing",
        status="approved",
    )

    resultado = terminal_hook.processar_terminal(
        descoberta_id=terminal.id,
        conta_id=terminal.conta_id,
        status=terminal.status,
        ocorrido_em=(terminal.atualizado_em),
    )

    assert resultado.sucesso is True
    assert resultado.criado is True

    assert reconciliation_repository.listar_terminais_sem_evidencia() == []


def test_limite_de_lote_e_respeitado(
    tmp_path: Path,
):
    (
        _banco,
        discovery_repository,
        _trust_repository,
        _terminal_hook,
        reconciliation_repository,
        _reconciliation_service,
        queue,
        relogio,
    ) = preparar_contexto(tmp_path)

    for indice in range(3):
        criar_terminal_historico(
            discovery_repository,
            queue,
            relogio,
            discovery_id=(f"dsc-limit-{indice}"),
            status="approved",
        )

        relogio[0] += timedelta(minutes=1)

    candidatos = reconciliation_repository.listar_terminais_sem_evidencia(limite=2)

    assert len(candidatos) == 2

    assert reconciliation_repository.contar_terminais_sem_evidencia() == 3


@dataclass(frozen=True, slots=True)
class ResultadoFalhaFake:
    sucesso: bool
    falhas: tuple[str, ...]
    criado: bool | None = None


class TerminalHookFalhaFake:
    def processar_terminal(
        self,
        **_kwargs,
    ) -> ResultadoFalhaFake:
        return ResultadoFalhaFake(
            sucesso=False,
            falhas=("falha_reconciliacao_fake",),
        )


def test_falha_de_candidato_nao_aborta_lote(
    tmp_path: Path,
):
    (
        _banco,
        discovery_repository,
        _trust_repository,
        _terminal_hook,
        reconciliation_repository,
        _reconciliation_service,
        queue,
        relogio,
    ) = preparar_contexto(tmp_path)

    criar_terminal_historico(
        discovery_repository,
        queue,
        relogio,
        discovery_id="dsc-failure",
        status="approved",
    )

    service = CommunityTrustReconciliationService(
        repository=(reconciliation_repository),
        terminal_hook=(TerminalHookFalhaFake()),
    )

    resultado = service.reconciliar_lote()

    assert resultado.candidatos == 1
    assert resultado.processados == 0
    assert resultado.criados == 0
    assert resultado.idempotentes == 0
    assert resultado.falhas == 1

    assert "dsc-failure:" "falha_reconciliacao_fake" in resultado.falhas_detalhes[0]

    assert reconciliation_repository.contar_terminais_sem_evidencia() == 1


def test_contract_8d3a_preserva_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8D3A-community-trust-reconciliation-core"

    source = data["candidate_source"]

    assert source["terminal_statuses"] == [
        "approved",
        "rejected",
    ]

    assert source["order"] == [
        "atualizado_em ASC",
        "id ASC",
    ]

    processing = data["processing"]

    assert processing["uses_terminal_hook_8d2"] is True

    assert processing["uses_atomic_wiring_8d1"] is True

    assert processing["idempotent"] is True

    boundaries = data["boundaries"]

    assert boundaries["live_database_read"] is False

    assert boundaries["live_database_write"] is False

    assert boundaries["historical_backfill_executed"] is False

    assert boundaries["runtime_composition_activation"] is False

    assert boundaries["gamification_write"] is False


def test_contract_8d3a_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8D3B-controlled-live-backfill"

    validation = data["validation"]

    assert validation["baseline"] == "33124c9"

    assert validation["pre_commit_passed"] is True

    assert validation["isolated_tests_passed_pre_closure"] == 7

    assert validation["community_trust_regression_tests_passed_pre_closure"] == 95

    assert validation["terminal_missing_evidence_query_passed"] is True

    assert validation["deterministic_order_passed"] is True

    assert validation["temporary_backfill_passed"] is True

    assert validation["second_run_idempotency_passed"] is True

    assert validation["candidate_failure_isolation_passed"] is True

    assert validation["live_database_read"] is False

    assert validation["live_database_write"] is False

    assert validation["historical_backfill_executed"] is False

    assert validation["runtime_composition_activation"] is False

    assert validation["gamification_write"] is False

    assert validation["reputation_total_write"] is False
