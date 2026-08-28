import logging
from typing import Any
from urllib.parse import urlparse

from models.oferta import Oferta
from scrapers.base_scraper import BaseScraper
from services.shopee_api_service import ShopeeApiService

logger = logging.getLogger(__name__)

# 63.8738, -149.7525


class ShopeeScraper(BaseScraper):
    TERMOS_PADRAO = [
        "Ryzen 5",
        "Ryzen 7",
        "Intel Core i5",
        "Intel Core i7",
        "RTX placa de v?deo",
        "RX placa de v?deo",
        "SSD NVMe",
        "Mem?ria RAM DDR4",
        "Mem?ria RAM DDR5",
        "Monitor gamer",
        "Fonte Corsair",
        "Fonte MSI",
        "Placa m?e B550",
        "Placa m?e B650",
        "Gabinete gamer",
        "Mouse Logitech",
        "Teclado Redragon",
        "Headset HyperX",
    ]

    def __init__(
        self,
        termos_busca: list[str] | None = None,
        service: ShopeeApiService | None = None,
    ) -> None:
        termos = termos_busca if termos_busca is not None else self.TERMOS_PADRAO

        self.termos_busca = [termo.strip() for termo in termos if termo and termo.strip()]

        if not self.termos_busca:
            raise ValueError("A lista de termos da Shopee n?o pode estar vazia.")

        self.service = service or ShopeeApiService()

    def buscar_ofertas(
        self,
        limite: int = 5,
    ) -> list[Oferta]:
        if limite <= 0:
            logger.warning("O limite da Shopee deve ser maior que zero.")
            return []

        ofertas: list[Oferta] = []
        chaves_processadas: set[str] = set()

        for indice, termo in enumerate(
            self.termos_busca,
            start=1,
        ):
            logger.info(
                "Pesquisando na Shopee (%s/%s): %s",
                indice,
                len(self.termos_busca),
                termo,
            )

            try:
                produtos = self.service.buscar_produtos(
                    termo=termo,
                    limite=limite,
                    pagina=1,
                    tipo_ordenacao=1,
                )

            except Exception:
                logger.exception(
                    "Erro ao pesquisar '%s' na Shopee.",
                    termo,
                )
                continue

            novas = 0

            for produto in produtos:
                try:
                    oferta = self._criar_oferta(produto)

                    if oferta is None:
                        continue

                    chave = self._criar_chave(oferta)

                    if chave in chaves_processadas:
                        continue

                    chaves_processadas.add(chave)
                    ofertas.append(oferta)
                    novas += 1

                except Exception:
                    logger.exception(
                        "Erro ao processar produto da Shopee " "na busca '%s'.",
                        termo,
                    )

            logger.info(
                "Termo '%s': %s oferta(s) retornada(s), " "%s nova(s).",
                termo,
                len(produtos),
                novas,
            )

        logger.info(
            "Shopee: %s oferta(s) ?nica(s) coletada(s).",
            len(ofertas),
        )

        return ofertas

    @classmethod
    def _criar_oferta(
        cls,
        produto: dict[str, Any],
    ) -> Oferta | None:
        nome = cls._normalizar_texto(produto.get("productName"))

        link = cls._normalizar_link(produto.get("productLink"))

        preco = cls._converter_numero(produto.get("priceMin"))

        if not nome or not link or preco is None or preco <= 0:
            return None

        imagem = cls._normalizar_imagem(produto.get("imageUrl"))

        desconto = cls._converter_percentual(produto.get("priceDiscountRate"))

        item_id = cls._normalizar_identificador(produto.get("itemId"))

        return Oferta(
            nome=nome,
            loja="Shopee",
            preco=round(preco, 2),
            preco_antigo=None,
            link=link,
            imagem=imagem,
            moeda="R$",
            desconto_anunciado=desconto,
            marketplace="shopee",
            id_produto=item_id,
            id_anuncio=item_id,
        )

    @staticmethod
    def _normalizar_texto(
        valor: Any,
    ) -> str | None:
        if not isinstance(valor, str):
            return None

        valor = " ".join(valor.split()).strip()

        return valor or None

    @staticmethod
    def _normalizar_link(
        valor: Any,
    ) -> str | None:
        if not isinstance(valor, str):
            return None

        link = valor.strip()

        if not link:
            return None

        parsed = urlparse(link)
        dominio = (parsed.hostname or "").lower()

        if parsed.scheme not in {"http", "https"}:
            return None

        if not (dominio == "shopee.com.br" or dominio.endswith(".shopee.com.br")):
            return None

        return link.split("#")[0].strip()

    @staticmethod
    def _normalizar_imagem(
        valor: Any,
    ) -> str | None:
        if not isinstance(valor, str):
            return None

        imagem = valor.strip()

        if not imagem:
            return None

        if imagem.startswith("//"):
            imagem = "https:" + imagem

        return imagem.replace(
            "http://",
            "https://",
        )

    @staticmethod
    def _converter_numero(
        valor: Any,
    ) -> float | None:
        if valor is None:
            return None

        texto = str(valor).strip()

        if not texto:
            return None

        texto = texto.replace("R$", "").replace(" ", "")

        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif "," in texto:
            texto = texto.replace(",", ".")

        try:
            numero = float(texto)
        except (TypeError, ValueError):
            return None

        if numero <= 0:
            return None

        return numero

    @classmethod
    def _converter_percentual(
        cls,
        valor: Any,
    ) -> float | None:
        numero = cls._converter_numero(valor)

        if numero is None:
            if str(valor).strip() in {"0", "0.0", "0.00"}:
                return 0.0

            return None

        if numero > 100:
            return None

        return round(numero, 2)

    @staticmethod
    def _normalizar_identificador(
        valor: Any,
    ) -> str | None:
        if valor is None:
            return None

        identificador = str(valor).strip()

        return identificador or None

    @staticmethod
    def _criar_chave(
        oferta: Oferta,
    ) -> str:
        if oferta.id_produto:
            return f"item:{oferta.id_produto}"

        return oferta.link.split("?")[0].rstrip("/").lower()
