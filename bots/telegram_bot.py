import logging
from dataclasses import replace

from telegram import Bot

from affiliates.gerador_link_afiliado import GeradorLinkAfiliado
from affiliates.resultado_link_afiliado import (
    ResultadoLinkAfiliado
)
from formatters.oferta_formatter import OfertaFormatter
from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco


logger = logging.getLogger(__name__)


class TelegramBot:

    def __init__(
        self,
        token: str,
        channel_id: str,
        gerador_link_afiliado: GeradorLinkAfiliado
    ) -> None:
        self.bot = Bot(
            token=token
        )

        self.channel_id = channel_id
        self.gerador_link_afiliado = gerador_link_afiliado

    async def enviar_mensagem(
        self,
        mensagem: str
    ) -> None:
        await self.bot.send_message(
            chat_id=self.channel_id,
            text=mensagem
        )

    async def enviar_oferta(
        self,
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None = None
    ) -> ResultadoLinkAfiliado:
        resultado_link = self.gerador_link_afiliado.gerar(
            oferta.link
        )

        logger.info(
            "Link de publicação processado para '%s'. "
            "Afiliador: %s. Transformado: %s.",
            oferta.nome,
            resultado_link.afiliador_utilizado,
            (
                "sim"
                if resultado_link.foi_transformado
                else "não"
            )
        )

        oferta_para_publicacao = replace(
            oferta,
            link=resultado_link.link_publicacao
        )

        mensagem = OfertaFormatter.formatar(
            oferta=oferta_para_publicacao,
            resultado_historico=resultado_historico
        )

        if oferta.imagem:
            try:
                await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=oferta.imagem,
                    caption=mensagem
                )

                return resultado_link

            except Exception:
                logger.warning(
                    "Não foi possível enviar a imagem de '%s'. "
                    "Tentando enviar somente o texto.",
                    oferta.nome,
                    exc_info=True
                )

        await self.bot.send_message(
            chat_id=self.channel_id,
            text=mensagem
        )

        return resultado_link