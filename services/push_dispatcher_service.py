from __future__ import annotations

from models.push_dispatcher import (
    MensagemPushExpo,
    ResultadoEnvioPush,
    ResultadoRecibosPush,
)
from repositories.push_delivery_repository import PushDeliveryRepository
from services.expo_push_gateway import ErroExpoPush, ExpoPushGateway
from services.personalized_notification_outbox_service import (
    PersonalizedNotificationOutboxService,
)
from services.push_payload_builder import PushPayloadBuilder
from services.user_identity_service import UserIdentityService

_RETRYABLE_PROVIDER_CODES = {
    "TOO_MANY_REQUESTS",
    "MessageRateExceeded",
}


class PushDispatcherService:
    def __init__(
        self,
        *,
        outbox_service: PersonalizedNotificationOutboxService,
        identity_service: UserIdentityService,
        delivery_repository: PushDeliveryRepository,
        payload_builder: PushPayloadBuilder,
        gateway: ExpoPushGateway,
        retry_seconds: int = 300,
    ) -> None:
        if retry_seconds < 1:
            raise ValueError("retry_seconds precisa ser positivo.")

        self.outbox_service = outbox_service
        self.identity_service = identity_service
        self.delivery_repository = delivery_repository
        self.payload_builder = payload_builder
        self.gateway = gateway
        self.retry_seconds = int(retry_seconds)

    def processar_proximo_envio(self) -> ResultadoEnvioPush:
        outbox = self.outbox_service.reservar_proximo()
        if outbox is None:
            return ResultadoEnvioPush(status="sem_item", outbox_id=None)

        try:
            conteudo = self.payload_builder.montar(outbox)
        except Exception as erro:
            self.outbox_service.registrar_falha_terminal(
                outbox.id,
                erro=f"payload_invalido:{type(erro).__name__}",
            )
            return ResultadoEnvioPush(
                status="failed_payload",
                outbox_id=outbox.id,
            )

        dispositivos = self.identity_service.listar_dispositivos_ativos(outbox.conta_id)
        if not dispositivos:
            self.outbox_service.registrar_retry(
                outbox.id,
                erro="nenhum_dispositivo_ativo",
                atraso_segundos=self.retry_seconds,
            )
            return ResultadoEnvioPush(
                status="retry_sem_dispositivo",
                outbox_id=outbox.id,
            )

        mensagens = [
            MensagemPushExpo(
                dispositivo_id=dispositivo.id,
                push_token=dispositivo.push_token,
                titulo=conteudo.titulo,
                corpo=conteudo.corpo,
                dados=conteudo.dados,
            )
            for dispositivo in dispositivos
        ]

        try:
            tickets = self.gateway.enviar(mensagens)
        except ErroExpoPush as erro:
            if erro.retryable:
                atraso = erro.retry_after_seconds or self.retry_seconds
                self.outbox_service.registrar_retry(
                    outbox.id,
                    erro=f"expo_temporario:{erro.status_code or 'network'}",
                    atraso_segundos=max(1, atraso),
                )
                return ResultadoEnvioPush(
                    status="retry_provider",
                    outbox_id=outbox.id,
                    dispositivos=len(dispositivos),
                )

            self.outbox_service.registrar_falha_terminal(
                outbox.id,
                erro=f"expo_terminal:{erro.status_code or erro.codigo or 'request'}",
            )
            return ResultadoEnvioPush(
                status="failed_provider",
                outbox_id=outbox.id,
                dispositivos=len(dispositivos),
            )

        tickets_ok = 0
        tickets_erro = 0
        revogados = 0
        erros_codigos: list[str] = []

        for dispositivo, ticket in zip(dispositivos, tickets, strict=True):
            self.delivery_repository.registrar_ticket(
                outbox_id=outbox.id,
                dispositivo_id=dispositivo.id,
                outbox_tentativa=outbox.tentativas,
                ticket=ticket,
            )

            if ticket.status == "ok":
                tickets_ok += 1
                continue

            tickets_erro += 1
            codigo = ticket.erro_codigo or "erro_sem_codigo"
            erros_codigos.append(codigo)

            if codigo == "DeviceNotRegistered":
                revogado = self.identity_service.revogar_dispositivo(
                    conta_id=dispositivo.conta_id,
                    instalacao_id=dispositivo.instalacao_id,
                )
                revogados += int(revogado is not None and not revogado.ativo)

        if tickets_ok > 0:
            return ResultadoEnvioPush(
                status="aguardando_receipts",
                outbox_id=outbox.id,
                dispositivos=len(dispositivos),
                tickets_ok=tickets_ok,
                tickets_erro=tickets_erro,
                dispositivos_revogados=revogados,
            )

        if any(codigo in _RETRYABLE_PROVIDER_CODES for codigo in erros_codigos):
            self.outbox_service.registrar_retry(
                outbox.id,
                erro="tickets_retryable",
                atraso_segundos=self.retry_seconds,
            )
            status = "retry_tickets"
        else:
            self.outbox_service.registrar_falha_terminal(
                outbox.id,
                erro="nenhum_ticket_aceito",
            )
            status = "failed_tickets"

        return ResultadoEnvioPush(
            status=status,
            outbox_id=outbox.id,
            dispositivos=len(dispositivos),
            tickets_ok=0,
            tickets_erro=tickets_erro,
            dispositivos_revogados=revogados,
        )

    def processar_recibos_pendentes(
        self,
        *,
        criado_ate: str | None = None,
    ) -> ResultadoRecibosPush:
        pendentes = self.delivery_repository.listar_aguardando_recibo(
            limite=1000,
            criado_ate=criado_ate,
        )
        if not pendentes:
            return ResultadoRecibosPush(
                status="sem_recibos",
                consultados=0,
                recebidos=0,
            )

        try:
            recibos = self.gateway.obter_recibos(
                [item.ticket_id for item in pendentes if item.ticket_id]
            )
        except ErroExpoPush:
            return ResultadoRecibosPush(
                status="erro_provider",
                consultados=len(pendentes),
                recebidos=0,
            )

        pendente_por_ticket = {
            item.ticket_id: item for item in pendentes if item.ticket_id is not None
        }
        outboxes_afetadas: set[str] = set()
        revogados = 0

        for ticket_id, recibo in recibos.items():
            tentativa = pendente_por_ticket.get(ticket_id)
            if tentativa is None:
                continue

            atualizada = self.delivery_repository.registrar_recibo(recibo)
            outboxes_afetadas.add(atualizada.outbox_id)

            if recibo.erro_codigo == "DeviceNotRegistered":
                dispositivo = self.identity_service.obter_dispositivo_por_id(
                    atualizada.dispositivo_id
                )
                if dispositivo is not None and dispositivo.ativo:
                    revogado = self.identity_service.revogar_dispositivo(
                        conta_id=dispositivo.conta_id,
                        instalacao_id=dispositivo.instalacao_id,
                    )
                    revogados += int(revogado is not None and not revogado.ativo)

        entregues = 0
        retries = 0
        falhas = 0

        for outbox_id in outboxes_afetadas:
            item = self.outbox_service.obter_por_id(outbox_id)
            if item is None or item.status != "processing":
                continue

            tentativas = self.delivery_repository.listar_por_outbox(outbox_id)

            if any(t.receipt_status == "ok" for t in tentativas):
                self.outbox_service.registrar_sucesso(outbox_id)
                entregues += 1
                continue

            atuais = [
                tentativa
                for tentativa in tentativas
                if tentativa.outbox_tentativa == item.tentativas and tentativa.ticket_status == "ok"
            ]

            if not atuais:
                continue
            if any(t.receipt_status is None for t in atuais):
                continue

            codigos = {t.provider_error_code for t in atuais if t.provider_error_code}

            if any(codigo in _RETRYABLE_PROVIDER_CODES for codigo in codigos):
                self.outbox_service.registrar_retry(
                    outbox_id,
                    erro="receipt_retryable",
                    atraso_segundos=self.retry_seconds,
                )
                retries += 1
            else:
                self.outbox_service.registrar_falha_terminal(
                    outbox_id,
                    erro="receipts_sem_entrega",
                )
                falhas += 1

        return ResultadoRecibosPush(
            status="processado",
            consultados=len(pendentes),
            recebidos=len(recibos),
            outboxes_entregues=entregues,
            outboxes_retry=retries,
            outboxes_falha=falhas,
            dispositivos_revogados=revogados,
        )
