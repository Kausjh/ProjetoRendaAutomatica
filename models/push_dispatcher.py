from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MensagemPushExpo:
    dispositivo_id: str
    push_token: str = field(repr=False)
    titulo: str
    corpo: str
    dados: dict[str, object]
    canal: str = "ofertas"
    prioridade: str = "high"

    def como_payload(self) -> dict[str, object]:
        token = self.push_token.strip()
        titulo = self.titulo.strip()
        corpo = self.corpo.strip()
        canal = self.canal.strip()

        if not token:
            raise ValueError("push_token obrigatorio.")
        if not titulo:
            raise ValueError("titulo obrigatorio.")
        if not corpo:
            raise ValueError("corpo obrigatorio.")
        if not canal:
            raise ValueError("canal obrigatorio.")
        if self.prioridade not in {"default", "normal", "high"}:
            raise ValueError("prioridade Expo invalida.")

        return {
            "to": token,
            "title": titulo,
            "body": corpo,
            "data": dict(self.dados),
            "channelId": canal,
            "priority": self.prioridade,
        }


@dataclass(frozen=True, slots=True)
class TicketPushExpo:
    status: str
    ticket_id: str | None
    erro_codigo: str | None
    erro_mensagem: str | None


@dataclass(frozen=True, slots=True)
class ReciboPushExpo:
    ticket_id: str
    status: str
    erro_codigo: str | None
    erro_mensagem: str | None


@dataclass(frozen=True, slots=True)
class RegistroTentativaPush:
    id: str
    outbox_id: str
    dispositivo_id: str
    ticket_id: str | None
    ticket_status: str
    receipt_status: str | None
    provider_error_code: str | None
    ultimo_erro: str | None
    criado_em: str
    atualizado_em: str
