# 63.8738, -149.7525

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from affiliates.afiliador_awin import AfiliadorAwin
from bots.telegram_bot import TelegramBot
from scrapers import registro_scrapers
from services.politica_marketplace import PoliticaMarketplace


def test_kabum_esta_no_registro_de_scrapers(monkeypatch):
    monkeypatch.setattr(
        registro_scrapers,
        "MercadoLivreScraper",
        lambda: "ml",
    )
    monkeypatch.setattr(
        registro_scrapers,
        "ShopeeScraper",
        lambda: "shopee",
    )
    monkeypatch.setattr(
        registro_scrapers,
        "KabumScraper",
        lambda: "kabum",
    )
    monkeypatch.setattr(
        registro_scrapers,
        "AliExpressScraper",
        lambda: "ali",
    )

    assert registro_scrapers.criar_scrapers() == [
        "ml",
        "shopee",
        "kabum",
        "ali",
    ]


def test_kabum_exige_link_afiliado():
    assert TelegramBot._exige_link_afiliado("https://www.kabum.com.br/produto/123")


def test_config_kabum_usa_awin_17729():
    dados = json.loads(Path("config/afiliadores.json").read_text(encoding="utf-8"))

    kabum = next(item for item in dados["afiliadores"] if item["nome"] == "KaBuM!")

    assert kabum["ativo"] is True
    assert kabum["tipo"] == "awin"
    assert kabum["dominios"] == ["kabum.com.br"]
    assert kabum["parametros"]["advertiser_id"] == "17729"


def test_deep_link_kabum_usa_advertiser_correto():
    afiliador = AfiliadorAwin(
        nome="KaBuM!",
        dominios=["kabum.com.br"],
        advertiser_id="17729",
        publisher_id="123456",
    )

    link = afiliador.gerar_link("https://www.kabum.com.br/produto/123")

    partes = urlparse(link)
    parametros = parse_qs(partes.query)

    assert partes.hostname == "www.awin1.com"
    assert parametros["awinmid"] == ["17729"]
    assert parametros["awinaffid"] == ["123456"]
    assert parametros["ued"] == ["https://www.kabum.com.br/produto/123"]


def test_kabum_nao_pode_usar_reserva_de_cold_start():
    assert PoliticaMarketplace.bloqueia_cold_start("kabum") is True

    assert PoliticaMarketplace.bloqueia_cold_start("aliexpress") is False
