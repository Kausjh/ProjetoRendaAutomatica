import asyncio
import inspect
from types import SimpleNamespace

from affiliates.erro_monetizacao_obrigatoria import (
    ErroMonetizacaoObrigatoria,
)
from models.oferta import Oferta
from publicador_fila import PublicadorFila


class BotFalhaAfiliacao:
    async def enviar_oferta(self, *_args, **_kwargs):
        raise ErroMonetizacaoObrigatoria("link afiliado indisponivel")


def criar_oferta() -> Oferta:
    return Oferta(
        nome="Produto V21A4",
        loja="Mercado Livre",
        preco=100.0,
        preco_antigo=120.0,
        link="https://www.mercadolivre.com.br/produto/p/MLB123",
        imagem=None,
    )


def criar_publicador():
    retencoes = []
    estados = []
    marcacoes = []

    publicador = object.__new__(PublicadorFila)
    publicador.bot = BotFalhaAfiliacao()
    publicador._registrar_estado_fluxo = lambda codigo, detalhe: estados.append((codigo, detalhe))

    async def garantir_chrome(_link):
        return None

    publicador._garantir_chrome_para_afiliacao = garantir_chrome

    publicador.fila = SimpleNamespace(
        segurar_item=lambda item_id, minutos: (retencoes.append((item_id, minutos)) or True),
        marcar_publicado=lambda _id: marcacoes.append("fila"),
    )

    publicador.publicados = SimpleNamespace(
        marcar_como_publicada=lambda _link: marcacoes.append("publicados")
    )

    return (
        publicador,
        retencoes,
        estados,
        marcacoes,
    )


def test_afiliacao_pendente_recebe_cooldown_persistente():
    (
        publicador,
        retencoes,
        estados,
        marcacoes,
    ) = criar_publicador()

    item = SimpleNamespace(
        id=321,
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
    assert retencoes == [
        (
            321,
            PublicadorFila.AFILIACAO_RETRY_MINUTOS,
        )
    ]
    assert PublicadorFila.AFILIACAO_RETRY_MINUTOS == 15
    assert estados[-1][0] == "aguardando_afiliacao"
    assert "15 min" in estados[-1][1]
    assert marcacoes == []


def test_publicador_preserva_cooldown_no_fluxo_agendado():
    fonte = inspect.getsource(PublicadorFila.executar)

    assert 'elif resultado_agendado == "afiliacao_pendente":' in fonte
    assert "cooldown persistente mantido" in fonte
