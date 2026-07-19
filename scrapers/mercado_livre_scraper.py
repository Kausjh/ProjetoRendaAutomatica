import logging

import requests

from models.oferta import Oferta
from scrapers.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class MercadoLivreScraper(BaseScraper):

    URL_BUSCA = (
        "https://api.mercadolibre.com/sites/MLB/search"
    )

    def __init__(
        self,
        termo_busca: str
    ) -> None:
        termo_normalizado = termo_busca.strip()

        if not termo_normalizado:
            raise ValueError(
                "O termo de busca do Mercado Livre não pode estar vazio."
            )

        self.termo_busca = termo_normalizado

    def buscar_ofertas(
        self,
        limite: int = 5
    ) -> list[Oferta]:
        logger.info(
            "Buscando '%s' no Mercado Livre.",
            self.termo_busca
        )

        resposta = requests.get(
            self.URL_BUSCA,
            params={
                "q": self.termo_busca,
                "limit": limite
            },
            timeout=15
        )

        resposta.raise_for_status()

        dados = resposta.json()

        produtos = dados.get(
            "results",
            []
        )

        ofertas: list[Oferta] = []

        for produto in produtos:
            nome = produto.get(
                "title"
            )

            preco = produto.get(
                "price"
            )

            preco_antigo = produto.get(
                "original_price"
            )

            link = produto.get(
                "permalink"
            )

            imagem = produto.get(
                "thumbnail"
            )

            if (
                not nome
                or preco is None
                or not link
            ):
                logger.warning(
                    "Produto do Mercado Livre ignorado "
                    "por possuir dados incompletos."
                )

                continue

            if imagem:
                imagem = imagem.replace(
                    "http://",
                    "https://"
                )

            oferta = Oferta(
                nome=str(nome),
                loja="Mercado Livre",
                preco=float(preco),
                preco_antigo=(
                    float(preco_antigo)
                    if preco_antigo is not None
                    else None
                ),
                link=str(link),
                imagem=imagem,
                moeda="R$"
            )

            ofertas.append(
                oferta
            )

        logger.info(
            "Busca por '%s' retornou %s oferta(s) válidas.",
            self.termo_busca,
            len(ofertas)
        )

        return ofertas