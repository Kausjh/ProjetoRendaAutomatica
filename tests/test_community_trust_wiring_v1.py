from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest

from models.community_discovery import (
    DescobertaComunitaria,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)
from services.community_trust_discovery_wiring import (
    CommunityTrustDiscoveryWiring,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_trust_wiring_v1.json"


def preparar_banco(
    tmp_path: Path,
) -> CommunityTrustRepository:
    db = tmp_path / "identity.sqlite3"

    with sqlite3.connect(db) as conexao:
        conexao.execute("PRAGMA foreign_keys = ON")

        conexao.execute("""
            CREATE TABLE contas_usuario (
                id TEXT PRIMARY KEY
            )
            """)

        conexao.executemany(
            """
            INSERT INTO contas_usuario (id)
            VALUES (?)
            """,
            [
                ("conta-a",),
                ("conta-b",),
            ],
        )

    return CommunityTrustRepository(db)


def descoberta(
    *,
    discovery_id: str,
    atualizado_em: str,
    status: str = "approved",
    motivo: str = ("pipeline_processada:" "ciclo_pipeline_concluido_com_sucesso"),
    conta_id: str = "conta-a",
) -> DescobertaComunitaria:
    url = "https://example.com/" + discovery_id

    return DescobertaComunitaria(
        id=discovery_id,
        conta_id=conta_id,
        url=url,
        url_normalizada=url,
        marketplace="mercado_livre",
        status=status,
        tentativas=1,
        disponivel_em=atualizado_em,
        processando_desde=None,
        motivo_status=motivo,
        canonical_key=("produto-" + discovery_id if status == "approved" else None),
        criado_em=atualizado_em,
        atualizado_em=atualizado_em,
    )


def iso(
    base: datetime,
    minutos: int,
) -> str:
    return (base + timedelta(minutes=minutos)).isoformat()


def test_approved_pipeline_vira_positive_atomico(
    tmp_path: Path,
):
    repository = preparar_banco(tmp_path)

    wiring = CommunityTrustDiscoveryWiring(repository)

    resultado = wiring.processar(
        descoberta(
            discovery_id="d1",
            atualizado_em=("2026-09-22T10:00:00+00:00"),
        )
    )

    assert resultado.registro.criado is True
    assert resultado.decisao.classificacao == "positive"
    assert resultado.positivas_na_janela == 0

    evidencia = resultado.registro.evidencia

    assert evidencia.classificacao == "positive"
    assert evidencia.motivo == "approved_pipeline_processed"
    assert evidencia.politica_versao == "community-trust-production-v1"
    assert evidencia.metadados["positive_count_before"] == 0
    assert evidencia.metadados["impacto_unidades"] == 1

    perfil = repository.obter_perfil("conta-a")

    assert perfil.evidencias_total == 1
    assert perfil.positivas_total == 1
    assert perfil.negativas_total == 0
    assert perfil.neutras_total == 0


def test_rejected_market_quality_permanece_neutral(
    tmp_path: Path,
):
    repository = preparar_banco(tmp_path)

    wiring = CommunityTrustDiscoveryWiring(repository)

    resultado = wiring.processar(
        descoberta(
            discovery_id="d2",
            atualizado_em=("2026-09-22T10:00:00+00:00"),
            status="rejected",
            motivo=("coletor_fora_nicho:" "produto fora do nicho"),
        )
    )

    assert resultado.decisao.classificacao == "neutral"
    assert resultado.decisao.impacto_unidades == 0

    perfil = repository.obter_perfil("conta-a")

    assert perfil.evidencias_total == 1
    assert perfil.positivas_total == 0
    assert perfil.negativas_total == 0
    assert perfil.neutras_total == 1


def test_retry_idempotente_preserva_decisao_original(
    tmp_path: Path,
):
    repository = preparar_banco(tmp_path)

    wiring = CommunityTrustDiscoveryWiring(repository)

    item = descoberta(
        discovery_id="d3",
        atualizado_em=("2026-09-22T10:00:00+00:00"),
    )

    primeiro = wiring.processar(item)

    segundo = wiring.processar(item)

    assert primeiro.registro.criado is True
    assert segundo.registro.criado is False

    assert primeiro.registro.evidencia.id == segundo.registro.evidencia.id

    assert segundo.positivas_na_janela == primeiro.positivas_na_janela == 0

    perfil = repository.obter_perfil("conta-a")

    assert perfil.evidencias_total == 1
    assert perfil.positivas_total == 1


def test_decima_primeira_positive_vira_neutral(
    tmp_path: Path,
):
    repository = preparar_banco(tmp_path)

    wiring = CommunityTrustDiscoveryWiring(repository)

    base = datetime(
        2026,
        9,
        22,
        10,
        0,
        tzinfo=UTC,
    )

    resultados = []

    for indice in range(11):
        resultados.append(
            wiring.processar(
                descoberta(
                    discovery_id=(f"cap-{indice:02d}"),
                    atualizado_em=iso(
                        base,
                        indice,
                    ),
                )
            )
        )

    assert [item.decisao.classificacao for item in resultados[:10]] == ["positive"] * 10

    ultimo = resultados[10]

    assert ultimo.positivas_na_janela == 10

    assert ultimo.decisao.classificacao == "neutral"

    assert ultimo.decisao.motivo_politica == "positive_window_cap_exceeded"

    perfil = repository.obter_perfil("conta-a")

    assert perfil.evidencias_total == 11
    assert perfil.positivas_total == 10
    assert perfil.neutras_total == 1


def test_positive_fora_da_janela_nao_conta(
    tmp_path: Path,
):
    repository = preparar_banco(tmp_path)

    wiring = CommunityTrustDiscoveryWiring(repository)

    base = datetime(
        2026,
        9,
        20,
        10,
        0,
        tzinfo=UTC,
    )

    for indice in range(10):
        wiring.processar(
            descoberta(
                discovery_id=(f"old-{indice:02d}"),
                atualizado_em=iso(
                    base,
                    indice,
                ),
            )
        )

    novo_instante = (
        base
        + timedelta(
            days=1,
            hours=1,
        )
    ).isoformat()

    novo = wiring.processar(
        descoberta(
            discovery_id="new-window",
            atualizado_em=novo_instante,
        )
    )

    assert novo.positivas_na_janela == 0
    assert novo.decisao.classificacao == "positive"


def test_concorrencia_nao_ultrapassa_cap_positive(
    tmp_path: Path,
):
    repository = preparar_banco(tmp_path)

    wiring = CommunityTrustDiscoveryWiring(repository)

    base = datetime(
        2026,
        9,
        22,
        10,
        0,
        tzinfo=UTC,
    )

    for indice in range(9):
        wiring.processar(
            descoberta(
                discovery_id=(f"seed-{indice:02d}"),
                atualizado_em=iso(
                    base,
                    indice,
                ),
            )
        )

    barreira = Barrier(2)

    instante_concorrente = (base + timedelta(hours=1)).isoformat()

    def executar(
        discovery_id: str,
    ):
        barreira.wait()

        local_wiring = CommunityTrustDiscoveryWiring(repository)

        return local_wiring.processar(
            descoberta(
                discovery_id=discovery_id,
                atualizado_em=(instante_concorrente),
            )
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                executar,
                [
                    "race-a",
                    "race-b",
                ],
            )
        )

    classificacoes = sorted(item.decisao.classificacao for item in resultados)

    assert classificacoes == [
        "neutral",
        "positive",
    ]

    contagens = sorted(item.positivas_na_janela for item in resultados)

    assert contagens == [
        9,
        10,
    ]

    perfil = repository.obter_perfil("conta-a")

    assert perfil.evidencias_total == 11
    assert perfil.positivas_total == 10
    assert perfil.neutras_total == 1


