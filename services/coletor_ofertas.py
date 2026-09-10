# 63.8738, -149.7525

import logging
from collections.abc import Mapping

from models.oferta import Oferta
from models.resultado_hunter_v2 import ResultadoHunterV2
from scrapers.base_scraper import BaseScraper
from services.classificador_produto import ClassificadorProduto
from services.hunter_v2 import HunterV2
from services.pipeline.pipeline import Pipeline
from services.validadores.validador_oferta import (
    EstatisticasValidacao,
    ValidadorOferta,
)

logger = logging.getLogger(__name__)


class ColetorOfertas:

    def __init__(
        self,
        scrapers: list[BaseScraper],
        classificador: ClassificadorProduto,
        pipeline: Pipeline | None = None,
        validador: ValidadorOferta | None = None,
        hunter: HunterV2 | None = None,
        limites_hunter_por_fonte: (
            Mapping[
                str,
                int,
            ]
            | None
        ) = None,
    ) -> None:
        self.scrapers = list(scrapers)

        self.classificador = classificador
        self.pipeline = pipeline

        self.validador = validador if validador is not None else ValidadorOferta()

        self.hunter = hunter if hunter is not None else HunterV2(self.scrapers)

        self.limites_hunter_por_fonte = dict(limites_hunter_por_fonte or {})

        self.ultimo_resultado_hunter: ResultadoHunterV2 | None = None

    def _confirmar_handoff(
        self,
        oferta: Oferta,
        *,
        status: str,
        motivo: str,
    ) -> bool:
        for scraper in self.scrapers:
            confirmar = getattr(
                scraper,
                "confirmar_handoff",
                None,
            )

            if not callable(confirmar):
                continue

            try:
                confirmado = confirmar(
                    oferta,
                    status=status,
                    motivo=motivo,
                )

            except Exception:
                logger.exception(
                    ("Erro ao confirmar handoff " "da oferta '%s' no scraper '%s'."),
                    oferta.nome,
                    type(scraper).__name__,
                )

                continue

            if confirmado:
                return True

        return False

    def confirmar_handoffs(
        self,
        ofertas: list[Oferta],
        *,
        status: str,
        motivo: str,
    ) -> int:
        confirmados = 0

        for oferta in ofertas:
            if self._confirmar_handoff(
                oferta,
                status=status,
                motivo=motivo,
            ):
                confirmados += 1

        return confirmados

    def _confirmar_duplicatas_hunter(
        self,
        resultado: ResultadoHunterV2,
    ) -> int:
        confirmadas = 0

        for duplicata in resultado.duplicatas:
            if duplicata.tipo_identidade == "link_exato":
                motivo = "link_duplicado_no_coletor"

            else:
                motivo = "identidade_segura_" "duplicada_no_hunter"

            if self._confirmar_handoff(
                duplicata.oferta,
                status="coletor_duplicada",
                motivo=motivo,
            ):
                confirmadas += 1

        return confirmadas

    def _remover_duplicadas(
        self,
        ofertas: list[Oferta],
    ) -> list[Oferta]:
        ofertas_unicas: list[Oferta] = []

        links = set()

        for oferta in ofertas:
            if oferta.link in links:
                logger.debug(
                    "Oferta duplicada removida: %s",
                    oferta.nome,
                )

                self._confirmar_handoff(
                    oferta,
                    status="coletor_duplicada",
                    motivo=("link_duplicado_no_coletor"),
                )

                continue

            links.add(oferta.link)

            ofertas_unicas.append(oferta)

        return ofertas_unicas

    def _validar_ofertas(
        self,
        ofertas: list[Oferta],
    ) -> list[Oferta]:
        resultado: list[Oferta] = []

        estatisticas = EstatisticasValidacao()

        for oferta in ofertas:
            oferta_validada = self.validador.validar(
                oferta,
                estatisticas=estatisticas,
            )

            resultado.append(oferta_validada)

        logger.info(estatisticas.formatar_resumo())

        return resultado

    def _classificar_ofertas(
        self,
        ofertas: list[Oferta],
    ) -> list[Oferta]:
        resultado: list[Oferta] = []

        for oferta in ofertas:
            if not oferta.valida:
                logger.warning(
                    ("Oferta invalida nao seguira " "para a classificacao: '%s'. " "Motivos: %s"),
                    oferta.nome,
                    "; ".join(oferta.motivos_validacao),
                )

                self._confirmar_handoff(
                    oferta,
                    status=("coletor_rejeitada_validacao"),
                    motivo=(
                        "; ".join(oferta.motivos_validacao) or ("oferta_invalida_" "no_coletor")
                    ),
                )

                continue

            classificacao = self.classificador.aplicar_classificacao(oferta)

            if not classificacao.eh_nicho:
                logger.debug(
                    ("Oferta fora do nicho " "removida: '%s'. Motivo: %s"),
                    oferta.nome,
                    classificacao.motivo,
                )

                self._confirmar_handoff(
                    oferta,
                    status="coletor_fora_nicho",
                    motivo=(classificacao.motivo or "fora_do_nicho"),
                )

                continue

            logger.debug(
                ("Oferta classificada: '%s' | " "Categoria: %s | " "Relevancia: %.2f."),
                oferta.nome,
                classificacao.categoria,
                classificacao.relevancia,
            )

            resultado.append(oferta)

        logger.info(
            ("Classificacao concluida: " "%s de %s oferta(s) " "pertencem ao nicho."),
            len(resultado),
            len(ofertas),
        )

        return resultado

    def _processar_pipeline(
        self,
        ofertas: list[Oferta],
    ) -> list[Oferta]:
        if self.pipeline is None:
            return ofertas

        resultado: list[Oferta] = []

        for oferta in ofertas:
            resultado.append(self.pipeline.executar(oferta))

        return resultado

    def buscar_ofertas(
        self,
        limite_por_scraper: int,
    ) -> list[Oferta]:
        if not self.scrapers:
            logger.warning("Nenhum scraper foi configurado.")

            return []

        resultado_hunter = self.hunter.descobrir(
            limite_por_scraper,
            limites_por_fonte=(self.limites_hunter_por_fonte),
        )

        self.ultimo_resultado_hunter = resultado_hunter

        handoffs_duplicatas = self._confirmar_duplicatas_hunter(resultado_hunter)

        logger.info(
            (
                "Hunter V2 -> Coletor: "
                "%s bruta(s), "
                "%s unica(s), "
                "%s duplicada(s), "
                "%s fonte(s) com erro, "
                "%s handoff(s) de duplicata."
            ),
            resultado_hunter.quantidade_bruta,
            resultado_hunter.quantidade_unica,
            (resultado_hunter.duplicadas_confirmadas),
            len(resultado_hunter.fontes_com_erro),
            handoffs_duplicatas,
        )

        ofertas = resultado_hunter.ofertas

        # Barreira defensiva legada.
        ofertas = self._remover_duplicadas(ofertas)

        ofertas = self._validar_ofertas(ofertas)

        ofertas = self._classificar_ofertas(ofertas)

        ofertas = self._processar_pipeline(ofertas)

        logger.info(
            "Pipeline executado para %s oferta(s).",
            len(ofertas),
        )

        return ofertas
