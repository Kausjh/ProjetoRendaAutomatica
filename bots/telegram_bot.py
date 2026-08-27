import logging
from dataclasses import replace
from urllib.parse import urlparse

from telegram import Bot, ReplyParameters

from affiliates.gerador_link_afiliado import GeradorLinkAfiliado
from affiliates.resultado_link_afiliado import ResultadoLinkAfiliado
from formatters.oferta_formatter import OfertaFormatter
from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco

logger = logging.getLogger(__name__)


class TelegramBot:

    def __init__(
        self, token: str, channel_id: str, gerador_link_afiliado: GeradorLinkAfiliado
    ) -> None:
        self.bot = Bot(token=token)

        self.channel_id = channel_id
        self.gerador_link_afiliado = gerador_link_afiliado
        self.ultima_mensagem_publicada_id: int | None = None

    @staticmethod
    def _eh_link_mercado_livre(link: str) -> bool:
        dominio = (urlparse(link).hostname or "").lower()

        if dominio.startswith("www."):
            dominio = dominio[4:]

        return dominio == "mercadolivre.com.br" or dominio.endswith(".mercadolivre.com.br")

    async def enviar_mensagem(self, mensagem: str) -> None:
        await self.bot.send_message(chat_id=self.channel_id, text=mensagem)

    async def responder_mensagem(
        self,
        mensagem_id: int,
        mensagem: str,
    ) -> None:
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=mensagem,
                disable_notification=True,
                reply_parameters=ReplyParameters(
                    message_id=mensagem_id,
                ),
            )
        except Exception as erro:
            logger.info(
                "Telegram não vinculou o comentário à publicação; "
                "enviando como mensagem editorial independente. Detalhes: %s",
                erro,
            )
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=mensagem,
                disable_notification=True,
            )

    async def enviar_enquete(
        self,
        pergunta: str,
        opcoes,
    ) -> None:
        await self.bot.send_poll(
            chat_id=self.channel_id,
            question=pergunta,
            options=opcoes,
            is_anonymous=True,
            allows_multiple_answers=False,
            disable_notification=True,
        )

    async def enviar_oferta(
        self, oferta: Oferta, resultado_historico: ResultadoHistoricoPreco | None = None
    ) -> ResultadoLinkAfiliado:
        self.ultima_mensagem_publicada_id = None
        resultado_link = self.gerador_link_afiliado.gerar(oferta.link)

        if self._eh_link_mercado_livre(oferta.link) and not resultado_link.foi_transformado:
            raise RuntimeError(
                "Publicação do Mercado Livre bloqueada porque o link afiliado "
                "não pôde ser gerado. A oferta permanecerá na fila para nova tentativa."
            )

        logger.info(
            "Link de publicação processado para '%s'. " "Afiliador: %s. Transformado: %s.",
            oferta.nome,
            resultado_link.afiliador_utilizado,
            ("sim" if resultado_link.foi_transformado else "não"),
        )

        oferta_para_publicacao = replace(oferta, link=resultado_link.link_publicacao)

        mensagem = OfertaFormatter.formatar(
            oferta=oferta_para_publicacao, resultado_historico=resultado_historico
        )

        if oferta.imagem:
            try:
                mensagem_enviada = await self.bot.send_photo(
                    chat_id=self.channel_id, photo=oferta.imagem, caption=mensagem
                )

                self.ultima_mensagem_publicada_id = getattr(
                    mensagem_enviada,
                    "message_id",
                    None,
                )
                return resultado_link

            except Exception:
                logger.warning(
                    "Não foi possível enviar a imagem de '%s'. " "Tentando enviar somente o texto.",
                    oferta.nome,
                    exc_info=True,
                )

        mensagem_enviada = await self.bot.send_message(chat_id=self.channel_id, text=mensagem)

        self.ultima_mensagem_publicada_id = getattr(
            mensagem_enviada,
            "message_id",
            None,
        )
        return resultado_link
