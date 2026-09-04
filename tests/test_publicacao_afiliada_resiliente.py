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


def test_telegram_publica_preco_condicional_aliexpress():
    original = "https://pt.aliexpress.com/" "item/1005000000000001.html"

    afiliado = "https://www.awin1.com/" "cread.php?teste=1"

    resultado = ResultadoLinkAfiliado(
        link_original=original,
        link_publicacao=afiliado,
        afiliador_utilizado="AliExpress",
        foi_transformado=True,
    )

    bot = criar_bot(resultado)

    oferta = Oferta(
        nome="Produto AliExpress",
        loja="AliExpress",
        preco=40.04,
        preco_antigo=None,
        link=original,
        imagem=None,
        moeda="R$",
        marketplace="aliexpress",
        preco_novo_usuario=25.04,
        moeda_novo_usuario="BRL",
        preco_origem=8.96,
        moeda_origem="CNY",
    )

    asyncio.run(bot.enviar_oferta(oferta))

    assert len(bot.bot.mensagens) == 1

    mensagem = bot.bot.mensagens[0][1]

    assert "\U0001f4b0 Pre\u00e7o: R$ 40.04" in mensagem

    assert "\U0001f381 Novo usu\u00e1rio no AliExpress: " "R$ 25.04" in mensagem

    assert "exclusivo para conta eleg\u00edvel " "de novo usu\u00e1rio" in mensagem

    assert afiliado in mensagem

    assert "CNY" not in mensagem
    assert "8.96" not in mensagem


def test_formatter_nao_exibe_preco_condicional_invalido():
    oferta = Oferta(
        nome="Produto AliExpress",
        loja="AliExpress",
        preco=40.04,
        preco_antigo=None,
        link=("https://pt.aliexpress.com/" "item/1005000000000002.html"),
        imagem=None,
        moeda="R$",
        marketplace="aliexpress",
        preco_novo_usuario=45.00,
        moeda_novo_usuario="BRL",
    )

    from formatters.oferta_formatter import (
        OfertaFormatter,
    )

    mensagem = OfertaFormatter.formatar(
        oferta=oferta,
        resultado_historico=None,
    )

    assert "Novo usu\u00e1rio" not in mensagem

    assert "\U0001f4b0 Pre\u00e7o: R$ 40.04" in mensagem


def test_telegram_bloqueia_shopee_sem_link_afiliado():
    original = "https://shopee.com.br/" "product/123/456"

    resultado = ResultadoLinkAfiliado(
        link_original=original,
        link_publicacao=original,
        afiliador_utilizado="Shopee",
        foi_transformado=False,
    )

    bot = criar_bot(resultado)

    try:
        asyncio.run(bot.enviar_oferta(criar_oferta(original)))

    except RuntimeError as erro:
        assert "link afiliado" in str(erro)

    else:
        raise AssertionError("Oferta Shopee sem monetizacao " "nao deveria ser publicada.")

    assert bot.bot.mensagens == []


def test_telegram_bloqueia_aliexpress_sem_link_afiliado():
    original = "https://pt.aliexpress.com/" "item/1005000000000001.html"

    resultado = ResultadoLinkAfiliado(
        link_original=original,
        link_publicacao=original,
        afiliador_utilizado="AliExpress",
        foi_transformado=False,
    )

    bot = criar_bot(resultado)

    try:
        asyncio.run(bot.enviar_oferta(criar_oferta(original)))

    except RuntimeError as erro:
        assert "link afiliado" in str(erro)

    else:
        raise AssertionError("Oferta AliExpress sem monetizacao " "nao deveria ser publicada.")

    assert bot.bot.mensagens == []
