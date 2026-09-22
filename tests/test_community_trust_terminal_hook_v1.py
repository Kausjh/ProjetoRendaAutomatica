from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
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
from services.community_trust_terminal_hook import (
    CommunityTrustTerminalHook,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_trust_terminal_hook_v1.json"


def preparar_banco(
    tmp_path: Path,
) -> Path:
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

    return banco


def preparar_stack(
    tmp_path: Path,
    *,
    agora: datetime | None = None,
    max_tentativas: int = 5,
):
    banco = preparar_banco(tmp_path)

    discovery_repository = CommunityDiscoveryRepository(banco)

    trust_repository = CommunityTrustRepository(banco)

    trust_wiring = CommunityTrustDiscoveryWiring(trust_repository)

    terminal_hook = CommunityTrustTerminalHook(
        discovery_repository,
        trust_wiring,
    )

    instante = agora or datetime(
        2026,
        9,
        22,
        16,
        0,
        tzinfo=UTC,
    )

    queue = CommunityDiscoveryQueueService(
        discovery_repository,
        max_tentativas=max_tentativas,
        agora_provider=lambda: instante,
        terminal_hook=terminal_hook,
    )

    return (
        discovery_repository,
        trust_repository,
        terminal_hook,
        queue,
        instante,
    )


def registrar_e_reservar(
    repository: CommunityDiscoveryRepository,
    queue: CommunityDiscoveryQueueService,
    *,
    sufixo: str,
    agora: datetime,
):
    discovery_id = f"dsc-{sufixo}"

    url = "https://example.com/" + sufixo

    repository.registrar(
        descoberta_id=discovery_id,
        conta_id="conta-a",
        url=url,
        url_normalizada=url,
        url_hash=f"hash-{sufixo}",
        marketplace="mercado_livre",
        agora=agora.isoformat(),
    )

    reservadas = queue.reservar(limite=10)

    assert len(reservadas) == 1

    return reservadas[0]


def test_approved_terminal_hook_grava_positive(
    tmp_path: Path,
):
    (
        discovery_repository,
        trust_repository,
        _terminal_hook,
        queue,
        agora,
    ) = preparar_stack(tmp_path)

    item = registrar_e_reservar(
        discovery_repository,
        queue,
        sufixo="approved",
        agora=agora,
    )

    aprovada = queue.aprovar(
        item.id,
        canonical_key="rtx_5060_ti",
        motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
    )

    assert aprovada.status == "approved"

    evidencias = trust_repository.listar_evidencias(conta_id="conta-a")

    assert len(evidencias) == 1

    assert evidencias[0].classificacao == "positive"

    assert evidencias[0].origem_id == aprovada.id


def test_rejected_direto_terminal_hook_grava_neutral(
    tmp_path: Path,
):
    (
        discovery_repository,
        trust_repository,
        _terminal_hook,
        queue,
        agora,
    ) = preparar_stack(tmp_path)

    item = registrar_e_reservar(
        discovery_repository,
        queue,
        sufixo="rejected",
        agora=agora,
    )

    rejeitada = queue.rejeitar(
        item.id,
        motivo=("coletor_fora_nicho:" "produto fora do nicho"),
    )

    assert rejeitada.status == "rejected"

    evidencias = trust_repository.listar_evidencias(conta_id="conta-a")

    assert len(evidencias) == 1

    assert evidencias[0].classificacao == "neutral"


def test_retry_nao_executa_terminal_hook(
    tmp_path: Path,
):
    (
        discovery_repository,
        trust_repository,
        _terminal_hook,
        queue,
        agora,
    ) = preparar_stack(tmp_path)

    item = registrar_e_reservar(
        discovery_repository,
        queue,
        sufixo="retry",
        agora=agora,
    )

    retry = queue.registrar_erro(
        item.id,
        erro="falha temporaria",
        transitorio=True,
    )

    assert retry.status == "retry"

    evidencias = trust_repository.listar_evidencias(conta_id="conta-a")

    assert evidencias == []


def test_rejeicao_terminal_por_erro_executa_hook(
    tmp_path: Path,
):
    (
        discovery_repository,
        trust_repository,
        _terminal_hook,
        queue,
        agora,
    ) = preparar_stack(tmp_path)

    item = registrar_e_reservar(
        discovery_repository,
        queue,
        sufixo="terminal-error",
        agora=agora,
    )

    rejeitada = queue.registrar_erro(
        item.id,
        erro="falha definitiva",
        transitorio=False,
    )

    assert rejeitada.status == "rejected"

    evidencias = trust_repository.listar_evidencias(conta_id="conta-a")

    assert len(evidencias) == 1

    assert evidencias[0].classificacao == "neutral"


@dataclass(frozen=True, slots=True)
class ResultadoHookFake:
    sucesso: bool
    falhas: tuple[str, ...]


class TerminalHookFalhaFake:
    def processar_terminal(
        self,
        **_kwargs,
    ) -> ResultadoHookFake:
        return ResultadoHookFake(
            sucesso=False,
            falhas=("falha_fake",),
        )


def test_falha_terminal_hook_nao_reverte_aprovacao(
    tmp_path: Path,
):
    banco = preparar_banco(tmp_path)

    repository = CommunityDiscoveryRepository(banco)

    agora = datetime(
        2026,
        9,
        22,
        16,
        0,
        tzinfo=UTC,
    )

    queue = CommunityDiscoveryQueueService(
        repository,
        agora_provider=lambda: agora,
        terminal_hook=(TerminalHookFalhaFake()),
    )

    item = registrar_e_reservar(
        repository,
        queue,
        sufixo="hook-failure",
        agora=agora,
    )

    aprovada = queue.aprovar(
        item.id,
        canonical_key="produto-x",
        motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
    )

    assert aprovada.status == "approved"

    persistida = repository.obter_por_id(item.id)

    assert persistida is not None
    assert persistida.status == "approved"


class ApprovalHookFake:
    def __init__(self) -> None:
        self.chamadas = 0

    def processar_aprovacao(
        self,
        **_kwargs,
    ) -> ResultadoHookFake:
        self.chamadas += 1

        return ResultadoHookFake(
            sucesso=True,
            falhas=(),
        )


class TerminalHookOkFake:
    def __init__(self) -> None:
        self.chamadas = 0

    def processar_terminal(
        self,
        **_kwargs,
    ) -> ResultadoHookFake:
        self.chamadas += 1

        return ResultadoHookFake(
            sucesso=True,
            falhas=(),
        )


def test_mission_approval_hook_e_trust_terminal_hook_sao_independentes(
    tmp_path: Path,
):
    banco = preparar_banco(tmp_path)

    repository = CommunityDiscoveryRepository(banco)

    agora = datetime(
        2026,
        9,
        22,
        16,
        0,
        tzinfo=UTC,
    )

    approval_hook = ApprovalHookFake()
    terminal_hook = TerminalHookOkFake()

    queue = CommunityDiscoveryQueueService(
        repository,
        agora_provider=lambda: agora,
        approval_hook=approval_hook,
        terminal_hook=terminal_hook,
    )

    item = registrar_e_reservar(
        repository,
        queue,
        sufixo="dual-hooks",
        agora=agora,
    )

    aprovada = queue.aprovar(
        item.id,
        canonical_key="produto-y",
        motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
    )

    assert aprovada.status == "approved"
    assert approval_hook.chamadas == 1
    assert terminal_hook.chamadas == 1


def test_terminal_hook_e_idempotente(
    tmp_path: Path,
):
    (
        discovery_repository,
        trust_repository,
        terminal_hook,
        queue,
        agora,
    ) = preparar_stack(tmp_path)

    item = registrar_e_reservar(
        discovery_repository,
        queue,
        sufixo="idempotent",
        agora=agora,
    )

    aprovada = queue.aprovar(
        item.id,
        canonical_key="produto-z",
        motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
    )

    repeticao = terminal_hook.processar_terminal(
        descoberta_id=aprovada.id,
        conta_id=aprovada.conta_id,
        status=aprovada.status,
        ocorrido_em=(aprovada.atualizado_em),
    )

    assert repeticao.sucesso is True
    assert repeticao.criado is False

    evidencias = trust_repository.listar_evidencias(conta_id="conta-a")

    assert len(evidencias) == 1


def test_terminal_hook_falha_fechado_em_identidade_divergente(
    tmp_path: Path,
):
    banco = preparar_banco(tmp_path)

    discovery_repository = CommunityDiscoveryRepository(banco)

    trust_repository = CommunityTrustRepository(banco)

    trust_wiring = CommunityTrustDiscoveryWiring(trust_repository)

    terminal_hook = CommunityTrustTerminalHook(
        discovery_repository,
        trust_wiring,
    )

    agora = datetime(
        2026,
        9,
        22,
        16,
        0,
        tzinfo=UTC,
    )

    queue_sem_hook = CommunityDiscoveryQueueService(
        discovery_repository,
        agora_provider=lambda: agora,
    )

    item = registrar_e_reservar(
        discovery_repository,
        queue_sem_hook,
        sufixo="mismatch",
        agora=agora,
    )

    aprovada = queue_sem_hook.aprovar(
        item.id,
        canonical_key="produto-m",
        motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
    )

    resultado = terminal_hook.processar_terminal(
        descoberta_id=aprovada.id,
        conta_id="outra-conta",
        status=aprovada.status,
        ocorrido_em=(aprovada.atualizado_em),
    )

    assert resultado.sucesso is False

    assert resultado.falhas == ("conta_id_divergente",)

    assert trust_repository.listar_evidencias(conta_id="conta-a") == []


def test_contract_8d2_preserva_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8D2-terminal-community-trust-hook"

    queue = data["queue_semantics"]

    assert queue["hook_runs_after_terminal_persistence"] is True

    assert queue["approved_triggers_terminal_hook"] is True

    assert queue["rejected_direct_triggers_terminal_hook"] is True

    assert queue["rejected_after_processing_error_triggers_terminal_hook"] is True

    assert queue["retry_triggers_terminal_hook"] is False

    assert queue["mission_approval_hook_preserved"] is True

    boundaries = data["boundaries"]

    assert boundaries["runtime_composition_activation"] is False

    assert boundaries["historical_reconciliation"] is False

    assert boundaries["live_database_backfill"] is False

    assert boundaries["gamification_write"] is False


def test_contract_8d2_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8D3-community-trust-reconciliation-backfill"

    validation = data["validation"]

    assert validation["baseline"] == "a755396"

    assert validation["pre_commit_passed"] is True

    assert validation["isolated_tests_passed_pre_closure"] == 9

    assert validation["original_queue_tests_passed_pre_closure"] == 5

    assert validation["queue_trust_regression_tests_passed_pre_closure"] == 87

    assert validation["approved_terminal_hook_passed"] is True

    assert validation["rejected_direct_terminal_hook_passed"] is True

    assert validation["terminal_error_rejection_hook_passed"] is True

    assert validation["retry_without_trust_passed"] is True

    assert validation["mission_approval_hook_preserved"] is True

    assert validation["terminal_hook_idempotency_passed"] is True

    assert validation["terminal_persistence_on_hook_failure_passed"] is True

    assert validation["identity_fail_closed_passed"] is True

    assert validation["runtime_composition_activation"] is False

    assert validation["historical_reconciliation"] is False

    assert validation["live_database_backfill"] is False

    assert validation["gamification_write"] is False

    assert validation["reputation_total_write"] is False
