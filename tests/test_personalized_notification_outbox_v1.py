from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from models.personalized_alert_match import EventoAlertaPersonalizavel
from repositories.personalized_alert_match_repository import (
    PersonalizedAlertMatchRepository,
)
from repositories.personalized_notification_outbox_repository import (
    PersonalizedNotificationOutboxRepository,
)
from repositories.user_identity_repository import UserIdentityRepository
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.personalized_alert_matching_service import (
    PersonalizedAlertMatchingService,
)
from services.personalized_notification_outbox_service import (
    PersonalizedNotificationOutboxService,
)
from services.user_identity_service import UserIdentityService
from services.user_personalization_service import UserPersonalizationService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "personalized_notification_outbox_v1.json"
DOC = ROOT / "docs" / "16-notification-outbox.md"
API_SERVER = ROOT / "services" / "api_aplicacao" / "servidor.py"


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
        senha="uma-senha-forte-123",
    )

    return (
        banco,
        identity_service,
        personalization_service,
        matching_service,
        outbox_repo,
        outbox_service,
        conta,
    )


def criar_match(
    personalization_service: UserPersonalizationService,
    matching_service: PersonalizedAlertMatchingService,
    conta,
    *,
    evento_id: str = "evt_1",
    canonical_key: str = "gpu_teste",
):
    personalization_service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key=canonical_key,
        preco_alvo="950.00",
        notificar_queda_preco=False,
    )

    matches = matching_service.processar_evento(
        EventoAlertaPersonalizavel(
            evento_id=evento_id,
            canonical_key=canonical_key,
            tipo_evento="mudanca_preco",
            preco_atual=Decimal("900.00"),
            preco_anterior=Decimal("1000.00"),
            marketplace="mercado_livre",
            ocorrido_em="2026-09-13T12:00:00+00:00",
        )
    )

    assert len(matches) == 1
    return matches[0]


def test_contract_define_outbox_sem_delivery_real():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["schema"] == ("projeto-renda-automatica.personalized-notification-outbox")
    assert data["outbox_version"] == 1
    assert data["stage"] == "delivery-foundation"
    assert data["network_exposure"] is False
    assert data["actual_delivery_enabled"] is False
    assert data["intended_channel"] == "push"


def test_contract_push_ready_sem_provedor():
    delivery = json.loads(CONTRACT.read_text(encoding="utf-8"))["delivery"]

    assert delivery["push_ready"] is True
    assert delivery["push_provider_configured"] is False
    assert delivery["device_tokens_supported"] is False
    assert delivery["provider_credentials_stored"] is False
    assert delivery["external_network_calls"] is False


def test_contract_preserva_api_read_only():
    boundaries = json.loads(CONTRACT.read_text(encoding="utf-8"))["boundaries"]

    assert boundaries["application_api_v1_remains_read_only"] is True
    assert boundaries["new_http_routes"] is False
    assert boundaries["telegram_delivery"] is False
    assert boundaries["email_delivery"] is False


def test_match_persistido_vira_item_outbox(contexto):
    (
        _,
        _,
        pservice,
        matching,
        _,
        outbox,
        conta,
    ) = contexto

    match = criar_match(pservice, matching, conta)

    criados = outbox.sincronizar_matches_pendentes()

    assert len(criados) == 1
    item = criados[0]
    assert item.match_id == match.id
    assert item.conta_id == conta.id
    assert item.canal == "push"
    assert item.status == "pending"
    assert item.tentativas == 0


def test_sincronizacao_e_idempotente(contexto):
    _, _, pservice, matching, repo, outbox, conta = contexto

    match = criar_match(pservice, matching, conta)

    primeiro = outbox.sincronizar_matches_pendentes()
    segundo = outbox.sincronizar_matches_pendentes()

    assert len(primeiro) == 1
    assert segundo == []

    itens = repo.listar_por_conta(conta.id)
    assert len(itens) == 1
    assert itens[0].match_id == match.id


def test_sem_match_sem_outbox(contexto):
    _, _, _, _, repo, outbox, conta = contexto

    assert outbox.sincronizar_matches_pendentes() == []
    assert repo.listar_por_conta(conta.id) == []


def test_reserva_muda_status_e_incrementa_tentativa(contexto):
    _, _, pservice, matching, _, outbox, conta = contexto

    criar_match(pservice, matching, conta)
    outbox.sincronizar_matches_pendentes()

    reservado = outbox.reservar_proximo()

    assert reservado is not None
    assert reservado.status == "processing"
    assert reservado.tentativas == 1


def test_sucesso_finaliza_item(contexto):
    _, _, pservice, matching, _, outbox, conta = contexto

    criar_match(pservice, matching, conta)
    outbox.sincronizar_matches_pendentes()
    reservado = outbox.reservar_proximo()

    assert reservado is not None

    entregue = outbox.registrar_sucesso(reservado.id)

    assert entregue.status == "delivered"
    assert entregue.entregue_em is not None
    assert entregue.ultimo_erro is None
    assert outbox.reservar_proximo() is None