def test_wiring_rejeita_estado_nao_terminal(
    tmp_path: Path,
):
    repository = preparar_banco(tmp_path)

    wiring = CommunityTrustDiscoveryWiring(repository)

    with pytest.raises(
        ValueError,
        match="estado terminal",
    ):
        wiring.processar(
            descoberta(
                discovery_id="received-1",
                atualizado_em=("2026-09-22T10:00:00+00:00"),
                status="received",
                motivo="aguardando",
            )
        )

    perfil = repository.obter_perfil("conta-a")

    assert perfil.evidencias_total == 0


def test_contract_8d1_preserva_fronteiras():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8D1-atomic-trust-decision-ledger-write"

    atomicity = data["atomicity"]

    assert atomicity["positive_window_count_server_side"] is True
    assert atomicity["policy_decision_inside_transaction"] is True
    assert atomicity["ledger_write_same_transaction"] is True
    assert atomicity["concurrent_positive_overrun_fail_closed"] is True

    boundaries = data["boundaries"]

    assert boundaries["community_discovery_terminal_hook"] is False
    assert boundaries["historical_reconciliation"] is False
    assert boundaries["runtime_wiring"] is False
    assert boundaries["live_database_backfill"] is False
    assert boundaries["gamification_write"] is False
    assert boundaries["reputation_total_write"] is False


def test_contract_8d1_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8D2-terminal-community-trust-hook"

    validation = data["validation"]

    assert validation["baseline"] == "8f0babb"

    assert validation["pre_commit_passed"] is True

    assert validation["pre_closure_isolated_tests_passed"] == 8

    assert validation["pre_closure_stage_8_accumulated_tests_passed"] == 72

    assert validation["concurrency_cap_test_passed"] is True

    assert validation["idempotency_test_passed"] is True

    assert validation["positive_window_cap_test_passed"] is True

    assert validation["rejected_neutral_test_passed"] is True

    assert validation["runtime_wiring"] is False

    assert validation["historical_reconciliation"] is False

    assert validation["live_database_write"] is False

    assert validation["gamification_write"] is False
