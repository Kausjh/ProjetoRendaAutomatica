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
        lambda **_: "social",
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


def test_social_scout_entra_em_sombra_por_padrao(
    monkeypatch,
):
    preparar_construtores(monkeypatch)

    capturado = {}

    def criar_social(
        **kwargs,
    ):
        capturado.update(kwargs)

        return "social"

    monkeypatch.setattr(
        registro_scrapers,
        "SocialScoutScraper",
        criar_social,
    )

    monkeypatch.setenv(
        "SOCIAL_SCOUT_PIPELINE_ATIVO",
        "true",
    )

    monkeypatch.delenv(
        "SOCIAL_SCOUT_MODO_SOMBRA",
        raising=False,
    )

    scrapers = registro_scrapers.criar_scrapers()

    assert scrapers[-1] == "social"

    assert capturado["modo_sombra"] is True


def test_social_scout_pode_sair_da_sombra_explicitamente(
    monkeypatch,
):
    preparar_construtores(monkeypatch)

    capturado = {}

    def criar_social(
        **kwargs,
    ):
        capturado.update(kwargs)

        return "social"

    monkeypatch.setattr(
        registro_scrapers,
        "SocialScoutScraper",
        criar_social,
    )

    monkeypatch.setenv(
        "SOCIAL_SCOUT_PIPELINE_ATIVO",
        "true",
    )

    monkeypatch.setenv(
        "SOCIAL_SCOUT_MODO_SOMBRA",
        "false",
    )

    registro_scrapers.criar_scrapers()

    assert capturado["modo_sombra"] is False


def test_valor_invalido_de_sombra_falha_para_sombra(
    monkeypatch,
):
    preparar_construtores(monkeypatch)

    capturado = {}

    def criar_social(
        **kwargs,
    ):
        capturado.update(kwargs)

        return "social"

    monkeypatch.setattr(
        registro_scrapers,
        "SocialScoutScraper",
        criar_social,
    )

    monkeypatch.setenv(
        "SOCIAL_SCOUT_PIPELINE_ATIVO",
        "true",
    )

    monkeypatch.setenv(
        "SOCIAL_SCOUT_MODO_SOMBRA",
        "valor-invalido",
    )

    registro_scrapers.criar_scrapers()

    assert capturado["modo_sombra"] is True


def test_env_example_documenta_modo_sombra_seguro():
    texto = Path(".env.example").read_text(
        encoding="utf-8",
    )

    assert "SOCIAL_SCOUT_MODO_SOMBRA=true" in texto