def test_retry_volta_para_pending_e_guarda_erro(contexto):
    _, _, pservice, matching, _, outbox, conta = contexto

    criar_match(pservice, matching, conta)
    outbox.sincronizar_matches_pendentes()
    reservado = outbox.reservar_proximo()

    assert reservado is not None

    retry = outbox.registrar_retry(
        reservado.id,
        erro=" timeout   temporario ",
        atraso_segundos=3600,
    )

    assert retry.status == "pending"
    assert retry.tentativas == 1
    assert retry.ultimo_erro == "timeout temporario"
    assert outbox.reservar_proximo() is None


def test_falha_terminal_finaliza_com_failed(contexto):
    _, _, pservice, matching, _, outbox, conta = contexto

    criar_match(pservice, matching, conta)
    outbox.sincronizar_matches_pendentes()
    reservado = outbox.reservar_proximo()

    assert reservado is not None

    falha = outbox.registrar_falha_terminal(
        reservado.id,
        erro="token futuro invalido",
    )

    assert falha.status == "failed"
    assert falha.ultimo_erro == "token futuro invalido"
    assert falha.entregue_em is None
    assert outbox.reservar_proximo() is None


def test_transicao_invalida_falha_fechada(contexto):
    _, _, pservice, matching, _, outbox, conta = contexto

    criar_match(pservice, matching, conta)
    item = outbox.sincronizar_matches_pendentes()[0]

    with pytest.raises(ValueError, match="processing"):
        outbox.registrar_sucesso(item.id)

    with pytest.raises(ValueError, match="processing"):
        outbox.registrar_falha_terminal(
            item.id,
            erro="falha",
        )


def test_retry_exige_atraso_positivo(contexto):
    _, _, pservice, matching, _, outbox, conta = contexto

    criar_match(pservice, matching, conta)
    outbox.sincronizar_matches_pendentes()
    reservado = outbox.reservar_proximo()

    assert reservado is not None

    with pytest.raises(ValueError, match="positivo"):
        outbox.registrar_retry(
            reservado.id,
            erro="timeout",
            atraso_segundos=0,
        )


def test_erro_vazio_e_rejeitado(contexto):
    _, _, pservice, matching, _, outbox, conta = contexto

    criar_match(pservice, matching, conta)
    outbox.sincronizar_matches_pendentes()
    reservado = outbox.reservar_proximo()

    assert reservado is not None

    with pytest.raises(ValueError, match="nao pode ser vazio"):
        outbox.registrar_falha_terminal(
            reservado.id,
            erro="   ",
        )


def test_usuarios_geram_itens_independentes(contexto):
    (
        _,
        identity_service,
        pservice,
        matching,
        repo,
        outbox,
        conta_a,
    ) = contexto

    conta_b = identity_service.criar_conta(
        email="outro@example.com",
        senha="outra-senha-forte-456",
    )

    criar_match(
        pservice,
        matching,
        conta_a,
        evento_id="evt_a",
    )
    criar_match(
        pservice,
        matching,
        conta_b,
        evento_id="evt_b",
        canonical_key="gpu_teste_b",
    )

    criados = outbox.sincronizar_matches_pendentes()

    assert len(criados) == 2
    assert len(repo.listar_por_conta(conta_a.id)) == 1
    assert len(repo.listar_por_conta(conta_b.id)) == 1


def test_cascade_remove_outbox_ao_remover_match(contexto):
    banco, _, pservice, matching, _, outbox, conta = contexto

    match = criar_match(pservice, matching, conta)
    outbox.sincronizar_matches_pendentes()

    with sqlite3.connect(banco) as conexao:
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.execute(
            "DELETE FROM personalized_alert_matches WHERE id = ?",
            (match.id,),
        )

    with sqlite3.connect(banco) as conexao:
        quantidade = conexao.execute(
            "SELECT COUNT(*) FROM personalized_notification_outbox"
        ).fetchone()[0]

    assert quantidade == 0


def test_bloco_nao_adiciona_rotas_http():
    fonte = API_SERVER.read_text(encoding="utf-8")

    proibidas = (
        "/api/v1/notifications",
        "/api/v1/devices",
        "/api/v1/push",
        "/api/v1/outbox",
    )

    assert all(rota not in fonte for rota in proibidas)


def test_documentacao_declara_fronteiras():
    texto = " ".join(DOC.read_text(encoding="utf-8").split())

    assert "Este bloco não envia push real" in texto
    assert "Este bloco não:" in texto
    assert "nenhuma nova rota HTTP é criada" in texto
    assert "armazena credenciais de provedor" in texto
    assert "armazena tokens de dispositivo" in texto
    assert "Application API V1 continua read-only" in texto
