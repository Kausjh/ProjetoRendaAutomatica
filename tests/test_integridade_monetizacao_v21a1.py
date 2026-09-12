import asyncio
from types import SimpleNamespace

from affiliates.erro_monetizacao_obrigatoria import (
    ErroMonetizacaoObrigatoria,
)
from affiliates.resultado_link_afiliado import ResultadoLinkAfiliado
from bots.telegram_bot import TelegramBot
from models.oferta import Oferta
from publicador_fila import PublicadorFila


class GeradorSemMonetizacaoFake:
    def gerar(self, link: str) -> ResultadoLinkAfiliado:
        return ResultadoLinkAfiliado(
            link_original=link,
            link_publicacao=link,
            afiliador_utilizado="Mercado Livre",
            foi_transformado=False,
        )


class TelegramSemEnvioFake:
    def __init__(self) -> None:
        self.mensagens: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str):
        self.mensagens.append((chat_id, text))


def criar_oferta() -> Oferta:
    return Oferta(
        nome="Produto V21A1",
        loja="Mercado Livre",
        preco=100.0,
        preco_antigo=120.0,
        link="https://www.mercadolivre.com.br/produto/p/MLB123",
        imagem=None,
    )


def criar_telegram_bot() -> TelegramBot:
    bot = object.__new__(TelegramBot)
    bot.channel_id = "@teste"
    bot.gerador_link_afiliado = GeradorSemMonetizacaoFake()
    bot.bot = TelegramSemEnvioFake()
    bot.ultima_mensagem_publicada_id = None
    return bot


def test_telegram_usa_excecao_especifica_para_bloqueio_de_monetizacao():
    bot = criar_telegram_bot()

    try:
        asyncio.run(bot.enviar_oferta(criar_oferta()))
    except ErroMonetizacaoObrigatoria as erro:
        assert "link afiliado" in str(erro)
    else:
        raise AssertionError("Era esperado ErroMonetizacaoObrigatoria.")

    assert bot.bot.mensagens == []


def test_publicador_distingue_afiliacao_pendente_de_erro_generico():
    estados: list[tuple[str, str]] = []
    marcacoes: list[str] = []

    publicador = object.__new__(PublicadorFila)
    publicador.bot = criar_telegram_bot()

    async def garantir_chrome(_link: str) -> None:
        return None

    publicador._garantir_chrome_para_afiliacao = garantir_chrome
    publicador._registrar_estado_fluxo = lambda codigo, detalhe: estados.append((codigo, detalhe))

    publicador.publicados = SimpleNamespace(
        marcar_como_publicada=lambda _link: marcacoes.append("publicados")
    )
    publicador.fila = SimpleNamespace(marcar_publicado=lambda _id: marcacoes.append("fila"))

    item = SimpleNamespace(
        id=1,
        oferta=criar_oferta(),
        pontuacao=90.0,
        resultado_historico=None,
        deve_republicar_por_queda=False,
    )

    resultado = asyncio.run(
        publicador._publicar_item(
            item=item,
            prioridade_editorial=90.0,
            forcar=True,
        )
    )

    assert resultado == "afiliacao_pendente"
    assert estados[-1][0] == "aguardando_afiliacao"
    assert "link afiliado" in estados[-1][1]
    assert marcacoes == []
