from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from affiliates.resultado_link_afiliado import (
    ResultadoLinkAfiliado,
)
from bots.telegram_bot import TelegramBot
from models.oferta import Oferta
from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.enforcement_segmentado_monetizacao import (
    EnforcementSegmentadoMonetizacao,
    ErroEnforcementSegmentadoMonetizacao,
)


class GeradorFake:
    def __init__(
        self,
        *,
        afiliador="awin",
    ):
        self.afiliador = afiliador
        self.chamadas = 0

    def gerar(
        self,
        link_original,
    ):
        self.chamadas += 1

        return ResultadoLinkAfiliado(
            link_original=link_original,
            link_publicacao=("https://tidd.ly/abc"),
            afiliador_utilizado=(self.afiliador),
            foi_transformado=True,
        )


class BotInternoFake:
    def __init__(self):
        self.envios = 0

    async def send_message(
        self,
        **kwargs,
    ):
        self.envios += 1

        @dataclass
        class Mensagem:
            message_id: int = 1

        return Mensagem()

    async def send_photo(
        self,
        **kwargs,
    ):
        self.envios += 1

        @dataclass
        class Mensagem:
            message_id: int = 1

        return Mensagem()


def _oferta(
    link,
):
    return Oferta(
        nome="Teste",
        loja="Teste",
        preco=100.0,
        preco_antigo=None,
        link=link,
        imagem=None,
    )


def _telegram(
    tmp_path,
    *,
    link_afiliador="awin",
):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")
    enforcement = EnforcementSegmentadoMonetizacao(repo)
    gerador = GeradorFake(afiliador=link_afiliador)

    bot = object.__new__(TelegramBot)
    bot.channel_id = "@teste"
    bot.gerador_link_afiliado = gerador
    bot.observador_monetizacao = None
    bot.enforcement_segmentado = enforcement
    bot.ultima_mensagem_publicada_id = None
    bot.bot = BotInternoFake()

    return (
        bot,
        gerador,
        repo,
    )


def test_origem_suspensa_bloqueia_antes_do_afiliador(
    tmp_path,
):
    bot, gerador, repo = _telegram(tmp_path)

    repo.definir_enforcement_segmento_monetizacao(
        escopo="origem",
        alvo="mercado_livre",
        ativo=True,
        recomendacao_id="r1",
    )

    with pytest.raises(ErroEnforcementSegmentadoMonetizacao) as erro:
        asyncio.run(bot.enviar_oferta(_oferta("https://www.mercadolivre.com.br/p/1")))

    assert erro.value.escopo == "origem"
    assert gerador.chamadas == 0
    assert bot.bot.envios == 0


def test_afiliador_suspenso_bloqueia_antes_do_telegram(
    tmp_path,
):
    bot, gerador, repo = _telegram(
        tmp_path,
        link_afiliador="awin",
    )

    repo.definir_enforcement_segmento_monetizacao(
        escopo="afiliador",
        alvo="awin",
        ativo=True,
        recomendacao_id="r2",
    )

    with pytest.raises(ErroEnforcementSegmentadoMonetizacao) as erro:
        asyncio.run(bot.enviar_oferta(_oferta("https://www.kabum.com.br/produto/1")))

    assert erro.value.escopo == "afiliador"
    assert gerador.chamadas == 1
    assert bot.bot.envios == 0


def test_segmentos_liberados_nao_bloqueiam(
    tmp_path,
):
    bot, _, repo = _telegram(
        tmp_path,
        link_afiliador="awin",
    )

    repo.definir_enforcement_segmento_monetizacao(
        escopo="origem",
        alvo="kabum",
        ativo=False,
    )

    repo.definir_enforcement_segmento_monetizacao(
        escopo="afiliador",
        alvo="awin",
        ativo=False,
    )

    asyncio.run(bot.enviar_oferta(_oferta("https://www.kabum.com.br/produto/1")))

    assert bot.bot.envios == 1


def test_publicador_retencao_segmentada_nao_contamina_retry_tecnico():
    fonte = open(
        "publicador_fila.py",
        encoding="utf-8-sig",
    ).read()

    assert "ErroEnforcementSegmentadoMonetizacao" in fonte
    assert 'return "segmento_suspenso"' in fonte

    inicio = fonte.index("except ErroEnforcementSegmentadoMonetizacao")
    fim = fonte.index(
        "except ErroMonetizacaoObrigatoria",
        inicio,
    )

    trecho = fonte[inicio:fim]

    assert "segurar_item" in trecho
    assert "registrar_retry_seguro" not in trecho


# 63.8738, -149.7525
