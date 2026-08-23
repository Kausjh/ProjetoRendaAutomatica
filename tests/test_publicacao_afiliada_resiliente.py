import asyncio

from affiliates.resultado_link_afiliado import ResultadoLinkAfiliado
from bots.telegram_bot import TelegramBot
from models.oferta import Oferta
from publicador_fila import PublicadorFila


class GeradorFake:
    def __init__(self, resultado):
        self.resultado = resultado

    def gerar(self, _link):
        return self.resultado


class TelegramFake:
    def __init__(self):
        self.mensagens = []

    async def send_message(self, chat_id, text):
        self.mensagens.append((chat_id, text))


def criar_oferta(link):
    return Oferta(
        nome="Produto de teste",
        loja="Mercado Livre",
        preco=100.0,
        preco_antigo=120.0,
        link=link,
        imagem=None,
    )


def criar_bot(resultado):
    bot = object.__new__(TelegramBot)
    bot.channel_id = "@teste"
    bot.gerador_link_afiliado = GeradorFake(resultado)
    bot.bot = TelegramFake()
    return bot


def test_publicador_identifica_link_mercado_livre():
    assert PublicadorFila._oferta_exige_chrome_afiliacao(
        "https://www.mercadolivre.com.br/produto/p/MLB123"
    )
    assert not PublicadorFila._oferta_exige_chrome_afiliacao("https://example.com/produto")


def test_telegram_bloqueia_mercado_livre_sem_link_afiliado():
    original = "https://www.mercadolivre.com.br/produto/p/MLB123"
    resultado = ResultadoLinkAfiliado(
        link_original=original,
        link_publicacao=original,
        afiliador_utilizado="Mercado Livre",
        foi_transformado=False,
    )
    bot = criar_bot(resultado)

    try:
        asyncio.run(bot.enviar_oferta(criar_oferta(original)))
    except RuntimeError as erro:
        assert "link afiliado" in str(erro)
    else:
        raise AssertionError("Oferta sem monetização não deveria ser publicada.")

    assert bot.bot.mensagens == []


def test_telegram_publica_quando_link_foi_transformado():
    original = "https://www.mercadolivre.com.br/produto/p/MLB123"
    afiliado = "https://meli.la/abc123"
    resultado = ResultadoLinkAfiliado(
        link_original=original,
        link_publicacao=afiliado,
        afiliador_utilizado="Mercado Livre",
        foi_transformado=True,
    )
    bot = criar_bot(resultado)

    asyncio.run(bot.enviar_oferta(criar_oferta(original)))

    assert len(bot.bot.mensagens) == 1
    assert afiliado in bot.bot.mensagens[0][1]
