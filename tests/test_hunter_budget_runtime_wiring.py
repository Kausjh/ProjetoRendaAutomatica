from __future__ import annotations

import ast
from pathlib import Path

import pytest

from config.hunter_budget_config import (
    DEFAULT_LIMITES_HUNTER_POR_FONTE,
    VARIAVEIS_LIMITE_HUNTER,
    carregar_limites_hunter_por_fonte,
)
from services.classificador_produto import (
    ClassificadorProduto,
)
from services.coletor_ofertas import (
    ColetorOfertas,
)

PROFILE_ESPERADO = {
    "MercadoLivreScraper": 10,
    "ShopeeScraper": 10,
    "KabumScraper": 10,
    "AliExpressScraper": 5,
    "SocialScoutScraper": 5,
}


def _limpar_variaveis(
    monkeypatch,
):
    for variavel in VARIAVEIS_LIMITE_HUNTER.values():
        monkeypatch.delenv(
            variavel,
            raising=False,
        )


def test_profile_padrao_e_o_validado_no_canario_real(
    monkeypatch,
):
    _limpar_variaveis(monkeypatch)

    assert DEFAULT_LIMITES_HUNTER_POR_FONTE == PROFILE_ESPERADO

    assert carregar_limites_hunter_por_fonte() == PROFILE_ESPERADO


def test_profile_aceita_override_por_variavel_de_ambiente(
    monkeypatch,
):
    _limpar_variaveis(monkeypatch)

    monkeypatch.setenv(
        "HUNTER_LIMITE_MERCADO_LIVRE",
        "7",
    )

    limites = carregar_limites_hunter_por_fonte()

    assert limites["MercadoLivreScraper"] == 7

    assert limites["ShopeeScraper"] == 10


def test_profile_rejeita_valor_nao_inteiro(
    monkeypatch,
):
    _limpar_variaveis(monkeypatch)

    monkeypatch.setenv(
        "HUNTER_LIMITE_KABUM",
        "abc",
    )

    with pytest.raises(
        ValueError,
        match="HUNTER_LIMITE_KABUM",
    ):
        carregar_limites_hunter_por_fonte()


def test_profile_rejeita_limite_nao_positivo(
    monkeypatch,
):
    _limpar_variaveis(monkeypatch)

    monkeypatch.setenv(
        "HUNTER_LIMITE_SHOPEE",
        "0",
    )

    with pytest.raises(
        ValueError,
        match="HUNTER_LIMITE_SHOPEE",
    ):
        carregar_limites_hunter_por_fonte()


class FonteA:
    def __init__(
        self,
    ):
        self.limites = []

    def buscar_ofertas(
        self,
        limite=5,
    ):
        self.limites.append(limite)

        return []


class FonteB:
    def __init__(
        self,
    ):
        self.limites = []

    def buscar_ofertas(
        self,
        limite=5,
    ):
        self.limites.append(limite)

        return []


def test_coletor_prefere_budget_por_fonte_ao_global():
    fonte_a = FonteA()
    fonte_b = FonteB()

    coletor = ColetorOfertas(
        scrapers=[
            fonte_a,
            fonte_b,
        ],
        classificador=ClassificadorProduto(),
        limites_hunter_por_fonte={
            "FonteA": 2,
            "FonteB": 3,
        },
    )

    assert coletor.buscar_ofertas(limite_por_scraper=40) == []

    assert fonte_a.limites == [2]

    assert fonte_b.limites == [3]


def test_main_entrega_profile_ao_coletor():
    fonte = Path("main.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(fonte)

    cargas = [
        node
        for node in ast.walk(arvore)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Name,
        )
        and node.func.id == "carregar_limites_hunter_por_fonte"
    ]

    assert len(cargas) == 1

    coletores = [
        node
        for node in ast.walk(arvore)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Name,
        )
        and node.func.id == "ColetorOfertas"
    ]

    assert len(coletores) == 1

    keywords = {item.arg: item.value for item in coletores[0].keywords}

    assert "limites_hunter_por_fonte" in keywords

    valor = keywords["limites_hunter_por_fonte"]

    assert isinstance(
        valor,
        ast.Name,
    )

    assert valor.id == "limites_hunter_por_fonte"


def test_env_example_documenta_todos_os_budgets():
    texto = Path(".env.example").read_text(encoding="utf-8-sig")

    for variavel in VARIAVEIS_LIMITE_HUNTER.values():
        assert f"{variavel}=" in texto
