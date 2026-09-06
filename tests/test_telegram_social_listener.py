import asyncio
from datetime import UTC, datetime

import pytest

from services.scout.telegram_social_listener import (
    converter_evento_para_mensagem,
    extrair_links_evento,
    extrair_links_texto,
    normalizar_chat_ids,
)


class ChatFake:
    title = "Ofertas Insanas"
    username = "ofertas_insanas"


class EntidadeTextoUrlFake:
    url = "https://www.kabum.com.br/produto/999"


class MensagemFake:
    edit_date = None
    fwd_from = None

    def __init__(
        self,
        entidades=(),
    ):
        self.entidades = entidades

    def get_entities_text(self):
        return self.entidades


class EventoFake:
    chat_id = -1001234567890
    id = 77
    raw_text = "RTX 5070 por R$ 3.299 " "https://www.kabum.com.br/produto/123"
    date = datetime(
        2026,
        9,
        6,
        20,
        0,
        tzinfo=UTC,
    )
    fwd_from = None

    def __init__(
        self,
        mensagem=None,
    ):
        self.message = mensagem if mensagem is not None else MensagemFake()

    async def get_chat(self):
        return ChatFake()


def test_extrair_links_texto():
    texto = "A https://kabum.com.br/produto/1 " "B https://amazon.com.br/dp/XYZ."

    assert extrair_links_texto(texto) == (
        "https://kabum.com.br/produto/1",
        "https://amazon.com.br/dp/XYZ",
    )


def test_extrair_links_remove_duplicatas():
    link = "https://kabum.com.br/produto/1"

    assert extrair_links_texto(f"{link} {link}") == (link,)


def test_normalizar_chat_ids():
    assert normalizar_chat_ids("-1001, -1002; -1001") == (
        -1001,
        -1002,
    )


def test_normalizar_chat_id_invalido():
    with pytest.raises(
        ValueError,
        match="Chat ID invalido",
    ):
        normalizar_chat_ids("-1001,abc")


def test_converter_evento_para_mensagem():
    mensagem = asyncio.run(converter_evento_para_mensagem(EventoFake()))

    assert mensagem.fonte == "telegram"
    assert mensagem.chat_id == "-1001234567890"
    assert mensagem.message_id == 77
    assert mensagem.chat_titulo == "Ofertas Insanas"
    assert mensagem.chat_username == "ofertas_insanas"
    assert mensagem.encaminhada is False

    assert mensagem.links == ("https://www.kabum.com.br/produto/123",)


def test_extrair_url_oculta_em_entidade():
    evento = EventoFake(
        MensagemFake(
            entidades=(
                (
                    EntidadeTextoUrlFake(),
                    "COMPRAR",
                ),
            )
        )
    )

    links = extrair_links_evento(evento)

    assert "https://www.kabum.com.br/produto/999" in links
