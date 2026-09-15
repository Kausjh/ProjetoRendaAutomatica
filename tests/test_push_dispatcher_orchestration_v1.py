from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import httpx

from models.personalized_alert_match import EventoAlertaPersonalizavel
from models.push_dispatcher import ReciboPushExpo, TicketPushExpo
from repositories.alert_engine_repository import AlertEngineRepository
from repositories.personalized_alert_match_repository import (
    PersonalizedAlertMatchRepository,
)
from repositories.personalized_notification_outbox_repository import (
    PersonalizedNotificationOutboxRepository,
)
from repositories.push_delivery_repository import PushDeliveryRepository
from repositories.user_identity_repository import UserIdentityRepository
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.expo_push_gateway import ExpoPushGateway
from services.personalized_alert_matching_service import (
    PersonalizedAlertMatchingService,
)
from services.personalized_notification_outbox_service import (
    PersonalizedNotificationOutboxService,
)
from services.push_dispatcher_service import PushDispatcherService
from services.push_payload_builder import PushPayloadBuilder
from services.user_identity_service import UserIdentityService
from services.user_personalization_service import UserPersonalizationService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "push_dispatcher_orchestration_v1.json"
DOC = ROOT / "docs" / "36-push-dispatcher-orchestration-v1.md"


def _contexto(tmp_path: Path, handler, *, devices: int = 1):
    user_db = tmp_path / "user_identity.sqlite3"
    alert_db = tmp_path / "alert_engine.sqlite3"

    identity_repo = UserIdentityRepository(user_db)
    identity = UserIdentityService(identity_repo)
    conta = identity.criar_conta(
        email="usuario@example.com",
        senha="senha-forte-123",
    )

    personalization_repo = UserPersonalizationRepository(user_db)
    personalization = UserPersonalizationService(
        personalization_repo,
        identity_repo,
    )
    personalization.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
        notificar_queda_preco=True,
    )

    match_repo = PersonalizedAlertMatchRepository(user_db)
    matching = PersonalizedAlertMatchingService(
        personalization_repository=personalization_repo,
        match_repository=match_repo,
    )
    matches = matching.processar_evento(
        EventoAlertaPersonalizavel(
            evento_id="evt_orquestracao_1",
            canonical_key="gpu_teste",
            tipo_evento="mudanca_preco",
            preco_atual=Decimal("900.00"),
            preco_anterior=Decimal("1000.00"),
            marketplace="mercado_livre",
            ocorrido_em="2026-09-15T15:00:00+00:00",
        )
    )
    assert len(matches) == 1

    outbox_repo = PersonalizedNotificationOutboxRepository(user_db)
    outbox_service = PersonalizedNotificationOutboxService(outbox_repo)
    outbox = outbox_service.sincronizar_matches_pendentes()[0]

    alert_repo = AlertEngineRepository(alert_db)
    alert_repo.inicializar_baseline(
        chave_canonica="gpu_teste",
        nome_canonico="GPU Teste RTX",
        menor_preco_historico=900.0,
        listings=[("mercado_livre", "MLB123", 900.0)],
    )

    dispositivos = []
    for indice in range(devices):
        dispositivo, _, _ = identity.registrar_dispositivo(
            conta_id=conta.id,
            instalacao_id=f"inst_teste_{indice}_abc",
            plataforma="android",
            push_token=f"ExponentPushToken[token-{indice}-123456789]",
        )
        dispositivos.append(dispositivo)

    delivery = PushDeliveryRepository(user_db)
    builder = PushPayloadBuilder(
        match_repository=match_repo,
        alert_engine_repository=alert_repo,
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    gateway = ExpoPushGateway(client=client)
    dispatcher = PushDispatcherService(
        outbox_service=outbox_service,
        identity_service=identity,
        delivery_repository=delivery,
        payload_builder=builder,
        gateway=gateway,
        retry_seconds=60,
    )

    return {
        "user_db": user_db,
        "identity": identity,
        "conta": conta,
        "outbox": outbox,
        "outbox_service": outbox_service,
        "delivery": delivery,
        "dispatcher": dispatcher,
        "dispositivos": dispositivos,
    }


def test_envio_aceito_fica_processing_ate_receipt(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        corpo = json.loads(request.content)
        assert corpo[0]["data"]["canonicalKey"] == "gpu_teste"
        assert corpo[0]["title"] == "Preco-alvo atingido"
        assert "GPU Teste RTX" in corpo[0]["body"]
        return httpx.Response(
            200,
            json={"data": [{"status": "ok", "id": "ticket_1"}]},
        )

    c = _contexto(tmp_path, handler)
    resultado = c["dispatcher"].processar_proximo_envio()

    assert resultado.status == "aguardando_receipts"
    assert resultado.tickets_ok == 1
    item = c["outbox_service"].obter_por_id(c["outbox"].id)
    assert item is not None
    assert item.status == "processing"
    tentativa = c["delivery"].listar_por_outbox(item.id)[0]
    assert tentativa.outbox_tentativa == 1
    assert tentativa.receipt_status is None


def test_receipt_ok_marca_outbox_delivered(tmp_path: Path):
    chamadas = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            return httpx.Response(
                200,
                json={"data": [{"status": "ok", "id": "ticket_1"}]},
            )
        return httpx.Response(
            200,
            json={"data": {"ticket_1": {"status": "ok"}}},
        )

    c = _contexto(tmp_path, handler)
    c["dispatcher"].processar_proximo_envio()
    recibos = c["dispatcher"].processar_recibos_pendentes()

    assert recibos.outboxes_entregues == 1
    item = c["outbox_service"].obter_por_id(c["outbox"].id)
    assert item is not None
    assert item.status == "delivered"


def test_device_not_registered_revoga_so_dispositivo_ruim(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "status": "error",
                        "message": "device dead",
                        "details": {"error": "DeviceNotRegistered"},
                    },
                    {"status": "ok", "id": "ticket_bom"},
                ]
            },
        )

    c = _contexto(tmp_path, handler, devices=2)

    ordem_envio = c["identity"].listar_dispositivos_ativos(c["conta"].id)
    assert len(ordem_envio) == 2

    resultado = c["dispatcher"].processar_proximo_envio()

    assert resultado.status == "aguardando_receipts"
    assert resultado.dispositivos_revogados == 1

    ativos = c["identity"].listar_dispositivos_ativos(c["conta"].id)
    assert len(ativos) == 1
    assert ativos[0].id == ordem_envio[1].id
    assert ordem_envio[0].id not in {dispositivo.id for dispositivo in ativos}


