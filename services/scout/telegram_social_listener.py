# 63.8738, -149.7525

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from telethon import TelegramClient, events

from models.mensagem_social_scout import MensagemSocialScout
from repositories.mensagens_social_scout_repository import (
    MensagensSocialScoutRepository,
)

logger = logging.getLogger(__name__)

_PADRAO_URL = re.compile(
    r"https?://[^\s<>\"']+",
    flags=re.IGNORECASE,
)


def extrair_links_texto(
    texto: str,
) -> tuple[str, ...]:
    encontrados: list[str] = []

    for bruto in _PADRAO_URL.findall(texto or ""):
        link = bruto.rstrip(".,;:!?)]}")

        if link and link not in encontrados:
            encontrados.append(link)

    return tuple(encontrados)


def normalizar_chat_ids(
    valor: str | Iterable[int | str],
) -> tuple[int, ...]:
    if isinstance(valor, str):
        itens = re.split(
            r"[,;\s]+",
            valor.strip(),
        )
    else:
        itens = list(valor)

    resultado: list[int] = []

    for item in itens:
        texto = str(item).strip()

        if not texto:
            continue

        try:
            chat_id = int(texto)
        except ValueError as erro:
            raise ValueError(f"Chat ID invalido no Social Scout: {texto!r}") from erro

        if chat_id not in resultado:
            resultado.append(chat_id)

    return tuple(resultado)


def _data_iso(
    valor: Any,
) -> str | None:
    if isinstance(valor, datetime):
        return valor.isoformat()

    if valor is None:
        return None

    metodo = getattr(
        valor,
        "isoformat",
        None,
    )

    if callable(metodo):
        return str(metodo())

    return str(valor)


def _adicionar_link(
    destino: list[str],
    link: str | None,
) -> None:
    if not link:
        return

    link = str(link).strip().rstrip(".,;:!?)]}")

    if link and link not in destino:
        destino.append(link)


def extrair_links_evento(
    evento: Any,
) -> tuple[str, ...]:
    links = list(
        extrair_links_texto(
            str(
                getattr(
                    evento,
                    "raw_text",
                    "",
                )
                or ""
            )
        )
    )

    mensagem = getattr(
        evento,
        "message",
        None,
    )

    obter_entidades = getattr(
        mensagem,
        "get_entities_text",
        None,
    )

    if callable(obter_entidades):
        try:
            entidades = obter_entidades()
        except Exception:
            entidades = ()

        for entidade, texto_entidade in entidades:
            url_oculta = getattr(
                entidade,
                "url",
                None,
            )

            if url_oculta:
                _adicionar_link(
                    links,
                    str(url_oculta),
                )
                continue

            for link in extrair_links_texto(str(texto_entidade or "")):
                _adicionar_link(
                    links,
                    link,
                )

    return tuple(links)


async def converter_evento_para_mensagem(
    evento: Any,
) -> MensagemSocialScout:
    chat = await evento.get_chat()

    chat_id = str(
        getattr(
            evento,
            "chat_id",
            "",
        )
    )

    if not chat_id:
        raise ValueError("Evento Telegram sem chat_id.")

    message_id = int(
        getattr(
            evento,
            "id",
            0,
        )
    )

    if message_id <= 0:
        raise ValueError("Evento Telegram sem message_id valido.")

    username = getattr(
        chat,
        "username",
        None,
    )

    titulo = (
        getattr(
            chat,
            "title",
            None,
        )
        or username
        or chat_id
    )

    mensagem = getattr(
        evento,
        "message",
        None,
    )

    encaminhada = (
        getattr(
            evento,
            "fwd_from",
            None,
        )
        is not None
        or getattr(
            mensagem,
            "fwd_from",
            None,
        )
        is not None
    )

    return MensagemSocialScout(
        fonte="telegram",
        chat_id=chat_id,
        message_id=message_id,
        chat_titulo=str(titulo),
        chat_username=(str(username) if username else None),
        texto=str(
            getattr(
                evento,
                "raw_text",
                "",
            )
            or ""
        ),
        links=extrair_links_evento(evento),
        enviado_em=_data_iso(
            getattr(
                evento,
                "date",
                None,
            )
        ),
        editado_em=_data_iso(
            getattr(
                mensagem,
                "edit_date",
                None,
            )
        ),
        encaminhada=encaminhada,
    )


class TelegramSocialListener:
    def __init__(
        self,
        *,
        api_id: int,
        api_hash: str,
        phone: str,
        session_path: str | Path,
        chat_ids: Iterable[int | str],
        repository: MensagensSocialScoutRepository | None = None,
    ) -> None:
        self.api_id = int(api_id)
        self.api_hash = str(api_hash).strip()
        self.phone = str(phone).strip()
        self.session_path = str(session_path)

        self.chat_ids = normalizar_chat_ids(chat_ids)

        if self.api_id <= 0:
            raise ValueError("TELEGRAM_SOCIAL_API_ID invalido.")

        if not self.api_hash:
            raise ValueError("TELEGRAM_SOCIAL_API_HASH vazio.")

        if not self.phone:
            raise ValueError("TELEGRAM_SOCIAL_PHONE vazio.")

        if not self.chat_ids:
            raise ValueError("Nenhum grupo/canal foi autorizado " "em TELEGRAM_SOCIAL_CHAT_IDS.")

        self.repository = repository or MensagensSocialScoutRepository()

    async def _salvar_evento(
        self,
        evento: Any,
    ) -> None:
        try:
            mensagem = await converter_evento_para_mensagem(evento)

            resultado = self.repository.salvar(mensagem)

            logger.info(
                "Social Scout Telegram: " "%s | chat=%s | message=%s | %s",
                mensagem.chat_titulo,
                mensagem.chat_id,
                mensagem.message_id,
                resultado,
            )

        except Exception:
            logger.exception("Falha ao processar mensagem " "recebida pelo Social Scout.")

    async def executar(
        self,
    ) -> None:
        cliente = TelegramClient(
            self.session_path,
            self.api_id,
            self.api_hash,
            sequential_updates=True,
        )

        @cliente.on(events.NewMessage(chats=list(self.chat_ids)))
        async def nova_mensagem(
            evento,
        ) -> None:
            await self._salvar_evento(evento)

        @cliente.on(events.MessageEdited(chats=list(self.chat_ids)))
        async def mensagem_editada(
            evento,
        ) -> None:
            await self._salvar_evento(evento)

        logger.info("Social Scout conectando ao Telegram.")

        await cliente.start(phone=self.phone)

        logger.info(
            "Social Scout ativo em %s " "grupo(s)/canal(is).",
            len(self.chat_ids),
        )

        try:
            await cliente.run_until_disconnected()
        finally:
            await cliente.disconnect()
