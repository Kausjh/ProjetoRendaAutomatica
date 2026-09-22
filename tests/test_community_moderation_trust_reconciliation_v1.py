from __future__ import annotations

import json
import sqlite3
from pathlib import Path

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
    CommunityModerationAuthorityV1,
)
from services.community_moderation_trust_bridge import (
    CommunityModerationTrustBridge,
)
from services.community_moderation_trust_reconciliation import (
    CommunityModerationTrustReconciliation,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_trust_reconciliation_v1.json"


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
            "contributor-a",
            "contributor-b",
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

    for indice, conta in (
        (1, "contributor-a"),
        (2, "contributor-b"),
    ):
        discovery, criada = discovery_repository.registrar(
            descoberta_id=(f"dsc-{indice}"),
            conta_id=conta,
            url=("https://example.com/" f"produto-{indice}"),
            url_normalizada=("https://example.com/" f"produto-{indice}"),
            url_hash=(f"hash-dsc-{indice}"),
            marketplace="example",
            agora=("2026-09-22T12:00:00+00:00"),
        )

        assert criada is True
        assert discovery.conta_id == conta

    moderation_repository = CommunityModerationRepository(banco)

    trust_repository = CommunityTrustRepository(banco)

    for indice, conta in (
        (1, "contributor-a"),
        (2, "contributor-b"),
    ):
        trust_repository.registrar_evidencia(
            conta_id=conta,
            chave_idempotencia=("v1:community-discovery:" f"dsc-{indice}"),
            tipo_evidencia=("community_discovery_terminal"),
            classificacao="positive",
            origem="community_discovery_v1",
            origem_id=f"dsc-{indice}",
            motivo="pipeline_processada",
            politica_versao=("community-trust-production-v1"),
            metadados={
                "seed": "8e5-test",
                "impacto_unidades": 1,
            },
            ocorrido_em=("2026-09-22T12:01:00+00:00"),
        )

    bridge = CommunityModerationTrustBridge(
        discovery_repository=(discovery_repository),
        trust_repository=(trust_repository),
    )

    reconciliation = CommunityModerationTrustReconciliation(
        moderation_repository=(moderation_repository),
        trust_bridge=bridge,
    )

    return {
        "banco": banco,
        "moderation": moderation_repository,
        "trust": trust_repository,
        "bridge": bridge,
        "reconciliation": reconciliation,
    }


def criar_confirmacao(
    ctx,
    *,
    discovery_id: str = "dsc-1",
    reporter: str = "reporter-a",
    motivo: str = "spam",
    actor: str | None = None,
    familia: str | None = None,
    report_time: str = ("2026-09-22T12:10:00+00:00"),
    decision_time: str = ("2026-09-22T12:20:00+00:00"),
    acao: str = "confirm-1",
):
    actor_final = actor if actor is not None else CommunityModerationAuthorityV1.ACTOR_ID

    familias = {
        "spam": "spam_confirmado",
        "fraud": "fraude_confirmada",
        "malicious_link": ("link_malicioso_confirmado"),
        "abuse": "abuso_confirmado",
    }

    familia_final = familia if familia is not None else familias[motivo]

    report = (
        ctx["moderation"]
        .registrar_denuncia(
            reporter_conta_id=reporter,
            target_type="community_discovery",
            target_id=discovery_id,
            motivo=motivo,
            detalhes=None,
            agora=report_time,
        )
        .denuncia
    )

    result = ctx["moderation"].registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia=acao,
        moderator_actor_id=actor_final,
        resultado="confirmed_abuse",
        familia_abuso_confirmado=(familia_final),
        justificativa=("Confirmacao teste 8E5."),
        ocorrido_em=decision_time,
    )

    return result


def negativas(
    trust: CommunityTrustRepository,
    conta_id: str,
):
    return [
        evidencia
        for evidencia in trust.listar_evidencias(
            conta_id=conta_id,
            limite=100,
        )
        if (evidencia.classificacao == "negative")
    ]


