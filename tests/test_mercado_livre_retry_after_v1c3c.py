# 63.8738, -149.7525

from types import SimpleNamespace

import pytest

from scrapers.mercado_livre_scraper import MercadoLivreScraper
from services.scout.mercado_livre_catalog_api import (
    ClienteCatalogoMercadoLivre,
    ErroApiMercadoLivre,
)


def _capturar_erro_429(retry_after):
    resposta = SimpleNamespace(
        status_code=429,
        headers={"Retry-After": retry_after},
    )

    with pytest.raises(ErroApiMercadoLivre) as capturado:
        ClienteCatalogoMercadoLivre._validar_status(resposta)

    return capturado.value


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("17", 17),
        ("1", 1),
        ("0", 1),
        ("-5", 1),
    ],
)
def test_retry_after_numerico_e_preservado(valor, esperado):
    erro = _capturar_erro_429(valor)

    assert erro.status_code == 429
    assert erro.transitorio is True
    assert erro.motivo == "api_mercado_livre_rate_limit"
    assert erro.retry_after == esperado


@pytest.mark.parametrize(
    "valor",
    [
        None,
        "",
        "abc",
        "1.5",
    ],
)
def test_retry_after_invalido_vira_none(valor):
    erro = _capturar_erro_429(valor)

    assert erro.retry_after is None


def test_429_sem_header_retry_after_continua_valido():
    resposta = SimpleNamespace(
        status_code=429,
        headers={},
    )

    with pytest.raises(ErroApiMercadoLivre) as capturado:
        ClienteCatalogoMercadoLivre._validar_status(resposta)

    assert capturado.value.retry_after is None


def test_backoff_prioriza_retry_after_e_nao_chama_jitter():
    esperas = []
    chamadas = 0

    def operacao():
        nonlocal chamadas
        chamadas += 1

        if chamadas == 1:
            raise ErroApiMercadoLivre(
                "api_mercado_livre_rate_limit",
                status_code=429,
                transitorio=True,
                retry_after=17,
            )

        return "ok"

    def jitter_nao_deveria_ser_chamado():
        raise AssertionError("jitter nao deve ser usado quando Retry-After existe")

    scraper = MercadoLivreScraper(
        termos_busca=["Ryzen 7"],
        cliente_catalogo=object(),
        sleep_fn=esperas.append,
        jitter_fn=jitter_nao_deveria_ser_chamado,
        tentativas_rate_limit=1,
    )

    resultado = scraper._executar_api_com_backoff(
        operacao,
        descricao="teste_retry_after",
    )

    assert resultado == "ok"
    assert chamadas == 2
    assert esperas == [17.0]
