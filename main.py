# 63.8738, -149.7525

import asyncio
import logging
from dataclasses import asdict

from config.configuracoes import Configuracoes
from config.hunter_budget_config import carregar_limites_hunter_por_fonte
from config.logging_config import configurar_logging
from filters.oferta_filter import OfertaFilter
from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from repositories.historico_precos_efetivos_repository import (
    HistoricoPrecosEfetivosRepository,
)
from repositories.historico_precos_repository import HistoricoPrecosRepository
from repositories.publicados_repository import PublicadosRepository
from repositories.relatorios_repository import RelatoriosRepository
from scrapers.registro_scrapers import criar_scrapers
from services.classificador_produto_assistido_ai import ClassificadorProdutoAssistidoAI
from services.coletor_ofertas import ColetorOfertas
from services.controle_operacional_ai import ControleOperacionalInteligenciaAI
from services.curadoria_publicacao import CuradoriaPublicacao
from services.curadoria_publicacao_assistida_ai import CuradoriaPublicacaoAssistidaAI
from services.detector_anomalia_preco import DetectorAnomaliaPreco
from services.executor_pipeline import ExecutorPipeline
from services.historico_precos_efetivos_service import (
    HistoricoPrecosEfetivosService,
)
from services.historico_precos_service import HistoricoPrecosService
from services.janela_publicacao import JanelaPublicacao
from services.normalizador_produto import NormalizadorProduto
from services.pontuador_oferta import PontuadorOferta
from services.provedor_http_inteligencia_ai import criar_provedor_http_inteligencia_ai
from services.scout.observabilidade_discovery_comercial_hunter import (
    criar_observabilidade_discovery_comercial_hunter,
)
from services.scout.wiring_alvos_discovery_comercial_hunter import (
    carregar_alvos_discovery_comercial_hunter,
)
from services.scout.wiring_discovery_comercial_hunter import aplicar_discovery_comercial_hunter
from services.scout.wiring_priorizacao_learning_discovery_comercial_hunter import (
    aplicar_priorizacao_learning_com_historico,
)

configurar_logging()

logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        configuracoes = Configuracoes()
        limites_hunter_por_fonte = carregar_limites_hunter_por_fonte()

        resultado_discovery_comercial = aplicar_discovery_comercial_hunter(
            limites_hunter_por_fonte,
        )

        limites_hunter_por_fonte = resultado_discovery_comercial.como_mapping()

        relatorios_repository = RelatoriosRepository()

        try:
            relatorios_learning_existentes = relatorios_repository.listar()
        except Exception as erro:
            logger.warning(
                "Commercial Discovery Learning Prioritization: "
                "falha ao ler relatorios; usando fallback. tipo=%s",
                type(erro).__name__,
            )

            relatorios_learning_existentes = []

        resultado_alvos_discovery_comercial = carregar_alvos_discovery_comercial_hunter()

        resultado_priorizacao_learning = aplicar_priorizacao_learning_com_historico(
            resultado=resultado_alvos_discovery_comercial,
            relatorios_execucao=relatorios_learning_existentes,
        )

        resultado_alvos_discovery_comercial = resultado_priorizacao_learning.resultado

    except ValueError:
        logger.exception("Erro nas configurações do projeto.")

        return

    scrapers = criar_scrapers(
        alvos_discovery_comercial=(resultado_alvos_discovery_comercial.alvos),
    )

    observabilidade_discovery_comercial_hunter = criar_observabilidade_discovery_comercial_hunter(
        resultado=resultado_alvos_discovery_comercial,
        scrapers=scrapers,
    )
    observabilidade_discovery_comercial_hunter["priorizacao_learning"] = (
        resultado_priorizacao_learning.observabilidade
    )

    controle_operacional_ai = ControleOperacionalInteligenciaAI(
        kill_switch_ativo=configuracoes.ai_kill_switch_ativo,
        limite_chamadas_externas=(configuracoes.ai_limite_chamadas_externas),
        limite_tokens_total=(configuracoes.ai_limite_tokens_total),
        limite_custo_estimado_usd=(configuracoes.ai_limite_custo_estimado_usd),
    )

    try:
        provedor_ai = criar_provedor_http_inteligencia_ai(
            endpoint=configuracoes.ai_provedor_endpoint,
            provedor=configuracoes.ai_provedor_nome,
            modelo=configuracoes.ai_provedor_modelo,
            auth_header_nome=(configuracoes.ai_provedor_auth_header_nome),
            auth_header_valor=(configuracoes.ai_provedor_auth_header_valor),
        )
    except (TypeError, ValueError):
        logger.exception("Erro na configuracao do provedor de inteligencia AI.")
        return

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=False,
        provedor=provedor_ai,
        controle_operacional=controle_operacional_ai,
    )

    coletor = ColetorOfertas(
        scrapers=scrapers,
        classificador=classificador,
        limites_hunter_por_fonte=limites_hunter_por_fonte,
    )

    repository = PublicadosRepository()

    fila_publicacao_repository = FilaPublicacaoRepository()

    controle_administrativo_repository = ControleAdministrativoRepository()

    try:
        controle_administrativo_repository.salvar_snapshot_operacional_ai(
            asdict(controle_operacional_ai.snapshot())
        )
    except Exception as erro:
        logger.warning(
            "Nao foi possivel persistir snapshot operacional AI inicial. tipo=%s",
            type(erro).__name__,
        )

    historico_precos_repository = HistoricoPrecosRepository(
        caminho_arquivo=("data/historico/" "mercado_livre_precos.json")
    )

    historico_precos_service = HistoricoPrecosService(repository=(historico_precos_repository))

    historico_precos_efetivos_repository = HistoricoPrecosEfetivosRepository(
        caminho_arquivo=("data/historico/" "precos_efetivos_confirmados.json"),
    )

    historico_precos_efetivos_service = HistoricoPrecosEfetivosService(
        repository=(historico_precos_efetivos_repository),
    )

    filtro = OfertaFilter(
        desconto_minimo=(configuracoes.desconto_minimo),
        preco_maximo=(configuracoes.preco_maximo),
        relevancia_nicho_minima=55,
    )

    pontuador = PontuadorOferta(preco_maximo=(configuracoes.preco_maximo))

    normalizador_produto = NormalizadorProduto()

    curadoria_publicacao = CuradoriaPublicacaoAssistidaAI(
        curadoria=CuradoriaPublicacao(
            nota_minima=configuracoes.nota_minima_curadoria,
            ativa=configuracoes.curadoria_publicacao_ativa,
        ),
        habilitado=False,
        provedor=provedor_ai,
        controle_operacional=controle_operacional_ai,
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

    logger.info(
        "Universo monitorado: tecnologia, setup, games, "
        "eletronicos e consumo recorrente do publico do Radar."
    )

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
            "Curadoria de publicação ativa: nota mínima %.1f/100.",
            configuracoes.nota_minima_curadoria,
        )
    else:
        logger.info("Curadoria de publicação desativada.")

    if configuracoes.deduplicacao_canonica_ativa:
        logger.info(
            "Deduplicação canônica ativa a partir de %.1f/100 de confiança.",
            configuracoes.confianca_minima_deduplicacao,
        )

    logger.info(
        (
            "Fila inteligente ativa: score principal %.1f, reposição adaptativa "
            "até %.1f quando necessário, alvo mínimo %s pendentes, até %s novas "
            "entradas por ciclo e máximo de %s pendentes."
        ),
        configuracoes.pontuacao_minima_fila,
        configuracoes.pontuacao_minima_reposicao_fila,
        configuracoes.alvo_minimo_pendentes_fila,
        configuracoes.maximo_entradas_fila_por_ciclo,
        configuracoes.tamanho_maximo_fila,
    )

    pipeline = ExecutorPipeline(
        coletor=coletor,
        repository=repository,
        fila_publicacao_repository=fila_publicacao_repository,
        relatorios_repository=(relatorios_repository),
        historico_precos_service=(historico_precos_service),
        historico_precos_efetivos_service=(historico_precos_efetivos_service),
        filtro=filtro,
        pontuador=pontuador,
        quantidade_scrapers=len(scrapers),
        limite_ofertas=(configuracoes.limite_ofertas),
        observabilidade_discovery_comercial_hunter=(observabilidade_discovery_comercial_hunter),
        maximo_entradas_fila_por_ciclo=(configuracoes.maximo_entradas_fila_por_ciclo),
        pontuacao_minima_fila=configuracoes.pontuacao_minima_fila,
        fila_reposicao_adaptativa_ativa=(configuracoes.fila_reposicao_adaptativa_ativa),
        pontuacao_minima_reposicao_fila=(configuracoes.pontuacao_minima_reposicao_fila),
        alvo_minimo_pendentes_fila=(configuracoes.alvo_minimo_pendentes_fila),
        queda_minima_republicacao_percentual=(configuracoes.queda_minima_repost_familia_percentual),
        cooldown_republicacao_sem_queda_minutos=(configuracoes.cooldown_familia_minutos),
        repositorio_admin=controle_administrativo_repository,
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

    try:
        await pipeline.executar()
    finally:
        try:
            controle_administrativo_repository.salvar_snapshot_operacional_ai(
                asdict(controle_operacional_ai.snapshot())
            )
        except Exception as erro:
            logger.warning(
                "Nao foi possivel persistir snapshot operacional AI. tipo=%s",
                type(erro).__name__,
            )


if __name__ == "__main__":
    asyncio.run(main())
