# 63.8738, -149.7525

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from urllib.parse import urlparse

from affiliates.registro_afiliadores import criar_gerador_link_afiliado
from bots.telegram_bot import TelegramBot
from config.configuracoes import Configuracoes
from config.logging_config import configurar_logging
from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from repositories.publicados_repository import PublicadosRepository
from services.cadencia_publicacao import CadenciaPublicacao
from services.janela_publicacao import JanelaPublicacao
from services.launcher.chrome_launcher import preparar_chrome
from services.seletor_editorial import SeletorEditorial

configurar_logging()

logger = logging.getLogger(__name__)


class PublicadorFila:
    def __init__(self, configuracoes: Configuracoes) -> None:
        self.configuracoes = configuracoes

        gerador_link_afiliado = criar_gerador_link_afiliado(configuracoes)

        self.bot = TelegramBot(
            token=configuracoes.telegram_bot_token,
            channel_id=configuracoes.channel_id,
            gerador_link_afiliado=gerador_link_afiliado,
        )

        self.fila = FilaPublicacaoRepository()
        self.publicados = PublicadosRepository()

        self.janela_publicacao = JanelaPublicacao(
            hora_inicio_madrugada=configuracoes.hora_inicio_madrugada,
            hora_fim_madrugada=configuracoes.hora_fim_madrugada,
            queda_minima_madrugada=configuracoes.queda_minima_madrugada,
            pontuacao_minima_madrugada=configuracoes.pontuacao_minima_madrugada,
            registros_minimos_madrugada=configuracoes.registros_minimos_madrugada,
            nota_comprador_minima_madrugada=(configuracoes.nota_comprador_minima_madrugada),
            queda_minima_menor_preco_madrugada=(configuracoes.queda_minima_menor_preco_madrugada),
            queda_maxima_automatica_madrugada=(configuracoes.queda_maxima_automatica_madrugada),
            ativa=configuracoes.restricao_madrugada_ativa,
        )

        self.seletor = SeletorEditorial(
            cooldown_categoria_minutos=(configuracoes.cooldown_categoria_minutos),
            cooldown_marca_minutos=configuracoes.cooldown_marca_minutos,
            cooldown_canonico_minutos=configuracoes.cooldown_canonico_minutos,
            cooldown_familia_minutos=configuracoes.cooldown_familia_minutos,
            queda_minima_repost_familia_percentual=(
                configuracoes.queda_minima_repost_familia_percentual
            ),
            bloqueio_categoria_minutos=(configuracoes.bloqueio_categoria_minutos),
            janela_saturacao_categoria_minutos=(configuracoes.janela_saturacao_categoria_minutos),
            limite_categoria_janela=configuracoes.limite_categoria_janela,
        )

        self.cadencia = CadenciaPublicacao(
            intervalo_minimo_segundos=(configuracoes.publicacao_intervalo_minimo_segundos),
            intervalo_maximo_segundos=(configuracoes.publicacao_intervalo_maximo_segundos),
            intervalo_modo_segundos=(configuracoes.publicacao_intervalo_modo_segundos),
            chance_intervalo_curto=(configuracoes.publicacao_chance_intervalo_curto),
            intervalo_curto_minimo_segundos=(
                configuracoes.publicacao_intervalo_curto_minimo_segundos
            ),
            intervalo_curto_maximo_segundos=(
                configuracoes.publicacao_intervalo_curto_maximo_segundos
            ),
            urgente_minimo_segundos=(configuracoes.publicacao_urgente_minimo_segundos),
            urgente_maximo_segundos=(configuracoes.publicacao_urgente_maximo_segundos),
        )

    @staticmethod
    def _oferta_exige_chrome_afiliacao(link: str) -> bool:
        dominio = (urlparse(link).hostname or "").lower()

        if dominio.startswith("www."):
            dominio = dominio[4:]

        return dominio == "mercadolivre.com.br" or dominio.endswith(".mercadolivre.com.br")

    async def _garantir_chrome_para_afiliacao(self, link: str) -> None:
        if not self._oferta_exige_chrome_afiliacao(link):
            return

        logger.info(
            "Garantindo Chrome/CDP funcional antes de gerar o link afiliado " "do Mercado Livre."
        )
        await asyncio.to_thread(preparar_chrome)

    async def _publicar_item(
        self,
        item,
        prioridade_editorial: float,
        motivos: list[str] | None = None,
        forcar: bool = False,
    ) -> str:
        if not forcar:
            resultado_janela = self.janela_publicacao.avaliar(
                oferta=item.oferta,
                pontuacao=item.pontuacao,
                resultado_historico=(item.resultado_historico),
            )

            if not resultado_janela.pode_publicar:
                logger.info(
                    ("Fila aguardando horario " "apropriado para '%s': %s"),
                    item.oferta.nome,
                    resultado_janela.motivo,
                )
                return "adiado"

        logger.info(
            (
                "Publicando da fila: %s | score=%.2f | "
                "prioridade editorial=%.2f | familia=%s | "
                "confiança família=%.1f"
            ),
            item.oferta.nome,
            item.pontuacao,
            prioridade_editorial,
            (item.oferta.familia_produto or "nao identificada"),
            item.oferta.confianca_familia,
        )

        if motivos:
            logger.info(
                "Ajustes editoriais: %s",
                " | ".join(motivos),
            )

        if forcar:
            logger.warning(
                ("Publicacao imediata solicitada " "administrativamente para: %s"),
                item.oferta.nome,
            )

        try:
            await self._garantir_chrome_para_afiliacao(item.oferta.link)

            await self.bot.enviar_oferta(
                oferta=item.oferta,
                resultado_historico=(item.resultado_historico),
            )

            self.publicados.marcar_como_publicada(item.oferta.link)

            self.fila.marcar_publicado(item.id)

            logger.info("Oferta publicada com sucesso a partir da fila.")

            return "publicado"

        except Exception:
            logger.exception(
                "Erro ao publicar item da fila: %s",
                item.oferta.nome,
            )

            return "erro"

    async def executar(self) -> None:
        logger.info("=" * 60)
        logger.info("Publicador contínuo da fila iniciado.")
        logger.info(
            (
                "Anti-repost por família ativo: cooldown %.0f min | "
                "queda mínima para republicação antecipada %.1f%%."
            ),
            self.configuracoes.cooldown_familia_minutos,
            self.configuracoes.queda_minima_repost_familia_percentual,
        )
        logger.info(
            "Cadência normal: %.0f-%.0fs, modo %.0fs | curto %.0f-%.0fs (%.0f%%).",
            self.configuracoes.publicacao_intervalo_minimo_segundos,
            self.configuracoes.publicacao_intervalo_maximo_segundos,
            self.configuracoes.publicacao_intervalo_modo_segundos,
            self.configuracoes.publicacao_intervalo_curto_minimo_segundos,
            self.configuracoes.publicacao_intervalo_curto_maximo_segundos,
            self.configuracoes.publicacao_chance_intervalo_curto * 100,
        )
        logger.info("=" * 60)

        proxima_publicacao = time.monotonic() + (
            self.configuracoes.publicacao_atraso_inicial_segundos
        )

        while True:
            expiradas = self.fila.expirar_antigos(self.configuracoes.fila_idade_maxima_minutos)

            if expiradas:
                logger.info(
                    "Ofertas expiradas removidas da fila: %s",
                    expiradas,
                )

            item_forcado = self.fila.consumir_publicacao_imediata()

            if item_forcado is not None:
                resultado_forcado = await self._publicar_item(
                    item=item_forcado,
                    prioridade_editorial=(item_forcado.prioridade),
                    motivos=["Acao administrativa: " "publicar agora"],
                    forcar=True,
                )

                if resultado_forcado == "publicado":
                    intervalo = self.cadencia.proximo_intervalo(
                        item_forcado.oferta.tipo_oportunidade
                    )

                    proxima_publicacao = time.monotonic() + intervalo

                    logger.info(
                        (
                            "Proxima publicacao podera ocorrer "
                            "em aproximadamente %.1f segundo(s)."
                        ),
                        intervalo,
                    )
                else:
                    proxima_publicacao = time.monotonic() + 60.0

                continue

            agora_monotonic = time.monotonic()

            if agora_monotonic < proxima_publicacao:
                await asyncio.sleep(
                    min(
                        self.configuracoes.publicador_intervalo_verificacao_segundos,
                        proxima_publicacao - agora_monotonic,
                    )
                )
                continue

            pendentes = self.fila.listar_pendentes(limite=self.configuracoes.tamanho_maximo_fila)

            if not pendentes:
                await asyncio.sleep(self.configuracoes.publicador_intervalo_verificacao_segundos)
                continue

            historico = self.fila.historico_publicacoes_recentes(
                minutos=max(
                    self.configuracoes.cooldown_canonico_minutos,
                    self.configuracoes.cooldown_familia_minutos,
                    self.configuracoes.cooldown_categoria_minutos,
                    self.configuracoes.cooldown_marca_minutos,
                )
            )

            resumo_familias = self.fila.resumo_familias_pendentes()

            logger.info(
                (
                    "Snapshot editorial da fila: %s item(ns) pendente(s), "
                    "%s família(s) semântica(s), %s item(ns) com família."
                ),
                resumo_familias["itens"],
                resumo_familias["familias"],
                resumo_familias["itens_com_familia"],
            )

            escolha = self.seletor.escolher(
                pendentes=pendentes,
                historico_publicacoes=historico,
                agora=datetime.now().astimezone(),
            )

            if escolha is None:
                logger.info(
                    "Nenhum item liberado para publicação agora. "
                    "Cooldowns editoriais/anti-repost podem estar segurando a fila."
                )
                await asyncio.sleep(self.configuracoes.publicador_intervalo_verificacao_segundos)
                continue

            item = escolha.item

            resultado_publicacao = await self._publicar_item(
                item=item,
                prioridade_editorial=(escolha.prioridade_editorial),
                motivos=escolha.motivos,
            )

            if resultado_publicacao != "publicado":
                proxima_publicacao = time.monotonic() + 60.0
                continue

            intervalo = self.cadencia.proximo_intervalo(item.oferta.tipo_oportunidade)

            proxima_publicacao = time.monotonic() + intervalo

            logger.info(
                "Próxima publicação poderá ocorrer em aproximadamente %.1f segundo(s).",
                intervalo,
            )


async def main() -> None:
    configuracoes = Configuracoes()
    publicador = PublicadorFila(configuracoes)
    await publicador.executar()


if __name__ == "__main__":
    asyncio.run(main())
