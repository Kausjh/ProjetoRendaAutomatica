# 63.8738, -149.7525

import logging
from datetime import datetime
from time import perf_counter

from filters.oferta_filter import OfertaFilter
from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from repositories.publicados_repository import PublicadosRepository
from repositories.relatorios_repository import RelatoriosRepository
from services.coletor_ofertas import ColetorOfertas
from services.curadoria_publicacao import CuradoriaPublicacao
from services.detector_anomalia_preco import DetectorAnomaliaPreco
from services.historico_precos_service import HistoricoPrecosService, ResultadoHistoricoPreco
from services.janela_publicacao import JanelaPublicacao
from services.normalizador_produto import NormalizadorProduto
from services.pontuador_oferta import PontuadorOferta

logger = logging.getLogger(__name__)


class ExecutorPipeline:
    def __init__(
        self,
        coletor: ColetorOfertas,
        repository: PublicadosRepository,
        fila_publicacao_repository: FilaPublicacaoRepository,
        relatorios_repository: RelatoriosRepository,
        historico_precos_service: HistoricoPrecosService,
        filtro: OfertaFilter,
        pontuador: PontuadorOferta,
        quantidade_scrapers: int,
        limite_ofertas: int,
        maximo_entradas_fila_por_ciclo: int = 12,
        pontuacao_minima_fila: float = 72.0,
        tamanho_maximo_fila: int = 30,
        fila_idade_maxima_minutos: float = 90.0,
        maximo_entradas_por_categoria_ciclo: int = 2,
        janela_publicacao: JanelaPublicacao | None = None,
        detector_anomalia: DetectorAnomaliaPreco | None = None,
        normalizador_produto: NormalizadorProduto | None = None,
        curadoria_publicacao: CuradoriaPublicacao | None = None,
        deduplicacao_canonica_ativa: bool = True,
        confianca_minima_deduplicacao: float = 90.0,
    ) -> None:
        self.coletor = coletor
        self.repository = repository
        self.fila_publicacao_repository = fila_publicacao_repository
        self.relatorios_repository = relatorios_repository
        self.historico_precos_service = historico_precos_service
        self.filtro = filtro
        self.pontuador = pontuador
        self.quantidade_scrapers = quantidade_scrapers
        self.limite_ofertas = limite_ofertas
        self.maximo_entradas_fila_por_ciclo = maximo_entradas_fila_por_ciclo
        self.pontuacao_minima_fila = pontuacao_minima_fila
        self.tamanho_maximo_fila = tamanho_maximo_fila
        self.fila_idade_maxima_minutos = fila_idade_maxima_minutos
        self.maximo_entradas_por_categoria_ciclo = maximo_entradas_por_categoria_ciclo

        self.janela_publicacao = janela_publicacao or JanelaPublicacao()
        self.detector_anomalia = detector_anomalia or DetectorAnomaliaPreco()
        self.normalizador_produto = normalizador_produto or NormalizadorProduto()
        self.curadoria_publicacao = curadoria_publicacao or CuradoriaPublicacao()
        self.deduplicacao_canonica_ativa = deduplicacao_canonica_ativa
        self.confianca_minima_deduplicacao = confianca_minima_deduplicacao

    async def executar(self) -> None:
        inicio_execucao = perf_counter()

        logger.info("=" * 60)

        logger.info("Iniciando nova execução do ProjetoRendaAutomatica.")

        logger.info("Quantidade de scrapers configurados: %s", self.quantidade_scrapers)

        logger.info("Limite de ofertas por scraper: %s", self.limite_ofertas)

        logger.info(
            "Score mínimo para entrar na fila: %.1f",
            self.pontuacao_minima_fila,
        )

        logger.info(
            "Máximo de novas entradas na fila por ciclo: %s",
            self.maximo_entradas_fila_por_ciclo,
        )

        logger.info(
            "Máximo de entradas da mesma categoria por ciclo: %s",
            self.maximo_entradas_por_categoria_ciclo,
        )

        try:
            ofertas = self.coletor.buscar_ofertas(limite_por_scraper=self.limite_ofertas)

        except Exception:
            logger.exception("Erro ao buscar ofertas.")

            return

        logger.info("Quantidade total de ofertas encontradas: %s", len(ofertas))

        quantidade_enfileirada = 0
        quantidade_atualizada_na_fila = 0
        quantidade_descartada_score_fila = 0
        quantidade_filtrada = 0
        quantidade_aprovada_pelo_filtro = 0
        quantidade_ignorada = 0
        quantidade_com_erro = 0
        quantidade_precos_registrados = 0
        quantidade_quedas_detectadas = 0
        quantidade_menores_precos = 0
        quantidade_anomalias_detectadas = 0
        quantidade_anomalias_publicaveis = 0
        quantidade_anomalias_retidas = 0
        quantidade_rejeitada_curadoria = 0
        quantidade_deduplicada_canonica = 0

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

            resultado_normalizacao = self.normalizador_produto.normalizar(oferta)

            logger.debug(
                "Produto normalizado: %s -> %s | confiança=%.1f",
                oferta.nome,
                resultado_normalizacao.nome_canonico,
                resultado_normalizacao.confianca,
            )

            resultado_curadoria = self.curadoria_publicacao.analisar(oferta)

            if not resultado_curadoria.publicavel:
                quantidade_rejeitada_curadoria += 1

                detalhes = list(resultado_curadoria.bloqueios) or list(resultado_curadoria.motivos)

                logger.info(
                    "Oferta rejeitada pela curadoria: %s | nota=%.1f | %s",
                    oferta.nome,
                    resultado_curadoria.nota,
                    " | ".join(detalhes),
                )
                continue

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

        if self.deduplicacao_canonica_ativa:
            ofertas_aprovadas, quantidade_deduplicada_canonica = self._deduplicar_ofertas_canonicas(
                ofertas_aprovadas
            )

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

        candidatos_fila = [
            item
            for item in ofertas_publicaveis
            if item[1] >= self.pontuacao_minima_fila
            or item[0].tipo_oportunidade in {"possivel_preco_bugado", "anomalia_forte"}
        ]

        quantidade_descartada_score_fila = len(ofertas_publicaveis) - len(candidatos_fila)

        candidatos_fila.sort(
            key=lambda item: (
                1 if item[0].tipo_oportunidade == "possivel_preco_bugado" else 0,
                1 if item[0].tipo_oportunidade == "anomalia_forte" else 0,
                item[1],
            ),
            reverse=True,
        )

        quantidade_candidatos_antes_diversidade = len(candidatos_fila)

        candidatos_fila = self._selecionar_candidatos_diversos(
            candidatos=candidatos_fila,
            limite_total=self.maximo_entradas_fila_por_ciclo,
            limite_por_categoria=self.maximo_entradas_por_categoria_ciclo,
        )

        quantidade_limitada_por_diversidade = quantidade_candidatos_antes_diversidade - len(
            candidatos_fila
        )

        if quantidade_limitada_por_diversidade > 0:
            logger.info(
                (
                    "Diversidade de entrada segurou %s candidato(s); "
                    "limite de %s por categoria neste ciclo."
                ),
                quantidade_limitada_por_diversidade,
                self.maximo_entradas_por_categoria_ciclo,
            )

        expiradas = self.fila_publicacao_repository.expirar_antigos(self.fila_idade_maxima_minutos)

        if expiradas:
            logger.info("Itens antigos expirados da fila: %s", expiradas)

        for (
            oferta,
            pontuacao,
            resultado_historico,
            deve_republicar_por_queda,
        ) in candidatos_fila:
            prioridade = self._calcular_prioridade_fila(
                oferta=oferta,
                pontuacao=pontuacao,
                deve_republicar_por_queda=deve_republicar_por_queda,
            )

            resultado_fila = self.fila_publicacao_repository.adicionar_ou_atualizar(
                oferta=oferta,
                resultado_historico=resultado_historico,
                pontuacao=pontuacao,
                deve_republicar_por_queda=deve_republicar_por_queda,
                prioridade=prioridade,
            )

            if resultado_fila in {"adicionado", "substituido_canonico"}:
                quantidade_enfileirada += 1
            elif resultado_fila == "atualizado":
                quantidade_atualizada_na_fila += 1

            logger.info(
                ("Fila: %s | %s | score=%.2f | prioridade=%.2f | " "categoria=%s | marca=%s"),
                resultado_fila,
                oferta.nome,
                pontuacao,
                prioridade,
                oferta.categoria or "sem categoria",
                oferta.marca or "sem marca",
            )

        removidos_por_limite = self.fila_publicacao_repository.reduzir_fila(
            self.tamanho_maximo_fila
        )

        if removidos_por_limite:
            logger.info(
                "Itens de menor prioridade removidos por limite da fila: %s",
                removidos_por_limite,
            )

        quantidade_pendente_fila = self.fila_publicacao_repository.quantidade_pendente()

        quantidade_nao_enfileirada = max(
            0,
            len(ofertas_publicaveis) - len(candidatos_fila),
        )

        logger.info("Ofertas aprovadas pelo filtro: %s", quantidade_aprovada_pelo_filtro)

        logger.info("Ofertas elegíveis para publicação: %s", len(ofertas_aprovadas))

        logger.info(
            "Ofertas que passaram também pela janela de horário: %s",
            len(ofertas_publicaveis),
        )

        logger.info("Ofertas adicionadas/renovadas na fila: %s", quantidade_enfileirada)

        logger.info("Ofertas atualizadas na fila: %s", quantidade_atualizada_na_fila)

        logger.info(
            "Ofertas fora da fila por score/capacidade do ciclo: %s",
            quantidade_nao_enfileirada,
        )

        logger.info("Fila pendente após o ciclo: %s", quantidade_pendente_fila)

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

        logger.info("Ofertas enfileiradas neste ciclo: %s", quantidade_enfileirada)

        logger.info(
            "Ofertas atualizadas na fila neste ciclo: %s",
            quantidade_atualizada_na_fila,
        )

        logger.info(
            "Ofertas abaixo do score mínimo da fila: %s",
            quantidade_descartada_score_fila,
        )

        logger.info("Fila pendente ao fim do ciclo: %s", quantidade_pendente_fila)

        logger.info(
            "Candidatos segurados pela diversidade de entrada: %s",
            quantidade_limitada_por_diversidade,
        )

        logger.info("Ofertas rejeitadas pelo filtro: %s", quantidade_filtrada)

        logger.info(
            "Ofertas rejeitadas pela curadoria: %s",
            quantidade_rejeitada_curadoria,
        )

        logger.info(
            "Anúncios redundantes removidos por produto canônico: %s",
            quantidade_deduplicada_canonica,
        )

        logger.info("Ofertas já publicadas e sem nova queda: %s", quantidade_ignorada)

        logger.info("Novos preços registrados: %s", quantidade_precos_registrados)

        logger.info("Quedas de preço detectadas: %s", quantidade_quedas_detectadas)

        logger.info("Novos menores preços históricos: %s", quantidade_menores_precos)

        logger.info("Anomalias de preço detectadas: %s", quantidade_anomalias_detectadas)

        logger.info("Anomalias liberadas para publicação: %s", quantidade_anomalias_publicaveis)

        logger.info("Anomalias retidas por segurança: %s", quantidade_anomalias_retidas)

        logger.info("Ofertas com erro: %s", quantidade_com_erro)

        logger.info("Tempo total da execução: %.2f segundo(s)", tempo_total)

        relatorio = {
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scrapers_executados": self.quantidade_scrapers,
            "ofertas_coletadas": len(ofertas),
            "ofertas_aprovadas_pelo_filtro": (quantidade_aprovada_pelo_filtro),
            "taxa_aprovacao_filtro": round(taxa_aprovacao_filtro, 2),
            "ofertas_elegiveis": len(ofertas_aprovadas),
            "ofertas_enfileiradas": quantidade_enfileirada,
            "ofertas_atualizadas_na_fila": quantidade_atualizada_na_fila,
            "ofertas_abaixo_score_fila": quantidade_descartada_score_fila,
            "fila_pendente_ao_fim": quantidade_pendente_fila,
            "candidatos_segurados_diversidade_entrada": (quantidade_limitada_por_diversidade),
            # Compatibilidade temporária com consumidores antigos do relatório.
            "ofertas_selecionadas": quantidade_enfileirada,
            "ofertas_publicadas": 0,
            "ofertas_elegiveis_nao_selecionadas": quantidade_nao_enfileirada,
            "ofertas_rejeitadas": quantidade_filtrada,
            "ofertas_rejeitadas_curadoria_v2": quantidade_rejeitada_curadoria,
            "anuncios_redundantes_removidos": quantidade_deduplicada_canonica,
            "ofertas_ja_publicadas_sem_nova_queda": (quantidade_ignorada),
            "novos_precos_registrados": (quantidade_precos_registrados),
            "quedas_preco_detectadas": (quantidade_quedas_detectadas),
            "novos_menores_precos_historicos": (quantidade_menores_precos),
            "anomalias_preco_detectadas": quantidade_anomalias_detectadas,
            "anomalias_preco_publicaveis": quantidade_anomalias_publicaveis,
            "anomalias_preco_retidas": quantidade_anomalias_retidas,
            "ofertas_com_erro": quantidade_com_erro,
            "tempo_total_segundos": round(tempo_total, 2),
        }

        self.relatorios_repository.salvar(relatorio)

        logger.info("Execução finalizada.")

        logger.info("=" * 60)

    @staticmethod
    def _selecionar_candidatos_diversos(
        candidatos: list,
        limite_total: int,
        limite_por_categoria: int,
    ) -> list:
        """Seleciona em rodadas para não deixar uma categoria dominar a fila.

        Exemplo: em vez de pegar os 6 melhores monitores antes de qualquer
        SSD/placa de vídeo, faz uma primeira rodada com 1 por categoria e só
        depois permite a segunda vaga de cada categoria.

        Oportunidades urgentes validadas entram primeiro e não são descartadas
        por esse balanceamento.
        """

        if limite_total <= 0 or not candidatos:
            return []

        urgentes = [
            item
            for item in candidatos
            if item[0].tipo_oportunidade in {"possivel_preco_bugado", "anomalia_forte"}
        ]

        comuns = [
            item
            for item in candidatos
            if item[0].tipo_oportunidade not in {"possivel_preco_bugado", "anomalia_forte"}
        ]

        selecionados: list = []
        ids_selecionados: set[int] = set()
        contagem_categoria: dict[str, int] = {}

        for item in urgentes:
            if len(selecionados) >= limite_total:
                return selecionados

            selecionados.append(item)
            ids_selecionados.add(id(item))

            categoria = ExecutorPipeline._chave_categoria(item[0].categoria)
            contagem_categoria[categoria] = contagem_categoria.get(categoria, 0) + 1

        # Rodadas: primeiro 1 de cada categoria, depois a segunda vaga etc.
        for rodada in range(1, limite_por_categoria + 1):
            for item in comuns:
                if len(selecionados) >= limite_total:
                    return selecionados

                if id(item) in ids_selecionados:
                    continue

                categoria = ExecutorPipeline._chave_categoria(item[0].categoria)

                if contagem_categoria.get(categoria, 0) >= rodada:
                    continue

                selecionados.append(item)
                ids_selecionados.add(id(item))
                contagem_categoria[categoria] = contagem_categoria.get(categoria, 0) + 1

        return selecionados

    @staticmethod
    def _chave_categoria(categoria: str | None) -> str:
        if not categoria:
            return "sem_categoria"

        return categoria.strip().casefold()

    @staticmethod
    def _calcular_prioridade_fila(
        oferta,
        pontuacao: float,
        deve_republicar_por_queda: bool,
    ) -> float:
        prioridade = float(pontuacao)

        if oferta.tipo_oportunidade == "possivel_preco_bugado":
            prioridade += 60.0
        elif oferta.tipo_oportunidade == "anomalia_forte":
            prioridade += 40.0

        if deve_republicar_por_queda:
            prioridade += 8.0

        if oferta.nota_curadoria:
            prioridade += min(10.0, oferta.nota_curadoria / 10.0)

        return round(prioridade, 2)

    def _deduplicar_ofertas_canonicas(self, ofertas_aprovadas: list) -> tuple[list, int]:
        """Mantém um representante por modelo quando a identidade é confiável.

        Não deduplica chaves de baixa confiança para evitar unir produtos
        diferentes só porque os títulos são parecidos.
        """

        selecionadas: list = []
        indice_por_chave: dict[str, int] = {}
        removidas = 0

        for item in ofertas_aprovadas:
            oferta, pontuacao, _, _ = item

            chave = oferta.chave_produto_canonica

            if not chave or oferta.confianca_normalizacao < self.confianca_minima_deduplicacao:
                selecionadas.append(item)
                continue

            indice_existente = indice_por_chave.get(chave)

            if indice_existente is None:
                indice_por_chave[chave] = len(selecionadas)
                selecionadas.append(item)
                continue

            item_existente = selecionadas[indice_existente]
            oferta_existente, pontuacao_existente, _, _ = item_existente

            if self._nova_oferta_e_melhor_representante(
                oferta_nova=oferta,
                pontuacao_nova=pontuacao,
                oferta_atual=oferta_existente,
                pontuacao_atual=pontuacao_existente,
            ):
                logger.info(
                    ("Deduplicação canônica: trocando representante de %s | " "%s %.2f -> %s %.2f"),
                    oferta.produto_canonico,
                    oferta_existente.moeda,
                    oferta_existente.preco,
                    oferta.moeda,
                    oferta.preco,
                )
                selecionadas[indice_existente] = item
            else:
                logger.info(
                    "Deduplicação canônica: anúncio redundante removido: %s | %s",
                    oferta.nome,
                    oferta.produto_canonico,
                )

            removidas += 1

        return selecionadas, removidas

    @staticmethod
    def _nova_oferta_e_melhor_representante(
        oferta_nova,
        pontuacao_nova: float,
        oferta_atual,
        pontuacao_atual: float,
    ) -> bool:
        prioridade_nova = (
            1 if oferta_nova.anomalia_publicavel else 0,
            -oferta_nova.preco,
            pontuacao_nova,
        )
        prioridade_atual = (
            1 if oferta_atual.anomalia_publicavel else 0,
            -oferta_atual.preco,
            pontuacao_atual,
        )

        return prioridade_nova > prioridade_atual
