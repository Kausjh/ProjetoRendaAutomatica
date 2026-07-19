import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.oferta import Oferta
from scrapers.base_scraper import BaseScraper
from services.classificador_produto import ClassificadorProduto
from services.pipeline.pipeline import Pipeline


logger = logging.getLogger(__name__)


class ColetorOfertas:

    def __init__(
        self,
        scrapers: list[BaseScraper],
        classificador: ClassificadorProduto,
        pipeline: Pipeline | None = None
    ) -> None:

        self.scrapers = scrapers
        self.classificador = classificador
        self.pipeline = pipeline

    def _executar_scraper(
        self,
        scraper: BaseScraper,
        limite: int
    ) -> list[Oferta]:

        nome_scraper = type(scraper).__name__

        logger.info(
            "Executando scraper: %s",
            nome_scraper
        )

        ofertas = scraper.buscar_ofertas(
            limite=limite
        )

        logger.info(
            "Scraper '%s' encontrou %s oferta(s).",
            nome_scraper,
            len(ofertas)
        )

        return ofertas

    def _remover_duplicadas(
        self,
        ofertas: list[Oferta]
    ) -> list[Oferta]:

        ofertas_unicas: list[Oferta] = []

        links = set()

        for oferta in ofertas:

            if oferta.link in links:

                logger.info(
                    "Oferta duplicada removida: %s",
                    oferta.nome
                )

                continue

            links.add(
                oferta.link
            )

            ofertas_unicas.append(
                oferta
            )

        return ofertas_unicas

    def _classificar_ofertas(
        self,
        ofertas: list[Oferta]
    ) -> list[Oferta]:

        resultado: list[Oferta] = []

        for oferta in ofertas:

            classificacao = (
                self.classificador
                .aplicar_classificacao(
                    oferta
                )
            )

            if not classificacao.eh_nicho:

                logger.info(
                    "Oferta fora do nicho removida: '%s'. Motivo: %s",
                    oferta.nome,
                    classificacao.motivo
                )

                continue

            logger.info(
                "Oferta classificada: '%s' | Categoria: %s | Relevância: %.2f.",
                oferta.nome,
                classificacao.categoria,
                classificacao.relevancia
            )

            resultado.append(
                oferta
            )

        logger.info(
            "Classificação concluída: %s de %s oferta(s) pertencem ao nicho.",
            len(resultado),
            len(ofertas)
        )

        return resultado

    def _processar_pipeline(
        self,
        ofertas: list[Oferta]
    ) -> list[Oferta]:

        if self.pipeline is None:
            return ofertas

        resultado: list[Oferta] = []

        for oferta in ofertas:

            resultado.append(
                self.pipeline.executar(
                    oferta
                )
            )

        return resultado

    def buscar_ofertas(
        self,
        limite_por_scraper: int
    ) -> list[Oferta]:

        ofertas: list[Oferta] = []

        if not self.scrapers:

            logger.warning(
                "Nenhum scraper foi configurado."
            )

            return ofertas

        with ThreadPoolExecutor(
            max_workers=max(
                1,
                len(self.scrapers)
            )
        ) as executor:

            tarefas = {
                executor.submit(
                    self._executar_scraper,
                    scraper,
                    limite_por_scraper
                ): scraper
                for scraper in self.scrapers
            }

            for tarefa in as_completed(
                tarefas
            ):

                scraper = tarefas[tarefa]

                try:

                    ofertas.extend(
                        tarefa.result()
                    )

                except Exception:

                    logger.exception(
                        "Erro ao executar o scraper '%s'.",
                        type(scraper).__name__
                    )

        logger.info(
            "Ofertas coletadas antes da remoção de duplicatas: %s",
            len(ofertas)
        )

        ofertas = self._remover_duplicadas(
            ofertas
        )

        ofertas = self._classificar_ofertas(
            ofertas
        )

        ofertas = self._processar_pipeline(
            ofertas
        )

        logger.info(
            "Pipeline executado para %s oferta(s).",
            len(ofertas)
        )

        return ofertas