def test_sem_dispositivo_volta_para_retry(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("rede nao deveria ser chamada")

    c = _contexto(tmp_path, handler, devices=0)
    resultado = c["dispatcher"].processar_proximo_envio()

    assert resultado.status == "retry_sem_dispositivo"
    item = c["outbox_service"].obter_por_id(c["outbox"].id)
    assert item is not None
    assert item.status == "pending"
    assert item.tentativas == 1


def test_http_429_volta_para_retry(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "11"},
            json={"errors": [{"code": "TOO_MANY_REQUESTS"}]},
        )

    c = _contexto(tmp_path, handler)
    resultado = c["dispatcher"].processar_proximo_envio()

    assert resultado.status == "retry_provider"
    item = c["outbox_service"].obter_por_id(c["outbox"].id)
    assert item is not None
    assert item.status == "pending"


def test_receipt_ausente_mantem_processing(tmp_path: Path):
    chamadas = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            return httpx.Response(
                200,
                json={"data": [{"status": "ok", "id": "ticket_1"}]},
            )
        return httpx.Response(200, json={"data": {}})

    c = _contexto(tmp_path, handler)
    c["dispatcher"].processar_proximo_envio()
    recibos = c["dispatcher"].processar_recibos_pendentes()

    assert recibos.recebidos == 0
    item = c["outbox_service"].obter_por_id(c["outbox"].id)
    assert item is not None
    assert item.status == "processing"


def test_receipt_device_not_registered_revoga_e_falha_sem_outro_device(
    tmp_path: Path,
):
    chamadas = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            return httpx.Response(
                200,
                json={"data": [{"status": "ok", "id": "ticket_1"}]},
            )
        return httpx.Response(
            200,
            json={
                "data": {
                    "ticket_1": {
                        "status": "error",
                        "message": "device dead",
                        "details": {"error": "DeviceNotRegistered"},
                    }
                }
            },
        )

    c = _contexto(tmp_path, handler)
    c["dispatcher"].processar_proximo_envio()
    recibos = c["dispatcher"].processar_recibos_pendentes()

    assert recibos.dispositivos_revogados == 1
    assert recibos.outboxes_falha == 1
    assert c["identity"].listar_dispositivos_ativos(c["conta"].id) == []
    item = c["outbox_service"].obter_por_id(c["outbox"].id)
    assert item is not None
    assert item.status == "failed"


def _corte_stale_futuro() -> str:
    return "9999-12-31T23:59:59+00:00"


