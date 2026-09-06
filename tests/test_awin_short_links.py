from __future__ import annotations

from unittest.mock import Mock, patch

import requests

from affiliates.afiliador_awin import AfiliadorAwin
from repositories.links_afiliados_awin_repository import (
    LinksAfiliadosAwinRepository,
)


def criar_afiliador(
    tmp_path,
    api_token: str = "token-de-teste",
) -> AfiliadorAwin:
    repository = LinksAfiliadosAwinRepository(tmp_path / "awin.sqlite3")

    return AfiliadorAwin(
        nome="KaBuM!",
        dominios=["kabum.com.br"],
        advertiser_id="17729",
        publisher_id="123456",
        api_token=api_token,
        repository=repository,
        timeout_segundos=1,
    )


def resposta_sucesso() -> Mock:
    resposta = Mock()
    resposta.ok = True
    resposta.status_code = 200
    resposta.json.return_value = {
        "url": ("https://www.awin1.com/" "cread.php?tracking=teste"),
        "shortUrl": "https://tidd.ly/teste123",
    }
    return resposta


def test_gera_short_link_oficial_awin(
    tmp_path,
) -> None:
    afiliador = criar_afiliador(tmp_path)

    destino = "https://www.kabum.com.br/" "produto/123"

    with patch(
        "affiliates.afiliador_awin.requests.post",
        return_value=resposta_sucesso(),
    ) as post:
        resultado = afiliador.gerar_link(destino)

    assert resultado == ("https://tidd.ly/teste123")

    argumentos = post.call_args.kwargs

    assert argumentos["json"] == {
        "advertiserId": 17729,
        "destinationUrl": destino,
        "shorten": True,
    }


def test_reutiliza_short_link_do_cache(
    tmp_path,
) -> None:
    afiliador = criar_afiliador(tmp_path)

    destino = "https://www.kabum.com.br/" "produto/456"

    with patch(
        "affiliates.afiliador_awin.requests.post",
        return_value=resposta_sucesso(),
    ) as post:
        primeiro = afiliador.gerar_link(destino)
        segundo = afiliador.gerar_link(destino)

    assert primeiro == segundo
    assert primeiro == ("https://tidd.ly/teste123")
    assert post.call_count == 1


def test_cache_persiste_entre_instancias(
    tmp_path,
) -> None:
    destino = "https://www.kabum.com.br/" "produto/789"

    primeiro = criar_afiliador(tmp_path)

    with patch(
        "affiliates.afiliador_awin.requests.post",
        return_value=resposta_sucesso(),
    ):
        resultado_primeiro = primeiro.gerar_link(destino)

    segundo = criar_afiliador(tmp_path)

    with patch(
        "affiliates.afiliador_awin.requests.post",
    ) as post:
        resultado_segundo = segundo.gerar_link(destino)

    assert resultado_primeiro == resultado_segundo == "https://tidd.ly/teste123"
    post.assert_not_called()


def test_sem_token_mantem_link_awin_longo(
    tmp_path,
) -> None:
    afiliador = criar_afiliador(
        tmp_path,
        api_token="",
    )

    with patch(
        "affiliates.afiliador_awin.requests.post",
    ) as post:
        resultado = afiliador.gerar_link("https://www.kabum.com.br/" "produto/321")

    assert resultado.startswith("https://www.awin1.com/cread.php?")
    assert "awinmid=17729" in resultado
    assert "awinaffid=123456" in resultado

    post.assert_not_called()


def test_falha_da_api_mantem_link_awin_longo(
    tmp_path,
) -> None:
    afiliador = criar_afiliador(tmp_path)

    with patch(
        "affiliates.afiliador_awin.requests.post",
        side_effect=requests.RequestException("falha simulada"),
    ):
        resultado = afiliador.gerar_link("https://www.kabum.com.br/" "produto/654")

    assert resultado.startswith("https://www.awin1.com/cread.php?")


def test_short_link_de_dominio_invalido_e_rejeitado(
    tmp_path,
) -> None:
    afiliador = criar_afiliador(tmp_path)

    resposta = resposta_sucesso()

    resposta.json.return_value["shortUrl"] = "https://exemplo.com/nao-aceitar"

    with patch(
        "affiliates.afiliador_awin.requests.post",
        return_value=resposta,
    ):
        resultado = afiliador.gerar_link("https://www.kabum.com.br/" "produto/987")

    assert resultado.startswith("https://www.awin1.com/cread.php?")
