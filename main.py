# 63.8738, -149.7525

import asyncio
import logging

from affiliates.registro_afiliadores import criar_gerador_link_afiliado
from bots.telegram_bot import TelegramBot
from config.configuracoes import Configuracoes
from config.logging_config import configurar_logging
from filters.oferta_filter import OfertaFilter
from repositories.historico_precos_repository import HistoricoPrecosRepository
from repositories.publicados_repository import PublicadosRepository
from repositories.relatorios_repository import RelatoriosRepository
from scrapers.registro_scrapers import criar_scrapers
from services.classificador_produto import ClassificadorProduto
from services.coletor_ofertas import ColetorOfertas
from services.detector_anomalia_preco import DetectorAnomaliaPreco
from services.executor_pipeline import ExecutorPipeline
from services.historico_precos_service import HistoricoPrecosService
from services.janela_publicacao import JanelaPublicacao
from services.pontuador_oferta import PontuadorOferta

configurar_logging()

logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        configuracoes = Configuracoes()

    except ValueError:
        logger.exception("Erro nas configurações do projeto.")

        return

    scrapers = criar_scrapers()

    classificador = ClassificadorProduto()

    coletor = ColetorOfertas(scrapers=scrapers, classificador=classificador)

    gerador_link_afiliado = criar_gerador_link_afiliado(configuracoes)

    bot = TelegramBot(
        token=configuracoes.telegram_bot_token,
        channel_id=configuracoes.channel_id,
        gerador_link_afiliado=gerador_link_afiliado,
    )

    repository = PublicadosRepository()

    relatorios_repository = RelatoriosRepository()

    historico_precos_repository = HistoricoPrecosRepository(
        caminho_arquivo=("data/historico/" "mercado_livre_precos.json")
    )

    historico_precos_service = HistoricoPrecosService(repository=(historico_precos_repository))

    filtro = OfertaFilter(
        desconto_minimo=(configuracoes.desconto_minimo),
        preco_maximo=(configuracoes.preco_maximo),
        relevancia_nicho_minima=55,
    )

    pontuador = PontuadorOferta(preco_maximo=(configuracoes.preco_maximo))

    detector_anomalia = DetectorAnomaliaPreco(
        ativa=configuracoes.detector_anomalia_ativo,
        queda_minima_anomalia=configuracoes.queda_minima_anomalia,
        queda_minima_preco_bugado=configuracoes.queda_minima_preco_bugado,
        queda_maxima_publicavel=configuracoes.queda_maxima_anomalia_publicavel,
        registros_minimos=configuracoes.registros_minimos_anomalia,
        confianca_minima_publicacao=configuracoes.confianca_minima_anomalia,
    )

    janela_publicacao = JanelaPublicacao(
        hora_inicio_madrugada=(configuracoes.hora_inicio_madrugada),
        hora_fim_madrugada=(configuracoes.hora_fim_madrugada),
        queda_minima_madrugada=(configuracoes.queda_minima_madrugada),
        pontuacao_minima_madrugada=(configuracoes.pontuacao_minima_madrugada),
        registros_minimos_madrugada=(configuracoes.registros_minimos_madrugada),
        nota_comprador_minima_madrugada=(configuracoes.nota_comprador_minima_madrugada),
        queda_minima_menor_preco_madrugada=(configuracoes.queda_minima_menor_preco_madrugada),
        queda_maxima_automatica_madrugada=(configuracoes.queda_maxima_automatica_madrugada),
        ativa=configuracoes.restricao_madrugada_ativa,
    )

    logger.info("Desconto mínimo configurado: %s%%", configuracoes.desconto_minimo)

    logger.info("Preço máximo configurado: %s", configuracoes.preco_maximo)

    logger.info("Identificador público da marca: %s", configuracoes.identificador_marca)

    logger.info("Nicho configurado: hardware, periféricos " "e produtos gamer.")

    logger.info(
        "Produtos atualmente no histórico: %s", historico_precos_repository.quantidade_produtos()
    )

    if configuracoes.restricao_madrugada_ativa:
        logger.info(
            "Madrugada relâmpago ativa das %sh às %sh: exige pelo menos %s "
            "registros, nota do comprador >= %.1f/80, pontuação >= %.1f e "
            "queda forte. Quedas acima de %.1f%% são seguradas para "
            "validação reforçada.",
            configuracoes.hora_inicio_madrugada,
            configuracoes.hora_fim_madrugada,
            configuracoes.registros_minimos_madrugada,
            configuracoes.nota_comprador_minima_madrugada,
            configuracoes.pontuacao_minima_madrugada,
            configuracoes.queda_maxima_automatica_madrugada,
        )
    else:
        logger.info("Restrição de publicação por horário desativada.")

    if configuracoes.detector_anomalia_ativo:
        logger.info(
            (
                "Detector de anomalias ativo: queda >= %.1f%% entra em revisão; "
                "possível preço bugado a partir de %.1f%%; acima de %.1f%% "
                "fica retido automaticamente."
            ),
            configuracoes.queda_minima_anomalia,
            configuracoes.queda_minima_preco_bugado,
            configuracoes.queda_maxima_anomalia_publicavel,
        )
    else:
        logger.info("Detector de anomalias de preço desativado.")

    pipeline = ExecutorPipeline(
        coletor=coletor,
        bot=bot,
        repository=repository,
        relatorios_repository=(relatorios_repository),
        historico_precos_service=(historico_precos_service),
        filtro=filtro,
        pontuador=pontuador,
        quantidade_scrapers=len(scrapers),
        limite_ofertas=(configuracoes.limite_ofertas),
        maximo_publicacoes=(configuracoes.maximo_publicacoes),
        intervalo_publicacoes=(configuracoes.intervalo_publicacoes),
        janela_publicacao=janela_publicacao,
        detector_anomalia=detector_anomalia,
    )

    await pipeline.executar()


if __name__ == "__main__":
    asyncio.run(main())
