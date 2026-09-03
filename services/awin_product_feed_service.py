# 63.8738, -149.7525

from __future__ import annotations

import csv
import gzip
import io
import os
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class FeedAwin:
    advertiser_id: str
    advertiser_name: str
    feed_id: str
    feed_name: str
    language: str
    membership_status: str
    last_imported: str
    url: str

    @property
    def ativo(self) -> bool:
        return self.membership_status.strip().lower() in {
            "active",
            "joined",
        }


@dataclass(frozen=True, slots=True)
class ProdutoFeedAwin:
    feed_id: str
    aw_product_id: str
    merchant_product_id: str
    nome: str
    moeda: str
    preco_feed: float | None
    preco_base_feed: float | None
    desconto_percentual_feed: float | None
    estoque: int | None
    categoria_merchant: str
    categoria_awin: str
    marca: str
    link_merchant: str
    link_awin: str
    aw_image_url: str
    alternate_image: str
    alternate_image_two: str
    alternate_image_three: str
    alternate_image_four: str

    @property
    def imagem(self) -> str | None:
        candidatos = (
            self.aw_image_url,
            self.alternate_image,
            self.alternate_image_two,
            self.alternate_image_three,
            self.alternate_image_four,
        )

        for candidato in candidatos:
            if _imagem_valida(candidato):
                return candidato

        return None


class AwinProductFeedService:
    ADVERTISER_ALIEXPRESS = "18879"
    URL_LISTA = "https://productdata.awin.com/" "datafeed/list/apikey/{api_key}"

    def __init__(
        self,
        api_key: str | None = None,
        timeout_segundos: float = 60.0,
        urlopen=None,
    ) -> None:
        chave = (
            api_key
            if api_key is not None
            else os.getenv(
                "AWIN_PRODUCT_FEED_API_KEY",
                "",
            )
        )

        self.api_key = str(chave).strip()

        if not self.api_key:
            raise ValueError("AWIN_PRODUCT_FEED_API_KEY nao esta configurado.")

        if timeout_segundos <= 0:
            raise ValueError("timeout_segundos precisa ser maior que zero.")

        self.timeout_segundos = float(timeout_segundos)

        self._urlopen = urlopen if urlopen is not None else urllib.request.urlopen

    def listar_feeds(
        self,
        advertiser_id: str | None = None,
        somente_ativos: bool = False,
    ) -> list[FeedAwin]:
        url = self.URL_LISTA.format(api_key=self.api_key)

        feeds: list[FeedAwin] = []

        with self._abrir_csv(url) as leitor:
            for linha in leitor:
                feed = FeedAwin(
                    advertiser_id=_texto(linha.get("Advertiser ID")),
                    advertiser_name=_texto(linha.get("Advertiser Name")),
                    feed_id=_texto(linha.get("Feed ID")),
                    feed_name=_texto(linha.get("Feed Name")),
                    language=_texto(linha.get("Language")),
                    membership_status=_texto(linha.get("Membership Status")),
                    last_imported=_texto(linha.get("Last Imported")),
                    url=_texto(linha.get("URL")),
                )

                if advertiser_id is not None and feed.advertiser_id != str(advertiser_id):
                    continue

                if somente_ativos and not feed.ativo:
                    continue

                feeds.append(feed)

        return feeds

    def obter_feed(
        self,
        feed_id: str,
        advertiser_id: str = ADVERTISER_ALIEXPRESS,
    ) -> FeedAwin:
        feed_id = str(feed_id).strip()

        for feed in self.listar_feeds(
            advertiser_id=advertiser_id,
            somente_ativos=True,
        ):
            if feed.feed_id == feed_id:
                return feed

        raise LookupError(
            "Feed Awin nao encontrado ou nao ativo: "
            f"advertiser={advertiser_id}, "
            f"feed={feed_id}."
        )

    def iterar_produtos(
        self,
        feed_id: str,
        limite: int | None = None,
        advertiser_id: str = ADVERTISER_ALIEXPRESS,
    ):
        if limite is not None and limite <= 0:
            raise ValueError("limite precisa ser maior que zero.")

        feed = self.obter_feed(
            feed_id=feed_id,
            advertiser_id=advertiser_id,
        )

        quantidade = 0

        with self._abrir_csv(feed.url) as leitor:
            for linha in leitor:
                yield ProdutoFeedAwin(
                    feed_id=feed.feed_id,
                    aw_product_id=_texto(linha.get("aw_product_id")),
                    merchant_product_id=_texto(linha.get("merchant_product_id")),
                    nome=_texto(linha.get("product_name")),
                    moeda=_texto(linha.get("currency")).upper(),
                    preco_feed=_decimal(linha.get("search_price")),
                    preco_base_feed=_decimal(linha.get("base_price")),
                    desconto_percentual_feed=_percentual(linha.get("savings_percent")),
                    estoque=_inteiro(linha.get("stock_quantity")),
                    categoria_merchant=_texto(linha.get("merchant_category")),
                    categoria_awin=_texto(linha.get("category_name")),
                    marca=_texto(linha.get("brand_name")),
                    link_merchant=_texto(linha.get("merchant_deep_link")),
                    link_awin=_texto(linha.get("aw_deep_link")),
                    aw_image_url=_texto(linha.get("aw_image_url")),
                    alternate_image=_texto(linha.get("alternate_image")),
                    alternate_image_two=_texto(linha.get("alternate_image_two")),
                    alternate_image_three=_texto(linha.get("alternate_image_three")),
                    alternate_image_four=_texto(linha.get("alternate_image_four")),
                )

                quantidade += 1

                if limite is not None and quantidade >= limite:
                    break

    @contextmanager
    def _abrir_csv(
        self,
        url: str,
    ):
        requisicao = urllib.request.Request(
            url,
            headers={"User-Agent": ("RadarDeOfertas/1.0")},
        )

        with self._urlopen(
            requisicao,
            timeout=self.timeout_segundos,
        ) as resposta:
            if "/compression/gzip/" in url:
                binario = gzip.GzipFile(fileobj=resposta)
            else:
                binario = resposta

            texto = io.TextIOWrapper(
                binario,
                encoding="utf-8-sig",
                errors="replace",
                newline="",
            )

            try:
                yield csv.DictReader(texto)
            finally:
                texto.close()


def _texto(
    valor: object,
) -> str:
    if valor is None:
        return ""

    return str(valor).strip()


def _decimal(
    valor: object,
) -> float | None:
    texto = _texto(valor)

    if not texto:
        return None

    try:
        numero = float(texto)
    except ValueError:
        return None

    if numero < 0:
        return None

    return numero


def _inteiro(
    valor: object,
) -> int | None:
    texto = _texto(valor)

    if not texto:
        return None

    try:
        return int(float(texto))
    except ValueError:
        return None


def _percentual(
    valor: object,
) -> float | None:
    texto = _texto(valor).replace(
        "%",
        "",
    )

    return _decimal(texto)


def _imagem_valida(
    url: str,
) -> bool:
    url = url.strip()

    if not url:
        return False

    parsed = urlparse(url)

    if parsed.scheme not in {
        "http",
        "https",
    }:
        return False

    caminho = parsed.path.lower()

    if "noimage" in caminho:
        return False

    return True
