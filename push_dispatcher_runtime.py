# 63.8738, -149.7525

from __future__ import annotations

import logging
import os
from pathlib import Path

from config.logging_config import configurar_logging
from repositories.alert_engine_repository import AlertEngineRepository
from repositories.personalized_alert_match_repository import (
    PersonalizedAlertMatchRepository,
)
from repositories.personalized_notification_outbox_repository import (
    PersonalizedNotificationOutboxRepository,
)
from repositories.push_delivery_repository import PushDeliveryRepository
from repositories.user_identity_repository import UserIdentityRepository
from services.expo_push_gateway import ExpoPushGateway
from services.personalized_notification_outbox_service import (
    PersonalizedNotificationOutboxService,
)
from services.push_dispatcher_runtime_worker import PushDispatcherRuntimeWorker
from services.push_dispatcher_service import PushDispatcherService
from services.push_payload_builder import PushPayloadBuilder
from services.runtime.orquestrador import DIRETORIO_PROJETO, ConfiguracoesRuntime
from services.user_identity_service import UserIdentityService

logger = logging.getLogger(__name__)


def _caminho_banco(nome: str) -> Path:
    return DIRETORIO_PROJETO / "database" / nome


def construir_worker(
    configuracoes: ConfiguracoesRuntime,
) -> tuple[PushDispatcherRuntimeWorker, ExpoPushGateway]:
    user_db = _caminho_banco("user_identity.sqlite3")

    identity_repository = UserIdentityRepository(user_db)
    identity_service = UserIdentityService(identity_repository)

    match_repository = PersonalizedAlertMatchRepository(user_db)

    outbox_repository = PersonalizedNotificationOutboxRepository(user_db)
    outbox_service = PersonalizedNotificationOutboxService(outbox_repository)

    delivery_repository = PushDeliveryRepository(user_db)

    alert_engine_repository = AlertEngineRepository(
        _caminho_banco("alert_engine.sqlite3"),
    )

    payload_builder = PushPayloadBuilder(
        match_repository=match_repository,
        alert_engine_repository=alert_engine_repository,
    )

    gateway = ExpoPushGateway()

    dispatcher = PushDispatcherService(
        outbox_service=outbox_service,
        identity_service=identity_service,
        delivery_repository=delivery_repository,
        payload_builder=payload_builder,
        gateway=gateway,
        retry_seconds=configuracoes.push_dispatcher_retry_segundos,
    )

    worker = PushDispatcherRuntimeWorker(
        dispatcher=dispatcher,
        intervalo_segundos=configuracoes.push_dispatcher_intervalo_segundos,
        receipt_min_age_segundos=(configuracoes.push_dispatcher_receipt_min_age_segundos),
        max_envios_por_ciclo=configuracoes.push_dispatcher_max_envios_por_ciclo,
    )

    return worker, gateway


def main() -> int:
    os.chdir(DIRETORIO_PROJETO)
    configurar_logging()

    try:
        configuracoes = ConfiguracoesRuntime.carregar()
    except ValueError:
        logger.exception("Configuracao invalida do Push Dispatcher Runtime.")
        return 2

    if not configuracoes.push_dispatcher_ativo:
        logger.info(
            "Push Dispatcher Runtime permanece desativado " "(RUNTIME_PUSH_DISPATCHER_ATIVO=false)."
        )
        return 0

    gateway: ExpoPushGateway | None = None

    try:
        worker, gateway = construir_worker(configuracoes)
        worker.executar()
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupcao solicitada no Push Dispatcher Runtime.")
        return 130
    except Exception:
        logger.exception("Falha nao tratada no Push Dispatcher Runtime.")
        return 1
    finally:
        if gateway is not None:
            gateway.close()


if __name__ == "__main__":
    raise SystemExit(main())
