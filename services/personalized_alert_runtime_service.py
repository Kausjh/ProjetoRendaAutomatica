from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from models.alert_engine import ResultadoAlertEngine
from models.personalized_alert_match import EventoAlertaPersonalizavel
from services.personalized_alert_matching_service import (
    PersonalizedAlertMatchingService,
)
from services.personalized_notification_outbox_service import (
    PersonalizedNotificationOutboxService,
)


@dataclass(frozen=True, slots=True)
class ResultadoPersonalizedAlertRuntime:
    eventos_processados: int
    correspondencias: int
    itens_outbox_criados: int


class PersonalizedAlertRuntimeService:
    def __init__(
        self,
        *,
        matching_service: PersonalizedAlertMatchingService,
        outbox_service: PersonalizedNotificationOutboxService,
    ) -> None:
        self.matching_service = matching_service
        self.outbox_service = outbox_service

    def processar(
        self,
        resultado_alert_engine: ResultadoAlertEngine,
    ) -> ResultadoPersonalizedAlertRuntime:
        correspondencias = 0

        for evento in resultado_alert_engine.eventos:
            preco_anterior = (
                Decimal(str(evento.preco_anterior)) if evento.preco_anterior is not None else None
            )

            matches = self.matching_service.processar_evento(
                EventoAlertaPersonalizavel(
                    evento_id=f"alert_engine:{evento.fingerprint}",
                    canonical_key=evento.chave_canonica,
                    tipo_evento=evento.tipo,
                    preco_atual=Decimal(str(evento.preco_atual)),
                    preco_anterior=preco_anterior,
                    marketplace=evento.marketplace,
                    ocorrido_em=evento.criado_em,
                )
            )
            correspondencias += len(matches)

        itens_outbox = self.outbox_service.sincronizar_matches_pendentes()

        return ResultadoPersonalizedAlertRuntime(
            eventos_processados=len(resultado_alert_engine.eventos),
            correspondencias=correspondencias,
            itens_outbox_criados=len(itens_outbox),
        )
