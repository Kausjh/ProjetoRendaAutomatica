from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import scrapers.community_discovery_scraper as scraper_module
from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)
from scrapers.community_discovery_scraper import (
    CommunityDiscoveryScraper,
)
from services.community_trust_runtime import (
    criar_terminal_hook_community_trust_live,
)
from services.community_trust_terminal_hook import (
    CommunityTrustTerminalHook,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_trust_runtime_v1.json"


def preparar_banco(
    tmp_path: Path,
) -> Path:
    banco = tmp_path / "identity.sqlite3"

    with sqlite3.connect(banco) as conn:
        conn.execute("""
            CREATE TABLE contas_usuario (
                id TEXT PRIMARY KEY
            )
            """)

        conn.execute(
            """
            INSERT INTO contas_usuario (id)
            VALUES (?)
            """,
            ("conta-a",),
        )

    return banco


def registrar_e_reservar(
    repository: CommunityDiscoveryRepository,
    queue,
    *,
    discovery_id: str,
):
    url = "https://example.com/" + discovery_id

    repository.registrar(
        descoberta_id=discovery_id,
        conta_id="conta-a",
        url=url,
        url_normalizada=url,
        url_hash=("hash-" + discovery_id),
        marketplace="mercado_livre",
        agora="2026-01-01T00:00:00+00:00",
    )

    reservadas = queue.reservar(limite=1)

    assert len(reservadas) == 1
    assert reservadas[0].id == discovery_id

    return reservadas[0]


def test_runtime_factory_cria_terminal_hook_real(
    tmp_path: Path,
):
    banco = preparar_banco(tmp_path)

    discovery_repository = CommunityDiscoveryRepository(banco)

    hook = criar_terminal_hook_community_trust_live(
        caminho_banco=banco,
        discovery_repository=(discovery_repository),
    )

    assert isinstance(
        hook,
        CommunityTrustTerminalHook,
    )


def test_scraper_auto_queue_injeta_terminal_hook(
    tmp_path: Path,
    monkeypatch,
):
    banco = preparar_banco(tmp_path)

    monkeypatch.delenv(
        "MISSIONS_COMMUNITY_RUNTIME_ATIVO",
        raising=False,
    )

    scraper = CommunityDiscoveryScraper(
        caminho_banco=str(banco),
        adapter=object(),
    )

    assert isinstance(
        scraper.queue_service.terminal_hook,
        CommunityTrustTerminalHook,
    )


def test_runtime_approved_grava_positive(
    tmp_path: Path,
    monkeypatch,
):
    banco = preparar_banco(tmp_path)

    monkeypatch.delenv(
        "MISSIONS_COMMUNITY_RUNTIME_ATIVO",
        raising=False,
    )

    scraper = CommunityDiscoveryScraper(
        caminho_banco=str(banco),
        adapter=object(),
    )

    queue = scraper.queue_service
    repository = queue.repository

    item = registrar_e_reservar(
        repository,
        queue,
        discovery_id="dsc-runtime-approved",
    )

    aprovada = queue.aprovar(
        item.id,
        canonical_key="rtx_5060_ti",
        motivo=("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
    )

    assert aprovada.status == "approved"

    trust_repository = CommunityTrustRepository(banco)

    evidencias = trust_repository.listar_evidencias(
        conta_id="conta-a",
        limite=10,
    )

    assert len(evidencias) == 1

    assert evidencias[0].classificacao == "positive"

    assert evidencias[0].origem_id == aprovada.id


def test_runtime_rejected_grava_neutral(
    tmp_path: Path,
    monkeypatch,
):
    banco = preparar_banco(tmp_path)

    monkeypatch.delenv(
        "MISSIONS_COMMUNITY_RUNTIME_ATIVO",
        raising=False,
    )

    scraper = CommunityDiscoveryScraper(
        caminho_banco=str(banco),
        adapter=object(),
    )

    queue = scraper.queue_service
    repository = queue.repository

    item = registrar_e_reservar(
        repository,
        queue,
        discovery_id="dsc-runtime-rejected",
    )

    rejeitada = queue.rejeitar(
        item.id,
        motivo=("coletor_fora_nicho:" "produto fora do nicho"),
    )

    assert rejeitada.status == "rejected"

    trust_repository = CommunityTrustRepository(banco)

    evidencias = trust_repository.listar_evidencias(
        conta_id="conta-a",
        limite=10,
    )

    assert len(evidencias) == 1

    assert evidencias[0].classificacao == "neutral"

    assert evidencias[0].origem_id == rejeitada.id


def test_runtime_factory_failure_e_fail_open(
    tmp_path: Path,
    monkeypatch,
):
    banco = preparar_banco(tmp_path)

    monkeypatch.delenv(
        "MISSIONS_COMMUNITY_RUNTIME_ATIVO",
        raising=False,
    )

    def falhar(**_kwargs):
        raise RuntimeError("falha fake de runtime")

    monkeypatch.setattr(
        scraper_module,
        "criar_terminal_hook_community_trust_live",
        falhar,
    )

    scraper = scraper_module.CommunityDiscoveryScraper(
        caminho_banco=str(banco),
        adapter=object(),
    )

    assert scraper.queue_service.terminal_hook is None

    assert scraper.queue_service.repository is not None


def test_contract_8d4a_runtime_activation():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8D4A-community-trust-runtime-activation"

    composition = data["composition"]

    assert composition["automatic_queue_composition"] is True

    assert composition["terminal_hook_injected"] is True

    assert composition["mission_approval_hook_preserved"] is True

    assert composition["mission_and_trust_hooks_separate"] is True

    assert composition["trust_factory_failure_mode"] == "fail-open"

    assert composition["reconciliation_remains_recovery_path"] is True

    backfill = data["historical_backfill"]

    assert backfill["completed"] is True
    assert backfill["evidence_total"] == 2
    assert backfill["profile_total"] == 1
    assert backfill["remaining_candidates"] == 0

    boundaries = data["boundaries"]

    assert boundaries["live_synthetic_discovery_created"] is False

    assert boundaries["gamification_write"] is False

    assert boundaries["reputation_total_write"] is False


def test_contract_8d4a_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8D4B-final-validation-and-closure"

    validation = data["validation"]

    assert validation["baseline"] == "114dcac"

    assert validation["runtime_tests_passed_pre_closure"] == 6

    assert validation["community_discovery_scraper_tests_passed_pre_closure"] == 7

    assert validation["community_discovery_queue_tests_passed_pre_closure"] == 5

    assert validation["accumulated_8d_tests_passed_pre_closure"] == 109

    assert validation["terminal_hook_injection_passed"] is True

    assert validation["approved_runtime_path_passed"] is True

    assert validation["rejected_runtime_path_passed"] is True

    assert validation["composition_fail_open_passed"] is True

    assert validation["mission_approval_hook_preserved"] is True

    assert validation["mission_and_trust_hooks_separate"] is True

    assert validation["historical_backfill_completed"] is True

    assert validation["live_terminal_total"] == 2

    assert validation["live_trust_evidence_total"] == 2

    assert validation["live_trust_profile_total"] == 1

    assert validation["live_backfill_candidates"] == 0

    assert validation["live_positive_total"] == 1

    assert validation["live_negative_total"] == 0

    assert validation["live_neutral_total"] == 1

    assert validation["live_integrity_check"] == "ok"

    assert validation["live_foreign_key_errors"] == 0

    assert validation["live_database_mutation_during_8d4a"] is False

    assert validation["live_synthetic_discovery_created"] is False

    assert validation["gamification_write"] is False

    assert validation["reputation_total_write"] is False
