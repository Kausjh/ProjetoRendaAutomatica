import logging
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from models.oferta import Oferta
from scrapers.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class SegundoExemploScraper(BaseScraper):

    URL_BASE = "https://books.toscrape.com/"

    URL_CATEGORIA = (
        "https://books.toscrape.com/catalogue/"
        "category/books/science-fiction_16/index.html"
    )

    def buscar_ofertas(
        self,
        limite: int = 5
    ) -> list[Oferta]:
        logger.info(
            "Buscando ofertas na categoria Science Fiction."
        )

        resposta = requests.get(
            self.URL_CATEGORIA,
            timeout=15
        )

        resposta.raise_for_status()

        pagina = BeautifulSoup(
            resposta.content,
            "html.parser"
        )

        produtos = pagina.select(
            "article.product_pod"
        )

        ofertas: list[Oferta] = []

        for produto in produtos[:limite]:
            elemento_link = produto.select_one(
                "h3 a"
            )

            elemento_preco = produto.select_one(
                ".price_color"
            )

            elemento_imagem = produto.select_one(
                ".image_container img"
            )

            if (
                elemento_link is None
                or elemento_preco is None
                or elemento_imagem is None
            ):
                logger.warning(
                    "Produto ignorado por possuir dados incompletos."
                )

                continue

            nome = elemento_link.get(
                "title",
                "Produto sem nome"
            )

            preco_texto = elemento_preco.get_text(
                strip=True
            )

            preco_encontrado = re.search(
                r"\d+(?:[.,]\d+)?",
                preco_texto
            )

            if preco_encontrado is None:
                logger.warning(
                    "Produto '%s' ignorado porque o preço "
                    "não pôde ser interpretado: %s",
                    nome,
                    preco_texto
                )

                continue

            preco_normalizado = (
                preco_encontrado
                .group()
                .replace(",", ".")
            )

            preco = float(
                preco_normalizado
            )

            link_relativo = elemento_link.get(
                "href",
                ""
            )

            imagem_relativa = elemento_imagem.get(
                "src",
                ""
            )

            link = urljoin(
                self.URL_CATEGORIA,
                link_relativo
            )

            imagem = urljoin(
                self.URL_CATEGORIA,
                imagem_relativa
            )

            oferta = Oferta(
                nome=str(nome),
                loja="Books to Scrape - Science Fiction",
                preco=preco,
                preco_antigo=None,
                link=link,
                imagem=imagem,
                moeda="£"
            )

            ofertas.append(
                oferta
            )

        return ofertas