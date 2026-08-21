# 63.8738, -149.7525

import asyncio
import logging
from datetime import datetime
from time import perf_counter

from bots.telegram_bot import TelegramBot
from filters.oferta_filter import OfertaFilter
from repositories.publicados_repository import PublicadosRepository
from repositories.relatorios_repository import RelatoriosRepository
from services.coletor_ofertas import ColetorOfertas
from services.detector_anomalia_preco import DetectorAnomaliaPreco
from services.historico_precos_service import HistoricoPrecosService, ResultadoHistoricoPreco
from services.janela_publicacao import JanelaPublicacao
from services.pontuador_oferta import PontuadorOferta

logger = logging.getLogger(__name__)


class ExecutorPipeline:
    def __init__(
        self,
        coletor: ColetorOfertas,
        bot: TelegramBot,
        repository: PublicadosRepository,
        relatorios_repository: RelatoriosRepository,
        historico_precos_service: HistoricoPrecosService,
        filtro: OfertaFilter,
        pontuador: PontuadorOferta,
        quantidade_scrapers: int,
        limite_ofertas: int,
        maximo_publicacoes: int,
        intervalo_publicacoes: int | float,
        janela_publicacao: JanelaPublicacao | None = None,
        detector_anomalia: DetectorAnomaliaPreco | None = None,
    ) -> None:
        self.coletor = coletor
        self.bot = bot
        self.repository = repository
        self.relatorios_repository = relatorios_repository
        self.historico_precos_service = historico_precos_service
        self.filtro = filtro
        self.pontuador = pontuador
        self.quantidade_scrapers = quantidade_scrapers
        self.limite_ofertas = limite_ofertas
        self.maximo_publicacoes = maximo_publicacoes
        self.intervalo_publicacoes = intervalo_publicacoes

        self.janela_publicacao = janela_publicacao or JanelaPublicacao()
        self.detector_anomalia = detector_anomalia or DetectorAnomaliaPreco()

    async def executar(self) -> None:
        inicio_execucao = perf_counter()

        logger.info("=" * 60)

        logger.info("Iniciando nova execução do ProjetoRendaAutomatica.")

        logger.info("Quantidade de scrapers configurados: %s", self.quantidade_scrapers)

        logger.info("Limite de ofertas por scraper: %s", self.limite_ofertas)

        logger.info("Máximo de publicações por execução: %s", self.maximo_publicacoes)

        logger.info("Intervalo entre publicações: %s segundo(s)", self.intervalo_publicacoes)

        try:
            ofertas = self.coletor.buscar_ofertas(limite_por_scraper=self.limite_ofertas)

        except Exception:
            logger.exception("Erro ao buscar ofertas.")

            return

        logger.info("Quantidade total de ofertas encontradas: %s", len(ofertas))

        quantidade_publicada = 0
        quantidade_filtrada = 0
        quantidade_aprovada_pelo_filtro = 0
        quantidade_ignorada = 0
        quantidade_com_erro = 0
        quantidade_precos_registrados = 0
        quantidade_quedas_detectadas = 0
        quantidade_menores_precos = 0
        quantidade_republicada_por_queda = 0
        quantidade_anomalias_detectadas = 0
        quantidade_anomalias_publicaveis = 0
        quantidade_anomalias_retidas = 0

        quantidade_links_processados = 0
        quantidade_links_transformados = 0
        quantidade_links_mantidos = 0

        afiliadores_utilizados: dict[str, int] = {}

        ofertas_aprovadas = []

        for oferta in ofertas:
            resultado_historico: ResultadoHistoricoPreco | None = None

            try:
                resultado_historico = self.historico_precos_service.analisar_e_registrar(oferta)

                if resultado_historico.novo_preco_registrado:
                    quantidade_precos_registrados += 1

                if resultado_historico.preco_caiu:
                    quantidade_quedas_detectadas += 1

                    logger.info(
                        ("Queda de preço detectada: %s | " "%s %.2f → %s %.2f | %.2f%%"),
                        oferta.nome,
                        oferta.moeda,
                        resultado_historico.preco_anterior,
                        oferta.moeda,
                        oferta.preco,
                        resultado_historico.variacao_percentual,
                    )

                if (
                    not resultado_historico.primeiro_registro
                    and resultado_historico.menor_preco_historico
                ):
                    quantidade_menores_precos += 1

                    logger.info(
                        "Novo menor preço histórico: %s | %s %.2f",
                        oferta.nome,
                        oferta.moeda,
                        oferta.preco,
                    )

            except Exception:
                logger.exception("Erro ao analisar o histórico de preço de '%s'.", oferta.nome)

                quantidade_com_erro += 1

            resultado_filtro = self.filtro.analisar(oferta)

            if not resultado_filtro.aprovada:
                logger.info(
                    "Oferta rejeitada: %s | Motivo: %s", oferta.nome, resultado_filtro.motivo
                )

                quantidade_filtrada += 1
                continue

            quantidade_aprovada_pelo_filtro += 1

            oferta_ja_publicada = self.repository.ja_foi_publicada(oferta.link)

            deve_republicar_por_queda = (
                oferta_ja_publicada
                and resultado_historico is not None
                and resultado_historico.preco_caiu
            )

            if oferta_ja_publicada and not deve_republicar_por_queda:
                logger.info("Ignorando oferta já publicada: %s", oferta.nome)

                quantidade_ignorada += 1
                continue

            if deve_republicar_por_queda:
                logger.info(
                    (
                        "Oferta já publicada está elegível para "
                        "republicação porque o preço caiu: %s"
                    ),
                    oferta.nome,
                )

            pontuacao = self.pontuador.calcular(
                oferta=oferta, resultado_historico=resultado_historico
            )

            resultado_anomalia = self.detector_anomalia.avaliar(
                oferta=oferta,
                resultado_historico=resultado_historico,
            )

            if resultado_anomalia.detectada:
                quantidade_anomalias_detectadas += 1

                logger.warning(
                    (
                        "Anomalia de preço detectada: %s | tipo=%s | "
                        "queda=%.1f%% | confiança=%.0f/100 | publicável=%s"
                    ),
                    oferta.nome,
                    resultado_anomalia.tipo,
                    resultado_anomalia.queda_percentual,
                    resultado_anomalia.confianca,
                    resultado_anomalia.publicavel,
                )

                if not resultado_anomalia.publicavel:
                    quantidade_anomalias_retidas += 1

                    logger.warning(
                        "Anomalia retida para não publicar automaticamente: %s | %s",
                        oferta.nome,
                        " | ".join(resultado_anomalia.motivos),
                    )
                    continue

                quantidade_anomalias_publicaveis += 1

            ofertas_aprovadas.append(
                (oferta, pontuacao, resultado_historico, deve_republicar_por_queda)
            )

            logger.info("Oferta elegível: %s | Pontuação final: %.2f", oferta.nome, pontuacao)

        ofertas_aprovadas.sort(
            key=lambda item: (
                1 if item[0].tipo_oportunidade == "possivel_preco_bugado" else 0,
                1 if item[0].tipo_oportunidade == "anomalia_forte" else 0,
                item[1],
            ),
            reverse=True,
        )

        ofertas_publicaveis = []
        quantidade_adiada_por_horario = 0

        for item in ofertas_aprovadas:
            oferta_avaliada, pontuacao_avaliada, historico_avaliado, _ = item

            resultado_janela = self.janela_publicacao.avaliar(
                oferta=oferta_avaliada,
                pontuacao=pontuacao_avaliada,
                resultado_historico=historico_avaliado,
            )

            if resultado_janela.pode_publicar:
                ofertas_publicaveis.append(item)
                continue

            quantidade_adiada_por_horario += 1

            logger.info(
                "Oferta adiada por horário: %s | Motivo: %s",
                oferta_avaliada.nome,
                resultado_janela.motivo,
            )

        if quantidade_adiada_por_horario > 0:
            logger.info(
                "Ofertas adiadas para o horário de maior audiência: %s",
                quantidade_adiada_por_horario,
            )

        ofertas_selecionadas = ofertas_publicaveis[: self.maximo_publicacoes]

        quantidade_nao_selecionada = len(ofertas_publicaveis) - len(ofertas_selecionadas)

        logger.info("Ofertas aprovadas pelo filtro: %s", quantidade_aprovada_pelo_filtro)

        logger.info("Ofertas elegíveis para publicação: %s", len(ofertas_aprovadas))

        logger.info("Ofertas selecionadas para publicação: %s", len(ofertas_selecionadas))

        if quantidade_nao_selecionada > 0:
            logger.info(
                "Ofertas elegíveis deixadas para outra execução: %s", quantidade_nao_selecionada
            )

        for (
            oferta,
            pontuacao,
            resultado_historico,
            deve_republicar_por_queda,
        ) in ofertas_selecionadas:
            logger.info("Publicando: %s | Pontuação final: %.2f", oferta.nome, pontuacao)

            try:
                resultado_link = await self.bot.enviar_oferta(
                    oferta=oferta, resultado_historico=resultado_historico
                )

                self.repository.marcar_como_publicada(oferta.link)

                quantidade_publicada += 1
                quantidade_links_processados += 1

                if resultado_link.foi_transformado:
                    quantidade_links_transformados += 1

                else:
                    quantidade_links_mantidos += 1

                nome_afiliador = resultado_link.afiliador_utilizado

                afiliadores_utilizados[nome_afiliador] = (
                    afiliadores_utilizados.get(nome_afiliador, 0) + 1
                )

                if deve_republicar_por_queda:
                    quantidade_republicada_por_queda += 1

                    logger.info("Oferta republicada por queda de preço: %s", oferta.nome)

            except Exception:
                logger.exception("Erro ao publicar '%s'.", oferta.nome)

                quantidade_com_erro += 1
                continue

            await asyncio.sleep(self.intervalo_publicacoes)

        taxa_aprovacao_filtro = (
            quantidade_aprovada_pelo_filtro / len(ofertas) * 100 if ofertas else 0.0
        )

        tempo_total = perf_counter() - inicio_execucao

        logger.info("Resumo da execução:")

        logger.info("Scrapers executados: %s", self.quantidade_scrapers)

        logger.info("Ofertas coletadas: %s", len(ofertas))

        logger.info("Ofertas aprovadas pelo filtro: %s", quantidade_aprovada_pelo_filtro)

        logger.info("Taxa de aprovação do filtro: %.2f%%", taxa_aprovacao_filtro)

        logger.info("Ofertas elegíveis para publicação: %s", len(ofertas_aprovadas))

        logger.info("Ofertas selecionadas: %s", len(ofertas_selecionadas))

        logger.info("Ofertas publicadas: %s", quantidade_publicada)

        logger.info("Ofertas republicadas por queda de preço: %s", quantidade_republicada_por_queda)

        logger.info("Ofertas elegíveis não selecionadas: %s", quantidade_nao_selecionada)

        logger.info("Ofertas rejeitadas pelo filtro: %s", quantidade_filtrada)

        logger.info("Ofertas já publicadas e sem nova queda: %s", quantidade_ignorada)

        logger.info("Novos preços registrados: %s", quantidade_precos_registrados)

        logger.info("Quedas de preço detectadas: %s", quantidade_quedas_detectadas)

        logger.info("Novos menores preços históricos: %s", quantidade_menores_precos)

        logger.info("Anomalias de preço detectadas: %s", quantidade_anomalias_detectadas)

        logger.info("Anomalias liberadas para publicação: %s", quantidade_anomalias_publicaveis)

        logger.info("Anomalias retidas por segurança: %s", quantidade_anomalias_retidas)

        logger.info("Links de publicação processados: %s", quantidade_links_processados)

        logger.info("Links transformados: %s", quantidade_links_transformados)

        logger.info("Links mantidos sem alteração: %s", quantidade_links_mantidos)

        if afiliadores_utilizados:
            logger.info("Afiliadores utilizados:")

            for nome_afiliador, quantidade in afiliadores_utilizados.items():
                logger.info("- %s: %s", nome_afiliador, quantidade)

        logger.info("Ofertas com erro: %s", quantidade_com_erro)

        logger.info("Tempo total da execução: %.2f segundo(s)", tempo_total)

        relatorio = {
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scrapers_executados": self.quantidade_scrapers,
            "ofertas_coletadas": len(ofertas),
            "ofertas_aprovadas_pelo_filtro": (quantidade_aprovada_pelo_filtro),
            "taxa_aprovacao_filtro": round(taxa_aprovacao_filtro, 2),
            "ofertas_elegiveis": len(ofertas_aprovadas),
            "ofertas_selecionadas": len(ofertas_selecionadas),
            "ofertas_publicadas": quantidade_publicada,
            "ofertas_republicadas_por_queda": (quantidade_republicada_por_queda),
            "ofertas_elegiveis_nao_selecionadas": (quantidade_nao_selecionada),
            "ofertas_rejeitadas": quantidade_filtrada,
            "ofertas_ja_publicadas_sem_nova_queda": (quantidade_ignorada),
            "novos_precos_registrados": (quantidade_precos_registrados),
            "quedas_preco_detectadas": (quantidade_quedas_detectadas),
            "novos_menores_precos_historicos": (quantidade_menores_precos),
            "anomalias_preco_detectadas": quantidade_anomalias_detectadas,
            "anomalias_preco_publicaveis": quantidade_anomalias_publicaveis,
            "anomalias_preco_retidas": quantidade_anomalias_retidas,
            "links_processados": quantidade_links_processados,
            "links_transformados": quantidade_links_transformados,
            "links_mantidos_sem_alteracao": (quantidade_links_mantidos),
            "afiliadores_utilizados": afiliadores_utilizados,
            "ofertas_com_erro": quantidade_com_erro,
            "tempo_total_segundos": round(tempo_total, 2),
        }

        self.relatorios_repository.salvar(relatorio)

        logger.info("Execução finalizada.")

        logger.info("=" * 60)
