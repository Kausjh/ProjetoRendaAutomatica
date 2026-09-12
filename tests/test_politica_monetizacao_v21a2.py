import asyncio

import pytest

from affiliates.erro_monetizacao_obrigatoria import (
    ErroMonetizacaoObrigatoria,
)
from affiliates.politica_monetizacao import PoliticaMonetizacao
from affiliates.resultado_link_afiliado import ResultadoLinkAfiliado
from bots.telegram_bot import TelegramBot
from models.oferta import Oferta
from publicador_fila import PublicadorFila


@pytest.mark.parametrize(
    "url",
    [
        "https://www.mercadolivre.com.br/produto/p/MLB123",
        "https://produto.mercadolivre.com.br/MLB-123-produto-_JM",
        "https://shopee.com.br/product/123/456",
        "https://s.shopee.com.br/abc123",
        "https://pt.aliexpress.com/item/1005000000000001.html",
        "https://www.kabum.com.br/produto/123",
        "https://www.amazon.com.br/dp/B0ABCDEF12",
        "https://meli.la/abc123",
        "https://amzn.to/abc123",
        "https://link.amazon/abc123",
        "https://tidd.ly/abc123",
        "https://www.awin1.com/cread.php?teste=1",
    ],
)
def test_politica_exige_confirmacao_para_urls_comerciais(url):
    assert PoliticaMonetizacao.exige_confirmacao_afiliacao(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/produto",
        "https://mercadolivre.com.br.evil.example/produto",
        "https://evilmercadolivre.com.br/produto",
        "https://example.com/?next=https://meli.la/abc123",
        "",
    ],
)
def test_politica_nao_confunde_dominios_nao_suportados(url):
    assert not PoliticaMonetizacao.exige_confirmacao_afiliacao(url)


def test_chrome_so_e_exigido_para_mercado_livre_direto():
    assert PoliticaMonetizacao.exige_preparo_chrome_mercado_livre(
        "https://www.mercadolivre.com.br/produto/p/MLB123"
    )
    assert PoliticaMonetizacao.exige_preparo_chrome_mercado_livre(
        "https://produto.mercadolivre.com.br/MLB-123-produto-_JM"
    )
    assert not PoliticaMonetizacao.exige_preparo_chrome_mercado_livre("https://meli.la/abc123")
    assert not PoliticaMonetizacao.exige_preparo_chrome_mercado_livre(
        "https://shopee.com.br/product/123/456"
    )


class GeradorSemTransformacaoFake:
    def __init__(self, link: str):
        self.link = link

    def gerar(self, _link: str) -> ResultadoLinkAfiliado:
        return ResultadoLinkAfiliado(
            link_original=self.link,
            link_publicacao=self.link,
            afiliador_utilizado="Nenhum",
            foi_transformado=False,
        )


class TelegramSemEnvioFake:
    def __init__(self):
        self.mensagens = []

    async def send_message(self, chat_id, text):
        self.mensagens.append((chat_id, text))


def criar_oferta(link: str) -> Oferta:
    return Oferta(
        nome="Produto V21A2",
        loja="Teste",
        preco=100.0,
        preco_antigo=120.0,
        link=link,
        imagem=None,
    )


@pytest.mark.parametrize(
    "link",
    [
        "https://meli.la/abc123",
        "https://tidd.ly/abc123",
        "https://amzn.to/abc123",
        "https://link.amazon/abc123",
        "https://www.awin1.com/cread.php?teste=1",
    ],
)
def test_telegram_bloqueia_intermediario_sem_confirmacao_interna(link):
    bot = object.__new__(TelegramBot)
    bot.channel_id = "@teste"
    bot.gerador_link_afiliado = GeradorSemTransformacaoFake(link)
    bot.bot = TelegramSemEnvioFake()
    bot.ultima_mensagem_publicada_id = None

    with pytest.raises(ErroMonetizacaoObrigatoria):
        asyncio.run(bot.enviar_oferta(criar_oferta(link)))

    assert bot.bot.mensagens == []


def test_wrappers_existentes_delegam_para_politica_central():
    assert TelegramBot._exige_link_afiliado("https://meli.la/abc123")
    assert TelegramBot._exige_link_afiliado("https://tidd.ly/abc123")
    assert PublicadorFila._oferta_exige_chrome_afiliacao(
        "https://www.mercadolivre.com.br/produto/p/MLB123"
    )
    assert not PublicadorFila._oferta_exige_chrome_afiliacao("https://meli.la/abc123")
