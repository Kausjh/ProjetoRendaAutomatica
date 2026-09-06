# 63.8738, -149.7525

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MensagemSocialScout:
    fonte: str
    chat_id: str
    message_id: int

    chat_titulo: str
    texto: str

    chat_username: str | None = None

    links: tuple[str, ...] = ()

    enviado_em: str | None = None
    editado_em: str | None = None

    encaminhada: bool = False
