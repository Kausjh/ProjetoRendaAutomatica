# 63.8738, -149.7525

import asyncio
import logging

from config.configuracoes import Configuracoes
from config.logging_config import configurar_logging
from filters.oferta_filter import OfertaFilter
from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from repositories.historico_precos_repository import HistoricoPrecosRepository
from repositories.publicados_repository import PublicadosRepository
from repositories.relatorios_repository import RelatoriosRepository
from scrapers.registro_scrapers import criar_scrapers
from services.classificador_produto import ClassificadorProduto
from services.coletor_ofertas import ColetorOfertas
from services.curadoria_publicacao import CuradoriaPublicacao
from services.detector_anomalia_preco import DetectorAnomaliaPreco
from services.executor_pipeline import ExecutorPipeline
from services.historico_precos_service import HistoricoPrecosService
from services.janela_publicacao import JanelaPublicacao
from services.normalizador_produto import NormalizadorProduto
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

    repository = PublicadosRepository()

    fila_publicacao_repository = FilaPublicacaoRepository()

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

    normalizador_produto = NormalizadorProduto()

    curadoria_publicacao = CuradoriaPublicacao(
        nota_minima=configuracoes.nota_minima_curadoria,
        ativa=configuracoes.curadoria_publicacao_ativa,
    )

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

    if configuracoes.curadoria_publicacao_ativa:
        logger.info(
            "Curadoria de publicação v2 ativa: nota mínima %.1f/100.",
            configuracoes.nota_minima_curadoria,
        )
    else:
        logger.info("Curadoria de publicação v2 desativada.")

    if configuracoes.deduplicacao_canonica_ativa:
        logger.info(
            "Deduplicação canônica ativa a partir de %.1f/100 de confiança.",
            configuracoes.confianca_minima_deduplicacao,
        )

    logger.info(
        (
            "Fila inteligente ativa: score mínimo %.1f, até %s entradas novas "
            "por ciclo, máximo de %s pendentes."
        ),
        configuracoes.pontuacao_minima_fila,
        configuracoes.maximo_entradas_fila_por_ciclo,
        configuracoes.tamanho_maximo_fila,
    )

    pipeline = ExecutorPipeline(
        coletor=coletor,
        repository=repository,
        fila_publicacao_repository=fila_publicacao_repository,
        relatorios_repository=(relatorios_repository),
        historico_precos_service=(historico_precos_service),
        filtro=filtro,
        pontuador=pontuador,
        quantidade_scrapers=len(scrapers),
        limite_ofertas=(configuracoes.limite_ofertas),
        maximo_entradas_fila_por_ciclo=(configuracoes.maximo_entradas_fila_por_ciclo),
        pontuacao_minima_fila=configuracoes.pontuacao_minima_fila,
        tamanho_maximo_fila=configuracoes.tamanho_maximo_fila,
        fila_idade_maxima_minutos=configuracoes.fila_idade_maxima_minutos,
        maximo_entradas_por_categoria_ciclo=(configuracoes.maximo_entradas_por_categoria_ciclo),
        janela_publicacao=janela_publicacao,
        detector_anomalia=detector_anomalia,
        normalizador_produto=normalizador_produto,
        curadoria_publicacao=curadoria_publicacao,
        deduplicacao_canonica_ativa=configuracoes.deduplicacao_canonica_ativa,
        confianca_minima_deduplicacao=(configuracoes.confianca_minima_deduplicacao),
    )

    await pipeline.executar()


if __name__ == "__main__":
    asyncio.run(main())
