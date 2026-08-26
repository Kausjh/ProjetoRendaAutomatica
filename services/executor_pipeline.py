# 63.8738, -149.7525

import logging
from datetime import datetime
from time import perf_counter

from filters.oferta_filter import OfertaFilter
from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
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
        fila_reposicao_adaptativa_ativa: bool = True,
        pontuacao_minima_reposicao_fila: float = 45.0,
        alvo_minimo_pendentes_fila: int = 2,
        queda_minima_republicacao_percentual: float = 5.0,
        cooldown_republicacao_sem_queda_minutos: float = 720.0,
        repositorio_admin: ControleAdministrativoRepository | None = None,
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
        self.fila_reposicao_adaptativa_ativa = fila_reposicao_adaptativa_ativa
        self.pontuacao_minima_reposicao_fila = pontuacao_minima_reposicao_fila
        self.alvo_minimo_pendentes_fila = alvo_minimo_pendentes_fila
        self.queda_minima_republicacao_percentual = queda_minima_republicacao_percentual
        self.cooldown_republicacao_sem_queda_minutos = cooldown_republicacao_sem_queda_minutos
        self.repositorio_admin = repositorio_admin

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

                    logger.debug(
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

                    logger.debug(
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
                logger.debug(
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

                logger.debug(
                    "Oferta rejeitada pela curadoria: %s | nota=%.1f | %s",
                    oferta.nome,
                    resultado_curadoria.nota,
                    " | ".join(detalhes),
                )
                continue

            oferta_ja_publicada = self.repository.ja_foi_publicada(oferta.link)

            queda_percentual_republicacao = self._obter_queda_percentual(resultado_historico)
            deve_republicar_por_queda = (
                oferta_ja_publicada
                and queda_percentual_republicacao >= self.queda_minima_republicacao_percentual
            )
            pode_republicar_por_tempo = oferta_ja_publicada and self._pode_republicar_por_tempo(
                oferta.link
            )
            permitir_republicacao = deve_republicar_por_queda or pode_republicar_por_tempo

            if oferta_ja_publicada and not permitir_republicacao:
                logger.debug("Ignorando oferta já publicada: %s", oferta.nome)

                quantidade_ignorada += 1
                continue

            if deve_republicar_por_queda:
                logger.debug(
                    (
                        "Oferta já publicada voltou a ser elegível por queda "
                        "material de %.2f%%: %s"
                    ),
                    queda_percentual_republicacao,
                    oferta.nome,
                )
            elif pode_republicar_por_tempo:
                logger.debug(
                    "Oferta já publicada voltou a ser elegível após o cooldown: %s",
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
                (
                    oferta,
                    pontuacao,
                    resultado_historico,
                    deve_republicar_por_queda,
                    permitir_republicacao,
                )
            )

            logger.debug("Oferta elegível: %s | Pontuação final: %.2f", oferta.nome, pontuacao)

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

        expiradas = self.fila_publicacao_repository.expirar_antigos(self.fila_idade_maxima_minutos)

        if expiradas:
            logger.info("Itens antigos expirados da fila: %s", expiradas)

        quantidade_pendente_antes = self.fila_publicacao_repository.quantidade_pendente()

        candidatos_fila, quantidade_reposicao_adaptativa = self._selecionar_candidatos_para_fila(
            candidatos=ofertas_aprovadas,
            pontuacao_minima_principal=self.pontuacao_minima_fila,
            reposicao_adaptativa_ativa=self.fila_reposicao_adaptativa_ativa,
            pontuacao_minima_reposicao=self.pontuacao_minima_reposicao_fila,
            alvo_minimo_pendentes=self.alvo_minimo_pendentes_fila,
            quantidade_pendente=quantidade_pendente_antes,
        )

        quantidade_descartada_score_fila = len(ofertas_aprovadas) - len(candidatos_fila)

        if quantidade_reposicao_adaptativa > 0:
            logger.info(
                (
                    "Reposição adaptativa da fila: %s candidato(s) abaixo do piso "
                    "principal selecionado(s) para abastecer a fila."
                ),
                quantidade_reposicao_adaptativa,
            )

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

        for (
            oferta,
            pontuacao,
            resultado_historico,
            deve_republicar_por_queda,
            permitir_republicacao,
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
                permitir_republicacao=permitir_republicacao,
            )

            if resultado_fila in {
                "adicionado",
                "reativado",
                "reativado_por_queda",
                "reativado_por_tempo",
            }:
                quantidade_enfileirada += 1
            elif resultado_fila in {
                "atualizado",
                "substituido_canonico",
                "substituido_familia",
            }:
                quantidade_atualizada_na_fila += 1

            logger.debug(
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
            len(ofertas_aprovadas) - len(candidatos_fila),
        )

        taxa_aprovacao_filtro = (
            quantidade_aprovada_pelo_filtro / len(ofertas) * 100 if ofertas else 0.0
        )

        tempo_total = perf_counter() - inicio_execucao

        logger.info(
            (
                "Resumo do ciclo | coletadas=%s | filtro=%s | elegíveis=%s | "
                "fila +%s/~%s | reposição=%s | abaixo_score=%s | pendentes=%s"
            ),
            len(ofertas),
            quantidade_aprovada_pelo_filtro,
            len(ofertas_aprovadas),
            quantidade_enfileirada,
            quantidade_atualizada_na_fila,
            quantidade_reposicao_adaptativa,
            quantidade_descartada_score_fila,
            quantidade_pendente_fila,
        )

        logger.info(
            (
                "Qualidade do ciclo | rejeitadas=%s | curadoria=%s | "
                "deduplicadas=%s | já_publicadas=%s | quedas=%s | mínimos=%s | "
                "anomalias=%s/%s | erros=%s"
            ),
            quantidade_filtrada,
            quantidade_rejeitada_curadoria,
            quantidade_deduplicada_canonica,
            quantidade_ignorada,
            quantidade_quedas_detectadas,
            quantidade_menores_precos,
            quantidade_anomalias_publicaveis,
            quantidade_anomalias_retidas,
            quantidade_com_erro,
        )

        logger.info("Ciclo concluído em %.2f segundo(s).", tempo_total)

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
            "reposicao_adaptativa_fila": quantidade_reposicao_adaptativa,
            "fila_pendente_antes": quantidade_pendente_antes,
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

        self._registrar_telemetria_fluxo(
            ofertas_coletadas=len(ofertas),
            ofertas_elegiveis=len(ofertas_aprovadas),
            ofertas_enfileiradas=quantidade_enfileirada,
            ofertas_abaixo_score=quantidade_descartada_score_fila,
            reposicao_adaptativa=quantidade_reposicao_adaptativa,
            fila_pendente=quantidade_pendente_fila,
        )

        self.relatorios_repository.salvar(relatorio)

        logger.info("Execução finalizada.")

        logger.info("=" * 60)

    @staticmethod
    def _obter_queda_percentual(
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> float:
        if resultado_historico is None or not resultado_historico.preco_caiu:
            return 0.0

        try:
            return abs(float(resultado_historico.variacao_percentual))
        except (TypeError, ValueError):
            return 0.0

    def _pode_republicar_por_tempo(self, link: str) -> bool:
        ultima_publicacao = self.fila_publicacao_repository.obter_ultima_publicacao_link(link)

        if ultima_publicacao is None:
            return False

        agora = datetime.now().astimezone()
        minutos = max(
            0.0,
            (agora - ultima_publicacao.astimezone()).total_seconds() / 60.0,
        )

        return minutos >= self.cooldown_republicacao_sem_queda_minutos

    @staticmethod
    def _selecionar_candidatos_para_fila(
        candidatos: list,
        pontuacao_minima_principal: float,
        reposicao_adaptativa_ativa: bool,
        pontuacao_minima_reposicao: float,
        alvo_minimo_pendentes: int,
        quantidade_pendente: int,
    ) -> tuple[list, int]:
        """Mantém o piso principal e usa reposição controlada só quando falta fila.

        A reposição não transforma o piso baixo no novo padrão. Ela apenas completa
        o mínimo operacional da fila com os melhores candidatos disponíveis, sem
        ultrapassar o alvo mínimo e sem furar curadoria/deduplicação.
        """

        fortes = [
            item
            for item in candidatos
            if item[1] >= pontuacao_minima_principal
            or item[0].tipo_oportunidade in {"possivel_preco_bugado", "anomalia_forte"}
        ]

        if not reposicao_adaptativa_ativa:
            return fortes, 0

        vagas_reposicao = max(
            0,
            int(alvo_minimo_pendentes) - int(quantidade_pendente) - len(fortes),
        )

        if vagas_reposicao <= 0:
            return fortes, 0

        ids_fortes = {id(item) for item in fortes}

        reposicao = [
            item
            for item in candidatos
            if id(item) not in ids_fortes and item[1] >= pontuacao_minima_reposicao
        ][:vagas_reposicao]

        return fortes + reposicao, len(reposicao)

    def _registrar_telemetria_fluxo(
        self,
        ofertas_coletadas: int,
        ofertas_elegiveis: int,
        ofertas_enfileiradas: int,
        ofertas_abaixo_score: int,
        reposicao_adaptativa: int,
        fila_pendente: int,
    ) -> None:
        if self.repositorio_admin is None:
            return

        agora = datetime.now().astimezone().isoformat(timespec="seconds")
        valores = {
            "pipeline_ultimo_ofertas_coletadas": ofertas_coletadas,
            "pipeline_ultimo_ofertas_elegiveis": ofertas_elegiveis,
            "pipeline_ultimo_ofertas_enfileiradas": ofertas_enfileiradas,
            "pipeline_ultimo_ofertas_abaixo_score": ofertas_abaixo_score,
            "pipeline_ultimo_reposicao_adaptativa": reposicao_adaptativa,
            "pipeline_ultimo_fila_pendente": fila_pendente,
            "pipeline_ultimo_executado_em": agora,
        }

        for chave, valor in valores.items():
            self.repositorio_admin.definir_estado(chave, str(valor))

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
            oferta = item[0]
            pontuacao = item[1]

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
            oferta_existente = item_existente[0]
            pontuacao_existente = item_existente[1]

            if self._nova_oferta_e_melhor_representante(
                oferta_nova=oferta,
                pontuacao_nova=pontuacao,
                oferta_atual=oferta_existente,
                pontuacao_atual=pontuacao_existente,
            ):
                logger.debug(
                    ("Deduplicação canônica: trocando representante de %s | " "%s %.2f -> %s %.2f"),
                    oferta.produto_canonico,
                    oferta_existente.moeda,
                    oferta_existente.preco,
                    oferta.moeda,
                    oferta.preco,
                )
                selecionadas[indice_existente] = item
            else:
                logger.debug(
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
