from __future__ import annotations

import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.community_moderation_repository import (
    CommunityModerationRepository,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)
from services.community_moderation_authority import (
    AutorizacaoModeracaoNegada,
    CommunityModerationAuthorityV1,
)
from services.community_moderation_service import (
    CommunityModerationService,
)
from services.community_moderation_trust_bridge import (
    CommunityModerationTrustBridge,
    DecisaoModeracaoNaoAutoritativa,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_trust_bridge_v1.json"


TOKEN = "token-admin-8e4-teste"


def preparar(
    tmp_path: Path,
):
    banco = tmp_path / "identity.sqlite3"

    with sqlite3.connect(banco) as conn:

        conn.execute("""
            CREATE TABLE contas_usuario (
                id TEXT PRIMARY KEY
            )
            """)

        for conta in (
            "contributor",
            "reporter-a",
            "reporter-b",
        ):
            conn.execute(
                """
                INSERT INTO contas_usuario (
                    id
                )
                VALUES (?)
                """,
                (conta,),
            )

    discovery_repository = CommunityDiscoveryRepository(banco)

    discovery, criada = discovery_repository.registrar(
        descoberta_id="dsc-1",
        conta_id="contributor",
        url=("https://example.com/" "produto-1"),
        url_normalizada=("https://example.com/" "produto-1"),
        url_hash="hash-dsc-1",
        marketplace="example",
        agora=("2026-09-22T12:00:00+00:00"),
    )

    assert criada is True

    moderation_repository = CommunityModerationRepository(banco)

    trust_repository = CommunityTrustRepository(banco)

    terminal = trust_repository.registrar_evidencia(
        conta_id="contributor",
        chave_idempotencia=("v1:community-discovery:" "dsc-1"),
        tipo_evidencia=("community_discovery_terminal"),
        classificacao="positive",
        origem="community_discovery_v1",
        origem_id="dsc-1",
        motivo="pipeline_processada",
        politica_versao=("community-trust-production-v1"),
        metadados={
            "seed": "8e4-test",
            "impacto_unidades": 1,
        },
        ocorrido_em=("2026-09-22T12:01:00+00:00"),
    )

    authority = CommunityModerationAuthorityV1(token_administrativo=TOKEN)

    bridge = CommunityModerationTrustBridge(
        discovery_repository=(discovery_repository),
        trust_repository=(trust_repository),
    )

    service = CommunityModerationService(
        repository=moderation_repository,
        authority=authority,
        trust_bridge=bridge,
    )

    return {
        "banco": banco,
        "discovery": discovery,
        "discovery_repository": (discovery_repository),
        "moderation_repository": (moderation_repository),
        "trust_repository": (trust_repository),
        "authority": authority,
        "bridge": bridge,
        "service": service,
        "terminal": terminal.evidencia,
    }


def bearer() -> str:
    return f"Bearer {TOKEN}"


def criar_report(
    moderation_repository: CommunityModerationRepository,
    *,
    reporter: str = "reporter-a",
    motivo: str = "spam",
    agora: str = ("2026-09-22T12:10:00+00:00"),
):
    return moderation_repository.registrar_denuncia(
        reporter_conta_id=reporter,
        target_type="community_discovery",
        target_id="dsc-1",
        motivo=motivo,
        detalhes=None,
        agora=agora,
    ).denuncia


def obter_negative(
    trust_repository: CommunityTrustRepository,
):
    evidencias = trust_repository.listar_evidencias(
        conta_id="contributor",
        limite=100,
    )

    return [item for item in evidencias if item.classificacao == "negative"]


def test_confirmed_abuse_cria_negative_separado_sem_mutar_terminal(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    repository = ctx["moderation_repository"]

    trust = ctx["trust_repository"]

    terminal_before = trust.obter_evidencia_por_chave(
        conta_id="contributor",
        chave_idempotencia=("v1:community-discovery:" "dsc-1"),
    )

    assert terminal_before == ctx["terminal"]

    report = criar_report(
        repository,
        motivo="spam",
    )

    resultado = ctx["service"].registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia="confirm-1",
        resultado="confirmed_abuse",
        justificativa="Spam confirmado.",
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    negatives = obter_negative(trust)

    assert len(negatives) == 1

    negative = negatives[0]

    assert negative.tipo_evidencia == ("community_moderation_" "confirmed_abuse")

    assert negative.origem == "community_moderation_v1"

    assert negative.origem_id == resultado.decisao.id

    assert negative.motivo == "spam_confirmado"

    assert negative.chave_idempotencia == (
        "v1:community-moderation:" "community-discovery:" "dsc-1:" "confirmed-abuse"
    )

    assert negative.metadados["impacto_unidades"] == -1

    perfil = trust.obter_perfil("contributor")

    assert perfil.evidencias_total == 2
    assert perfil.positivas_total == 1
    assert perfil.negativas_total == 1
    assert perfil.neutras_total == 0

    terminal_after = trust.obter_evidencia_por_chave(
        conta_id="contributor",
        chave_idempotencia=("v1:community-discovery:" "dsc-1"),
    )

    assert terminal_after == terminal_before


def test_retry_da_mesma_decision_nao_duplica_negative(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    repository = ctx["moderation_repository"]

    report = criar_report(repository)

    first = ctx["service"].registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia="confirm-1",
        resultado="confirmed_abuse",
        justificativa="Confirmado.",
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    second = ctx["service"].registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia="confirm-1",
        resultado="confirmed_abuse",
        justificativa="Confirmado.",
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    assert first.criado is True
    assert second.criado is False

    negatives = obter_negative(ctx["trust_repository"])

    assert len(negatives) == 1

    assert negatives[0].origem_id == first.decisao.id


def test_multiplos_reports_mesma_discovery_nao_empilham_negative(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    repository = ctx["moderation_repository"]

    first_report = criar_report(
        repository,
        reporter="reporter-a",
        motivo="spam",
        agora=("2026-09-22T12:10:00+00:00"),
    )

    second_report = criar_report(
        repository,
        reporter="reporter-b",
        motivo="fraud",
        agora=("2026-09-22T12:11:00+00:00"),
    )

    first = ctx["service"].registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=first_report.id,
        acao_idempotencia="confirm-a",
        resultado="confirmed_abuse",
        justificativa=None,
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    second = ctx["service"].registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=second_report.id,
        acao_idempotencia="confirm-b",
        resultado="confirmed_abuse",
        justificativa=None,
        ocorrido_em=("2026-09-22T12:21:00+00:00"),
    )

    assert first.criado is True
    assert second.criado is True

    negatives = obter_negative(ctx["trust_repository"])

    assert len(negatives) == 1

    assert negatives[0].origem_id == first.decisao.id

    perfil = ctx["trust_repository"].obter_perfil("contributor")

    assert perfil.negativas_total == 1


@pytest.mark.parametrize(
    "outcome",
    [
        "dismissed",
        "keep_under_review",
    ],
)
def test_decision_nao_confirmada_nao_escreve_trust(
    tmp_path: Path,
    outcome: str,
):
    ctx = preparar(tmp_path)

    report = criar_report(
        ctx["moderation_repository"],
        motivo="off_topic",
    )

    ctx["service"].registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia=("action-" + outcome),
        resultado=outcome,
        justificativa=None,
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    negatives = obter_negative(ctx["trust_repository"])

    assert negatives == []

    perfil = ctx["trust_repository"].obter_perfil("contributor")

    assert perfil.evidencias_total == 1
    assert perfil.negativas_total == 0


def test_token_invalido_nao_escreve_decision_nem_trust(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    report = criar_report(ctx["moderation_repository"])

    with pytest.raises(AutorizacaoModeracaoNegada):
        (
            ctx["service"].registrar_decisao_autorizada(
                authorization_header=("Bearer token-errado"),
                denuncia_id=report.id,
                acao_idempotencia="confirm-1",
                resultado="confirmed_abuse",
                justificativa=None,
                ocorrido_em=("2026-09-22T12:20:00+00:00"),
            )
        )

    assert obter_negative(ctx["trust_repository"]) == []

    with sqlite3.connect(ctx["banco"]) as conn:

        total = int(conn.execute("""
                SELECT COUNT(*)
                FROM community_moderation_decisions
                """).fetchone()[0])

    assert total == 0


def test_bridge_rejeita_decision_confirmada_com_actor_forjado(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    repository = ctx["moderation_repository"]

    report = criar_report(repository)

    result = repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="forged-1",
        moderator_actor_id="forged-actor",
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("spam_confirmado"),
        justificativa=None,
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    with pytest.raises(DecisaoModeracaoNaoAutoritativa):
        ctx["bridge"].processar_decisao(result)

    assert obter_negative(ctx["trust_repository"]) == []


def test_bridge_rejeita_family_divergente_do_report(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    repository = ctx["moderation_repository"]

    report = criar_report(
        repository,
        motivo="spam",
    )

    result = repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="mismatch-1",
        moderator_actor_id=(CommunityModerationAuthorityV1.ACTOR_ID),
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("fraude_confirmada"),
        justificativa=None,
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    with pytest.raises(DecisaoModeracaoNaoAutoritativa):
        ctx["bridge"].processar_decisao(result)

    assert obter_negative(ctx["trust_repository"]) == []


def test_bridge_failure_preserva_decision_e_retry_repara(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    repository = ctx["moderation_repository"]

    report = criar_report(repository)

    class BridgeQueFalha:
        def processar_decisao(
            self,
            resultado,
        ):
            raise RuntimeError("falha simulada bridge")

    service_com_falha = CommunityModerationService(
        repository=repository,
        authority=ctx["authority"],
        trust_bridge=BridgeQueFalha(),
    )

    with pytest.raises(
        RuntimeError,
        match="falha simulada bridge",
    ):
        (
            service_com_falha.registrar_decisao_autorizada(
                authorization_header=bearer(),
                denuncia_id=report.id,
                acao_idempotencia="confirm-1",
                resultado="confirmed_abuse",
                justificativa="Confirmado.",
                ocorrido_em=("2026-09-22T12:20:00+00:00"),
            )
        )

    assert obter_negative(ctx["trust_repository"]) == []

    with sqlite3.connect(ctx["banco"]) as conn:

        decision_total = int(conn.execute("""
                SELECT COUNT(*)
                FROM community_moderation_decisions
                """).fetchone()[0])

    assert decision_total == 1

    retry = ctx["service"].registrar_decisao_autorizada(
        authorization_header=bearer(),
        denuncia_id=report.id,
        acao_idempotencia="confirm-1",
        resultado="confirmed_abuse",
        justificativa="Confirmado.",
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    assert retry.criado is False

    negatives = obter_negative(ctx["trust_repository"])

    assert len(negatives) == 1

    assert negatives[0].origem_id == retry.decisao.id


def test_concorrencia_de_confirmacoes_mantem_um_negative(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    repository = ctx["moderation_repository"]

    report_a = criar_report(
        repository,
        reporter="reporter-a",
        motivo="spam",
        agora=("2026-09-22T12:10:00+00:00"),
    )

    report_b = criar_report(
        repository,
        reporter="reporter-b",
        motivo="fraud",
        agora=("2026-09-22T12:11:00+00:00"),
    )

    result_a = repository.registrar_decisao(
        denuncia_id=report_a.id,
        acao_idempotencia="confirm-a",
        moderator_actor_id=(CommunityModerationAuthorityV1.ACTOR_ID),
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("spam_confirmado"),
        justificativa=None,
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    result_b = repository.registrar_decisao(
        denuncia_id=report_b.id,
        acao_idempotencia="confirm-b",
        moderator_actor_id=(CommunityModerationAuthorityV1.ACTOR_ID),
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("fraude_confirmada"),
        justificativa=None,
        ocorrido_em=("2026-09-22T12:21:00+00:00"),
    )

    barrier = threading.Barrier(2)

    def worker(result):
        barrier.wait()

        return ctx["bridge"].processar_decisao(result)

    with ThreadPoolExecutor(max_workers=2) as executor:

        futures = [
            executor.submit(
                worker,
                result_a,
            ),
            executor.submit(
                worker,
                result_b,
            ),
        ]

        bridge_results = [future.result(timeout=10) for future in futures]

    assert sum(int(item.criado) for item in bridge_results) == 1

    negatives = obter_negative(ctx["trust_repository"])

    assert len(negatives) == 1

    assert negatives[0].origem_id in {
        result_a.decisao.id,
        result_b.decisao.id,
    }

    perfil = ctx["trust_repository"].obter_perfil("contributor")

    assert perfil.negativas_total == 1


def test_contract_8e4_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E4-moderation-trust-bridge-core"

    bridge = data["bridge"]

    assert bridge["trigger"] == ("authoritative_" "confirmed_abuse_decision")

    assert bridge["live_injection_enabled"] is False

    assert bridge["non_confirmed_decision_writes_trust"] is False

    assert bridge["requires_authoritative_actor"] is True

    evidence = data["trust_evidence"]

    assert evidence["classification"] == "negative"

    assert evidence["separate_from_terminal_evidence"] is True

    assert evidence["terminal_evidence_mutated"] is False

    idem = data["idempotency"]

    assert idem["scope"] == ("one_negative_per_" "community_discovery")

    assert idem["multiple_reports_do_not_stack_negatives"] is True

    assert idem["multiple_confirmed_decisions_do_not_stack_negatives"] is True

    assert idem["concurrent_confirmed_decisions_do_not_stack_negatives"] is True

    transaction = data["transaction_model"]

    assert transaction["moderation_decision_committed_first"] is True

    assert transaction["bridge_failure_rolls_back_decision"] is False

    assert transaction["idempotent_retry_can_repair_missing_trust_evidence"] is True

    assert transaction["reconciliation_required_for_crash_gap"] is True

    runtime = data["runtime"]

    assert runtime["live_schema_activation"] is False

    assert runtime["live_bridge_injection"] is False

    boundaries = data["validation_boundaries"]

    assert boundaries["tests_use_temporary_databases_only"] is True

    assert boundaries["live_database_write"] is False

    assert data["next_step"] == ("8E5-moderation-trust-" "bridge-reconciliation")


def test_contract_8e4_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E5-moderation-trust-bridge-reconciliation"

    validation = data["validation"]

    assert validation["baseline"] == "cfc4776"

    assert validation["isolated_tests_passed_pre_closure"] == 11

    assert validation["stage_8e_tests_passed_pre_closure"] == 55

    assert validation["trust_moderation_tests_passed_pre_closure"] == 104

    assert validation["one_negative_per_discovery"] is True

    assert validation["multiple_reports_stack_negatives"] is False

    assert validation["multiple_decisions_stack_negatives"] is False

    assert validation["concurrent_decisions_stack_negatives"] is False

    assert validation["first_successful_decision_remains_origin"] is True

    assert validation["terminal_trust_evidence_mutated"] is False

    assert validation["terminal_trust_evidence_reclassified"] is False

    assert validation["idempotent_retry_repairs_bridge"] is True

    assert validation["crash_gap_requires_reconciliation"] is True

    assert validation["live_bridge_injection"] is False

    assert validation["live_database_write"] is False