def test_recovery_stale_sem_registro_delivery_volta_para_retry(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("rede nao deveria ser chamada")

    c = _contexto(tmp_path, handler)
    reservado = c["outbox_service"].reservar_proximo()
    assert reservado is not None
    assert reservado.status == "processing"

    recuperacao = c["dispatcher"].recuperar_processamentos_stale(
        atualizado_ate=_corte_stale_futuro()
    )

    item = c["outbox_service"].obter_por_id(reservado.id)
    assert item is not None
    assert item.status == "pending"
    assert item.tentativas == 1
    assert item.ultimo_erro == "recovery_processing_sem_registro_delivery"
    assert recuperacao["avaliados"] == 1
    assert recuperacao["retries"] == 1
    assert recuperacao["sem_registro_delivery"] == 1


def test_recovery_stale_protege_ticket_aceito_sem_receipt(tmp_path: Path):
    chamadas = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chamadas
        chamadas += 1
        return httpx.Response(
            200,
            json={"data": [{"status": "ok", "id": "ticket_stale_1"}]},
        )

    c = _contexto(tmp_path, handler)
    envio = c["dispatcher"].processar_proximo_envio()
    assert envio.status == "aguardando_receipts"

    recuperacao = c["dispatcher"].recuperar_processamentos_stale(
        atualizado_ate=_corte_stale_futuro()
    )

    item = c["outbox_service"].obter_por_id(c["outbox"].id)
    assert item is not None
    assert item.status == "processing"
    assert chamadas == 1
    assert recuperacao["protegidos_receipt_pendente"] == 1
    assert recuperacao["retries"] == 0


def test_recovery_stale_receipt_ok_ja_persistido_entrega_outbox(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"status": "ok", "id": "ticket_stale_ok"}]},
        )

    c = _contexto(tmp_path, handler)
    c["dispatcher"].processar_proximo_envio()
    c["delivery"].registrar_recibo(
        ReciboPushExpo(
            ticket_id="ticket_stale_ok",
            status="ok",
            erro_codigo=None,
            erro_mensagem=None,
        )
    )

    recuperacao = c["dispatcher"].recuperar_processamentos_stale(
        atualizado_ate=_corte_stale_futuro()
    )

    item = c["outbox_service"].obter_por_id(c["outbox"].id)
    assert item is not None
    assert item.status == "delivered"
    assert recuperacao["entregues"] == 1


def test_recovery_stale_ticket_retryable_persistido_volta_para_retry(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("rede nao deveria ser chamada")

    c = _contexto(tmp_path, handler)
    reservado = c["outbox_service"].reservar_proximo()
    assert reservado is not None

    c["delivery"].registrar_ticket(
        outbox_id=reservado.id,
        dispositivo_id=c["dispositivos"][0].id,
        outbox_tentativa=reservado.tentativas,
        ticket=TicketPushExpo(
            status="error",
            ticket_id=None,
            erro_codigo="MessageRateExceeded",
            erro_mensagem="rate limited",
        ),
    )

    recuperacao = c["dispatcher"].recuperar_processamentos_stale(
        atualizado_ate=_corte_stale_futuro()
    )

    item = c["outbox_service"].obter_por_id(reservado.id)
    assert item is not None
    assert item.status == "pending"
    assert item.ultimo_erro == "recovery_tickets_retryable"
    assert recuperacao["retries"] == 1


def test_recovery_stale_ticket_terminal_persistido_falha_outbox(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("rede nao deveria ser chamada")

    c = _contexto(tmp_path, handler)
    reservado = c["outbox_service"].reservar_proximo()
    assert reservado is not None

    c["delivery"].registrar_ticket(
        outbox_id=reservado.id,
        dispositivo_id=c["dispositivos"][0].id,
        outbox_tentativa=reservado.tentativas,
        ticket=TicketPushExpo(
            status="error",
            ticket_id=None,
            erro_codigo="MessageTooBig",
            erro_mensagem="payload rejected",
        ),
    )

    recuperacao = c["dispatcher"].recuperar_processamentos_stale(
        atualizado_ate=_corte_stale_futuro()
    )

    item = c["outbox_service"].obter_por_id(reservado.id)
    assert item is not None
    assert item.status == "failed"
    assert item.ultimo_erro == "recovery_nenhum_ticket_aceito"
    assert recuperacao["falhas"] == 1


def test_contract_e_docs_preservam_fronteiras():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["delivery_semantics"]["ticket_ok_marks_delivered"] is False
    assert contract["delivery_semantics"]["receipt_ok_marks_delivered"] is True
    assert contract["delivery_semantics"]["device_not_registered_revokes_only_device"] is True
    assert contract["boundaries"]["continuous_worker"] is False
    assert contract["boundaries"]["real_device_smoke"] is False

    texto = " ".join(DOC.read_text(encoding="utf-8").split())
    assert "nao envia push real automaticamente" in texto
    assert "Ticket `ok` nao marca a outbox como delivered" in texto
    assert "revoga somente o dispositivo" in texto
