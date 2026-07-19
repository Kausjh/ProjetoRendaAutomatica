from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from models.oferta import Oferta
from scrapers.base_scraper import BaseScraper


class ExemploScraper(BaseScraper):

    def buscar_ofertas(
        self,
        limite: int = 5
    ) -> list[Oferta]:
        url = "https://books.toscrape.com/"

        resposta = requests.get(
            url,
            timeout=10
        )

        resposta.raise_for_status()

        pagina = BeautifulSoup(
            resposta.text,
            "html.parser"
        )

        produtos = pagina.select(
            "article.product_pod"
        )

        ofertas = []

        for produto in produtos[:limite]:
            link_elemento = produto.select_one(
                "h3 a"
            )

            preco_elemento = produto.select_one(
                "p.price_color"
            )

            imagem_elemento = produto.select_one(
                "img"
            )

            nome = link_elemento["title"]

            preco_texto = preco_elemento.get_text(
                strip=True
            )

            link = urljoin(
                url,
                link_elemento["href"]
            )

            imagem = urljoin(
                url,
                imagem_elemento["src"]
            )

            preco = self._converter_preco(
                preco_texto
            )

            oferta = Oferta(
                nome=nome,
                loja="Books to Scrape",
                preco=preco,
                preco_antigo=preco,
                link=link,
                imagem=imagem,
                moeda="£"
            )

            ofertas.append(oferta)

        return ofertas

    def _converter_preco(
        self,
        preco_texto: str
    ) -> float:
        preco_limpo = (
            preco_texto
            .replace("Â", "")
            .replace("£", "")
            .strip()
        )

        return float(preco_limpo)