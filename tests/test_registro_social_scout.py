# 63.8738, -149.7525

from pathlib import Path

import pytest

from scrapers import registro_scrapers


def preparar_construtores(
    monkeypatch,
):
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

    monkeypatch.setattr(
        registro_scrapers,
        "SocialScoutScraper",
        lambda: "social",
    )


def test_social_scout_desativado_por_padrao(
    monkeypatch,
):
    preparar_construtores(monkeypatch)

    monkeypatch.delenv(
        "SOCIAL_SCOUT_PIPELINE_ATIVO",
        raising=False,
    )

    assert registro_scrapers.criar_scrapers() == [
        "ml",
        "shopee",
        "kabum",
        "ali",
    ]


@pytest.mark.parametrize(
    "valor",
    [
        "1",
        "true",
        "TRUE",
        "sim",
        "yes",
        "on",
    ],
)
def test_social_scout_ativa_somente_com_valor_explicito(
    monkeypatch,
    valor,
):
    preparar_construtores(monkeypatch)

    monkeypatch.setenv(
        "SOCIAL_SCOUT_PIPELINE_ATIVO",
        valor,
    )

    assert registro_scrapers.criar_scrapers() == [
        "ml",
        "shopee",
        "kabum",
        "ali",
        "social",
    ]


@pytest.mark.parametrize(
    "valor",
    [
        "",
        "0",
        "false",
        "nao",
        "n?o",
        "no",
        "off",
        "qualquer-coisa",
    ],
)
def test_social_scout_permanece_desativado(
    monkeypatch,
    valor,
):
    preparar_construtores(monkeypatch)

    monkeypatch.setenv(
        "SOCIAL_SCOUT_PIPELINE_ATIVO",
        valor,
    )

    assert registro_scrapers.criar_scrapers() == [
        "ml",
        "shopee",
        "kabum",
        "ali",
    ]


def test_env_example_documenta_flag_desativada():
    texto = Path(".env.example").read_text(
        encoding="utf-8",
    )

    assert "SOCIAL_SCOUT_PIPELINE_ATIVO=false" in texto
