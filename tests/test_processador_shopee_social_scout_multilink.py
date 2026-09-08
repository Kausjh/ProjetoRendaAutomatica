# 63.8738, -149.7525

import requests

from services.scout.processador_shopee_social_scout import (
    ProcessadorShopeeSocialScout,
)


def _processador():
    return ProcessadorShopeeSocialScout(service=object())


def test_multilink_tenta_produto_apos_link_de_cupom(
    monkeypatch,
):
    processador = _processador()

    cupom = "https://s.shopee.com.br/cupom"

    produto = "https://s.shopee.com.br/produto"

    identidade = (
        "627750190",
        "58211665704",
    )

    def resolver(link):
        if link == cupom:
            return (
                None,
                "shopee_identidade_nao_resolvida",
            )

        assert link == produto

        return (
            identidade,
            "identidade_shopee_redirect",
        )

    monkeypatch.setattr(
        processador,
        "_resolver_identidade_link",
        resolver,
    )

    resultado = processador._resolver_identidade_links(
        [
            cupom,
            produto,
        ]
    )

    assert resultado == (
        identidade,
        produto,
        "identidade_shopee_link_mensagem",
    )


def test_multilink_rejeita_produtos_diferentes(
    monkeypatch,
):
    processador = _processador()

    respostas = {
        "https://s.shopee.com.br/a": (
            (
                "111",
                "222",
            ),
            "identidade_shopee_redirect",
        ),
        "https://s.shopee.com.br/b": (
            (
                "333",
                "444",
            ),
            "identidade_shopee_redirect",
        ),
    }

    monkeypatch.setattr(
        processador,
        "_resolver_identidade_link",
        lambda link: respostas[link],
    )

    assert processador._resolver_identidade_links(list(respostas)) == (
        None,
        None,
        "shopee_identidade_ambigua",
    )


def test_multilink_aceita_mesma_identidade_repetida(
    monkeypatch,
):
    processador = _processador()

    identidade = (
        "111",
        "222",
    )

    monkeypatch.setattr(
        processador,
        "_resolver_identidade_link",
        lambda link: (
            identidade,
            "identidade_shopee_redirect",
        ),
    )

    primeiro = "https://s.shopee.com.br/a"

    segundo = "https://s.shopee.com.br/b"

    assert processador._resolver_identidade_links(
        [
            primeiro,
            segundo,
        ]
    ) == (
        identidade,
        primeiro,
        "identidade_shopee_link_mensagem",
    )


def test_multilink_falha_fechado_em_erro_transitorio(
    monkeypatch,
):
    processador = _processador()

    primeiro = "https://s.shopee.com.br/a"

    segundo = "https://s.shopee.com.br/b"

    def resolver(link):
        if link == primeiro:
            raise requests.RequestException("falha temporaria")

        return (
            (
                "111",
                "222",
            ),
            "identidade_shopee_redirect",
        )

    monkeypatch.setattr(
        processador,
        "_resolver_identidade_link",
        resolver,
    )

    assert processador._resolver_identidade_links(
        [
            primeiro,
            segundo,
        ]
    ) == (
        None,
        None,
        "falha_resolucao_link_shopee",
    )


def test_multilink_sem_identidade_continua_nao_resolvido(
    monkeypatch,
):
    processador = _processador()

    monkeypatch.setattr(
        processador,
        "_resolver_identidade_link",
        lambda link: (
            None,
            "shopee_identidade_nao_resolvida",
        ),
    )

    assert processador._resolver_identidade_links(
        [
            "https://s.shopee.com.br/a",
            "https://s.shopee.com.br/b",
        ]
    ) == (
        None,
        None,
        "shopee_identidade_nao_resolvida",
    )
