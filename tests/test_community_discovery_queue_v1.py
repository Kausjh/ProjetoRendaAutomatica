# 63.8738, -149.7525

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from services.community_discovery_queue_service import (
    CommunityDiscoveryQueueService,
)

CONTA_ID = "usr_teste"


def criar_repository(tmp_path):
    banco = tmp_path / "user_identity.sqlite3"

    with sqlite3.connect(banco) as conexao:
        conexao.execute("CREATE TABLE contas_usuario (id TEXT PRIMARY KEY)")
        conexao.execute(
            "INSERT INTO contas_usuario(id) VALUES (?)",
            (CONTA_ID,),
        )

    return CommunityDiscoveryRepository(banco)


def registrar(
    repository,
    *,
    sufixo: str,
    agora: datetime,
):
    item, criada = repository.registrar(
        descoberta_id=f"dsc_{sufixo}",
        conta_id=CONTA_ID,
        url=f"https://example.com/{sufixo}",
        url_normalizada=f"https://example.com/{sufixo}",
        url_hash=f"hash_{sufixo}",
        marketplace="mercado_livre",
        agora=agora.isoformat(),
    )

    assert criada is True
    return item


def test_reserva_atomica_muda_estado_e_incrementa_tentativas(
    tmp_path,
):
    repository = criar_repository(tmp_path)
    agora = datetime(2026, 9, 15, 20, 0, tzinfo=UTC)

    registrar(
        repository,
        sufixo="um",
        agora=agora,
    )

    fila = CommunityDiscoveryQueueService(
        repository,
        agora_provider=lambda: agora,
    )

    reservados = fila.reservar(limite=10)

    assert len(reservados) == 1
    assert reservados[0].status == "processing"
    assert reservados[0].tentativas == 1
    assert reservados[0].processando_desde == agora.isoformat()

    assert fila.reservar(limite=10) == []


def test_erro_transitorio_vira_retry_com_backoff(
    tmp_path,
):
    repository = criar_repository(tmp_path)
    relogio = [
        datetime(2026, 9, 15, 20, 0, tzinfo=UTC),
    ]

    registrar(
        repository,
        sufixo="retry",
        agora=relogio[0],
    )

    fila = CommunityDiscoveryQueueService(
        repository,
        atraso_base_segundos=60,
        agora_provider=lambda: relogio[0],
    )

    item = fila.reservar()[0]

    retry = fila.registrar_erro(
        item.id,
        erro="falha temporaria",
        transitorio=True,
    )

    assert retry.status == "retry"
    assert retry.tentativas == 1
    assert retry.processando_desde is None
    assert retry.motivo_status == "falha temporaria"

    assert fila.reservar() == []

    relogio[0] += timedelta(seconds=61)

    novamente = fila.reservar()

    assert len(novamente) == 1
    assert novamente[0].status == "processing"
    assert novamente[0].tentativas == 2


def test_limite_de_tentativas_vira_rejeicao_terminal(
    tmp_path,
):
    repository = criar_repository(tmp_path)
    agora = datetime(2026, 9, 15, 20, 0, tzinfo=UTC)

    registrar(
        repository,
        sufixo="terminal",
        agora=agora,
    )

    fila = CommunityDiscoveryQueueService(
        repository,
        max_tentativas=1,
        agora_provider=lambda: agora,
    )

    item = fila.reservar()[0]

    rejeitada = fila.registrar_erro(
        item.id,
        erro="falha persistente",
        transitorio=True,
    )

    assert rejeitada.status == "rejected"
    assert rejeitada.motivo_status == "limite_tentativas:falha persistente"


def test_processing_abandonado_volta_e_pode_ser_reservado(
    tmp_path,
):
    repository = criar_repository(tmp_path)
    relogio = [
        datetime(2026, 9, 15, 20, 0, tzinfo=UTC),
    ]

    registrar(
        repository,
        sufixo="stale",
        agora=relogio[0],
    )

    fila = CommunityDiscoveryQueueService(
        repository,
        timeout_processamento_segundos=900,
        agora_provider=lambda: relogio[0],
    )

    primeira = fila.reservar()[0]
    assert primeira.tentativas == 1

    relogio[0] += timedelta(seconds=901)

    segunda = fila.reservar()

    assert len(segunda) == 1
    assert segunda[0].status == "processing"
    assert segunda[0].tentativas == 2


def test_aprovacao_e_rejeicao_exigem_processing(
    tmp_path,
):
    repository = criar_repository(tmp_path)
    agora = datetime(2026, 9, 15, 20, 0, tzinfo=UTC)

    primeiro = registrar(
        repository,
        sufixo="approved",
        agora=agora,
    )

    segundo = registrar(
        repository,
        sufixo="rejected",
        agora=agora,
    )

    fila = CommunityDiscoveryQueueService(
        repository,
        agora_provider=lambda: agora,
    )

    with pytest.raises(ValueError):
        fila.aprovar(
            primeiro.id,
            canonical_key="produto_teste",
        )

    reservados = fila.reservar(limite=10)
    ids = {item.id for item in reservados}

    assert primeiro.id in ids
    assert segundo.id in ids

    aprovada = fila.aprovar(
        primeiro.id,
        canonical_key="produto_teste",
        motivo="oferta_validada",
    )

    rejeitada = fila.rejeitar(
        segundo.id,
        motivo="produto_invalido",
    )

    assert aprovada.status == "approved"
    assert aprovada.canonical_key == "produto_teste"
    assert aprovada.motivo_status == "oferta_validada"

    assert rejeitada.status == "rejected"
    assert rejeitada.motivo_status == "produto_invalido"
