from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from models.personalized_alert_match import EventoAlertaPersonalizavel
from models.push_dispatcher import ReciboPushExpo, TicketPushExpo
from repositories.personalized_alert_match_repository import PersonalizedAlertMatchRepository
from repositories.personalized_notification_outbox_repository import (
    PersonalizedNotificationOutboxRepository,
)
from repositories.push_delivery_repository import PushDeliveryRepository
from repositories.user_identity_repository import UserIdentityRepository
from repositories.user_personalization_repository import UserPersonalizationRepository
from services.personalized_alert_matching_service import PersonalizedAlertMatchingService
from services.personalized_notification_outbox_service import PersonalizedNotificationOutboxService
from services.user_identity_service import UserIdentityService
from services.user_personalization_service import UserPersonalizationService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "push_dispatcher_provider_v1.json"
DOC = ROOT / "docs" / "35-push-dispatcher-provider-v1.md"


@pytest.fixture
def contexto(tmp_path: Path):
    banco = tmp_path / "user_identity.sqlite3"

    identity_repo = UserIdentityRepository(banco)
    identity_service = UserIdentityService(identity_repo)
    personalization_repo = UserPersonalizationRepository(banco)
    personalization_service = UserPersonalizationService(
        personalization_repo,
        identity_repo,
    )
    match_repo = PersonalizedAlertMatchRepository(banco)
    matching_service = PersonalizedAlertMatchingService(
        personalization_repository=personalization_repo,
        match_repository=match_repo,
    )
    outbox_repo = PersonalizedNotificationOutboxRepository(banco)
    outbox_service = PersonalizedNotificationOutboxService(outbox_repo)

    conta = identity_service.criar_conta(
        email="usuario@example.com",
        senha="senha-forte-123",
    )
    dispositivo, _, _ = identity_service.registrar_dispositivo(
        conta_id=conta.id,
        instalacao_id="inst_teste_123",
        plataforma="android",
        push_token="ExponentPushToken[token-teste-123456789]",
    )

    personalization_service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
        notificar_queda_preco=False,
    )

    matches = matching_service.processar_evento(
        EventoAlertaPersonalizavel(
            evento_id="evt_push_provider_1",
            canonical_key="gpu_teste",
            tipo_evento="mudanca_preco",
            preco_atual=Decimal("900.00"),
            preco_anterior=Decimal("1000.00"),
            marketplace="mercado_livre",
            ocorrido_em="2026-09-15T15:00:00+00:00",
        )
    )
    assert len(matches) == 1

    outbox = outbox_service.sincronizar_matches_pendentes()[0]
    repo = PushDeliveryRepository(banco)
    return banco, repo, outbox, dispositivo


def test_ticket_ok_fica_aguardando_receipt(contexto):
    _, repo, outbox, dispositivo = contexto

    tentativa = repo.registrar_ticket(
        outbox_id=outbox.id,
        dispositivo_id=dispositivo.id,
        ticket=TicketPushExpo(
            status="ok",
            ticket_id="ticket_1",
            erro_codigo=None,
            erro_mensagem=None,
        ),
    )

    assert tentativa.ticket_status == "ok"
    assert tentativa.receipt_status is None
    assert tentativa.ticket_id == "ticket_1"
    assert [item.id for item in repo.listar_aguardando_recibo()] == [tentativa.id]


def test_receipt_ok_fecha_tentativa_sem_marcar_outbox(contexto):
    banco, repo, outbox, dispositivo = contexto

    repo.registrar_ticket(
        outbox_id=outbox.id,
        dispositivo_id=dispositivo.id,
        ticket=TicketPushExpo(
            status="ok",
            ticket_id="ticket_ok",
            erro_codigo=None,
            erro_mensagem=None,
        ),
    )
    atualizada = repo.registrar_recibo(
        ReciboPushExpo(
            ticket_id="ticket_ok",
            status="ok",
            erro_codigo=None,
            erro_mensagem=None,
        )
    )

    assert atualizada.receipt_status == "ok"
    assert repo.listar_aguardando_recibo() == []

    with sqlite3.connect(banco) as conexao:
        status_outbox = conexao.execute(
            "SELECT status FROM personalized_notification_outbox WHERE id = ?",
            (outbox.id,),
        ).fetchone()[0]
    assert status_outbox == "pending"


def test_ticket_error_persiste_codigo_sem_receipt(contexto):
    _, repo, outbox, dispositivo = contexto

    tentativa = repo.registrar_ticket(
        outbox_id=outbox.id,
        dispositivo_id=dispositivo.id,
        ticket=TicketPushExpo(
            status="error",
            ticket_id=None,
            erro_codigo="DeviceNotRegistered",
            erro_mensagem="device invalido",
        ),
    )

    assert tentativa.ticket_status == "error"
    assert tentativa.receipt_status is None
    assert tentativa.provider_error_code == "DeviceNotRegistered"
    assert repo.listar_aguardando_recibo() == []


def test_receipt_error_persiste_codigo(contexto):
    _, repo, outbox, dispositivo = contexto

    repo.registrar_ticket(
        outbox_id=outbox.id,
        dispositivo_id=dispositivo.id,
        ticket=TicketPushExpo(
            status="ok",
            ticket_id="ticket_error",
            erro_codigo=None,
            erro_mensagem=None,
        ),
    )
    tentativa = repo.registrar_recibo(
        ReciboPushExpo(
            ticket_id="ticket_error",
            status="error",
            erro_codigo="DeviceNotRegistered",
            erro_mensagem="device removido",
        )
    )

    assert tentativa.receipt_status == "error"
    assert tentativa.provider_error_code == "DeviceNotRegistered"
    assert tentativa.ultimo_erro == "device removido"


def test_repository_nao_possui_coluna_push_token(contexto):
    banco, _, _, _ = contexto

    with sqlite3.connect(banco) as conexao:
        colunas = {
            str(row[1])
            for row in conexao.execute("PRAGMA table_info(push_delivery_attempts)").fetchall()
        }

    assert "push_token" not in colunas
    assert "ticket_id" in colunas
    assert "receipt_status" in colunas


def test_fk_impede_dispositivo_inexistente(contexto):
    _, repo, outbox, _ = contexto

    with pytest.raises(sqlite3.IntegrityError):
        repo.registrar_ticket(
            outbox_id=outbox.id,
            dispositivo_id="dev_inexistente",
            ticket=TicketPushExpo(
                status="error",
                ticket_id=None,
                erro_codigo="teste",
                erro_mensagem="teste",
            ),
        )


def test_contract_documenta_semantica_honesta():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert contract["provider"] == "expo-push-service"
    assert contract["limits"]["messages_per_request"] == 100
    assert contract["limits"]["receipt_ids_per_request"] == 1000
    assert contract["semantics"]["ticket_ok"] == "accepted_by_expo_not_delivered"
    assert contract["semantics"]["receipt_ok"] == "accepted_by_fcm_or_apns_not_device_confirmed"
    assert contract["persistence"]["stores_push_token"] is False
    assert contract["boundaries"]["outbox_transition_on_receipt"] is False
    assert contract["boundaries"]["device_revocation_on_device_not_registered"] is False


def test_documentacao_declara_fronteiras():
    texto = " ".join(DOC.read_text(encoding="utf-8").split())

    assert "nao consome automaticamente a outbox" in texto
    assert "nao usa ticket `ok` como sinonimo de `delivered`" in texto
    assert "nao realizam chamadas externas" in texto
    assert "nao envia push real" in texto