def test_repository_lista_somente_confirmacoes_do_actor(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    good = criar_confirmacao(
        ctx,
        acao="good",
    )

    criar_confirmacao(
        ctx,
        discovery_id="dsc-2",
        reporter="reporter-b",
        actor="forged-actor",
        acao="forged",
    )

    decisoes = ctx["moderation"].listar_decisoes_abuso_confirmado(
        moderator_actor_id=(CommunityModerationAuthorityV1.ACTOR_ID),
        limite=100,
        offset=0,
    )

    assert [item.id for item in decisoes] == [good.decisao.id]


def test_reconciliation_repara_crash_gap(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    persisted = criar_confirmacao(ctx)

    assert (
        negativas(
            ctx["trust"],
            "contributor-a",
        )
        == []
    )

    result = ctx["reconciliation"].reconciliar()

    assert result.examinadas == 1
    assert result.evidencias_criadas == 1
    assert result.evidencias_existentes == 0
    assert result.falhas == ()

    items = negativas(
        ctx["trust"],
        "contributor-a",
    )

    assert len(items) == 1

    assert items[0].origem_id == persisted.decisao.id


def test_reconciliation_repetida_e_idempotente(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    criar_confirmacao(ctx)

    first = ctx["reconciliation"].reconciliar()

    second = ctx["reconciliation"].reconciliar()

    assert first.evidencias_criadas == 1

    assert second.examinadas == 1
    assert second.evidencias_criadas == 0
    assert second.evidencias_existentes == 1
    assert second.falhas == ()

    assert (
        len(
            negativas(
                ctx["trust"],
                "contributor-a",
            )
        )
        == 1
    )


def test_multiplas_decisions_mesma_discovery_nao_empilham(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    first = criar_confirmacao(
        ctx,
        reporter="reporter-a",
        motivo="spam",
        report_time=("2026-09-22T12:10:00+00:00"),
        decision_time=("2026-09-22T12:20:00+00:00"),
        acao="first",
    )

    second = criar_confirmacao(
        ctx,
        reporter="reporter-b",
        motivo="fraud",
        report_time=("2026-09-22T12:11:00+00:00"),
        decision_time=("2026-09-22T12:21:00+00:00"),
        acao="second",
    )

    result = ctx["reconciliation"].reconciliar()

    assert result.examinadas == 2
    assert result.evidencias_criadas == 1
    assert result.evidencias_existentes == 1
    assert result.falhas == ()

    items = negativas(
        ctx["trust"],
        "contributor-a",
    )

    assert len(items) == 1

    assert items[0].origem_id == first.decisao.id

    assert items[0].origem_id != second.decisao.id


def test_existing_negative_conta_como_idempotente(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    persisted = criar_confirmacao(ctx)

    ctx["bridge"].processar_decisao(persisted)

    result = ctx["reconciliation"].reconciliar()

    assert result.examinadas == 1
    assert result.evidencias_criadas == 0
    assert result.evidencias_existentes == 1
    assert result.falhas == ()

    assert (
        len(
            negativas(
                ctx["trust"],
                "contributor-a",
            )
        )
        == 1
    )


def test_non_authoritative_nao_e_candidata(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    criar_confirmacao(
        ctx,
        actor="forged-actor",
    )

    result = ctx["reconciliation"].reconciliar()

    assert result.examinadas == 0
    assert result.evidencias_criadas == 0
    assert result.evidencias_existentes == 0
    assert result.falhas == ()

    assert (
        negativas(
            ctx["trust"],
            "contributor-a",
        )
        == []
    )


def test_family_corrompida_vira_falha_sem_trust_write(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    criar_confirmacao(
        ctx,
        motivo="spam",
        familia="fraude_confirmada",
    )

    result = ctx["reconciliation"].reconciliar()

    assert result.examinadas == 1
    assert result.evidencias_criadas == 0
    assert result.evidencias_existentes == 0
    assert len(result.falhas) == 1

    assert result.falhas[0].tipo_erro == "DecisaoModeracaoNaoAutoritativa"

    assert (
        negativas(
            ctx["trust"],
            "contributor-a",
        )
        == []
    )


def test_falha_de_um_item_nao_bloqueia_outro(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    criar_confirmacao(
        ctx,
        discovery_id="dsc-1",
        reporter="reporter-a",
        motivo="spam",
        familia="fraude_confirmada",
        decision_time=("2026-09-22T12:20:00+00:00"),
        acao="bad",
    )

    criar_confirmacao(
        ctx,
        discovery_id="dsc-2",
        reporter="reporter-b",
        motivo="fraud",
        decision_time=("2026-09-22T12:21:00+00:00"),
        acao="good",
    )

    result = ctx["reconciliation"].reconciliar()

    assert result.examinadas == 2
    assert result.evidencias_criadas == 1
    assert result.evidencias_existentes == 0
    assert len(result.falhas) == 1

    assert (
        negativas(
            ctx["trust"],
            "contributor-a",
        )
        == []
    )

    assert (
        len(
            negativas(
                ctx["trust"],
                "contributor-b",
            )
        )
        == 1
    )


def test_limit_offset_sao_deterministicos(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    first = criar_confirmacao(
        ctx,
        discovery_id="dsc-1",
        reporter="reporter-a",
        decision_time=("2026-09-22T12:20:00+00:00"),
        acao="first",
    )

    second = criar_confirmacao(
        ctx,
        discovery_id="dsc-2",
        reporter="reporter-b",
        motivo="fraud",
        decision_time=("2026-09-22T12:21:00+00:00"),
        acao="second",
    )

    decisions_first = ctx["moderation"].listar_decisoes_abuso_confirmado(
        moderator_actor_id=(CommunityModerationAuthorityV1.ACTOR_ID),
        limite=1,
        offset=0,
    )

    decisions_second = ctx["moderation"].listar_decisoes_abuso_confirmado(
        moderator_actor_id=(CommunityModerationAuthorityV1.ACTOR_ID),
        limite=1,
        offset=1,
    )

    assert decisions_first[0].id == first.decisao.id
    assert decisions_second[0].id == second.decisao.id

    page = ctx["reconciliation"].reconciliar(
        limite=1,
        offset=1,
    )

    assert page.offset_inicial == 1
    assert page.proximo_offset == 2
    assert page.examinadas == 1
    assert page.evidencias_criadas == 1

    assert (
        negativas(
            ctx["trust"],
            "contributor-a",
        )
        == []
    )

    assert (
        len(
            negativas(
                ctx["trust"],
                "contributor-b",
            )
        )
        == 1
    )


def test_terminal_evidence_permanece_inalterada(
    tmp_path: Path,
):
    ctx = preparar(tmp_path)

    key = "v1:community-discovery:" "dsc-1"

    before = ctx["trust"].obter_evidencia_por_chave(
        conta_id="contributor-a",
        chave_idempotencia=key,
    )

    criar_confirmacao(ctx)

    ctx["reconciliation"].reconciliar()

    after = ctx["trust"].obter_evidencia_por_chave(
        conta_id="contributor-a",
        chave_idempotencia=key,
    )

    assert before is not None
    assert after == before


def test_contract_8e5_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E5-moderation-trust-bridge-reconciliation"

    assert data["status"] == "completed"

    selection = data["candidate_selection"]

    assert selection["decision_result"] == "confirmed_abuse"

    assert selection["moderator_actor_id"] == "radar-admin-control-plane-v1"

    assert selection["non_authoritative_decisions_selected"] is False

    reconciliation = data["reconciliation"]

    assert reconciliation["uses_existing_trust_bridge"] is True

    assert reconciliation["creates_second_trust_write_path"] is False

    assert reconciliation["continues_after_single_item_failure"] is True

    assert reconciliation["idempotent_rerun"] is True

    authority = data["authority"]

    assert authority["creates_new_moderation_decision"] is False

    assert authority["requires_new_admin_token"] is False

    assert authority["persisted_actor_revalidated_by_bridge"] is True

    trust = data["trust"]

    assert trust["terminal_evidence_mutated"] is False

    runtime = data["runtime"]

    assert runtime["scheduled_reconciliation_enabled"] is False

    assert runtime["live_reconciliation_execution"] is False

    boundaries = data["validation_boundaries"]

    assert boundaries["tests_use_temporary_databases_only"] is True

    assert boundaries["live_database_write"] is False

    assert data["next_step"] == "8E6-moderation-runtime-composition"


def test_contract_8e5_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E6-moderation-runtime-composition"

    validation = data["validation"]

    assert validation["baseline"] == "f3b5d01"

    assert validation["isolated_tests_passed_pre_closure"] == 11

    assert validation["stage_8e_tests_passed_pre_closure"] == 67

    assert validation["trust_moderation_tests_passed_pre_closure"] == 116

    assert validation["critical_reconciliation_tests_passed"] == 6

    assert validation["crash_gap_reconciliation_implemented"] is True

    assert validation["candidate_result"] == "confirmed_abuse"

    assert validation["candidate_authority"] == "radar-admin-control-plane-v1"

    assert validation["existing_8e4_bridge_reused"] is True

    assert validation["second_trust_write_path_created"] is False

    assert validation["persisted_actor_revalidated"] is True

    assert validation["persisted_reason_family_revalidated"] is True

    assert validation["new_admin_token_required"] is False

    assert validation["reconciliation_rerun_idempotent"] is True

    assert validation["multiple_runs_stack_negatives"] is False

    assert validation["multiple_decisions_stack_negatives"] is False

    assert validation["single_item_failure_blocks_all"] is False

    assert validation["terminal_trust_evidence_mutated"] is False

    assert validation["terminal_trust_evidence_reclassified"] is False

    assert validation["scheduled_reconciliation_enabled"] is False

    assert validation["live_reconciliation_execution"] is False

    assert validation["live_schema_activation"] is False

    assert validation["live_database_write"] is False
