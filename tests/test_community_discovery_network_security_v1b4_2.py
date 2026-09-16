# 63.8738, -149.7525

from __future__ import annotations

import socket
from types import SimpleNamespace

import pytest

from services.scout import processador_aliexpress_social_scout, processador_kabum_social_scout
from services.scout.seguranca_redirect_http import (
    UrlRedeNaoPermitida,
    resolver_redirects_requests_publicos,
)


class RespostaFake:
    def __init__(
        self,
        *,
        url: str,
        status_code: int,
        location: str | None = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.headers = {}
        self.closed = False

        if location is not None:
            self.headers["Location"] = location

    def close(self) -> None:
        self.closed = True

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def dns_global(host, port, *, type):
    del host, port, type

    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            ("93.184.216.34", 0),
        )
    ]


def test_redirect_publico_bloqueia_ip_privado_antes_do_segundo_http():
    chamadas = []

    def dns(host, port, *, type):
        del port, type

        ip = "127.0.0.1" if host == "interno.example" else "93.184.216.34"

        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (ip, 0),
            )
        ]

    def fake_get(url, **kwargs):
        chamadas.append((url, kwargs))

        return RespostaFake(
            url=url,
            status_code=302,
            location="http://interno.example/admin",
        )

    with pytest.raises(
        UrlRedeNaoPermitida,
        match="ip_nao_global",
    ):
        resolver_redirects_requests_publicos(
            "https://s.click.aliexpress.com/e/teste",
            dominios_iniciais=("aliexpress.com",),
            dominios_finais=("aliexpress.com",),
            timeout_segundos=1,
            http_get=fake_get,
            dns_resolver=dns,
        )

    assert len(chamadas) == 1
    assert chamadas[0][1]["allow_redirects"] is False


def test_redirect_publico_permite_intermediario_publico_e_exige_final():
    respostas = [
        RespostaFake(
            url="https://tidd.ly/abc",
            status_code=302,
            location="https://tracking.example/click",
        ),
        RespostaFake(
            url="https://tracking.example/click",
            status_code=302,
            location=("https://www.kabum.com.br/" "produto/123/produto"),
        ),
        RespostaFake(
            url=("https://www.kabum.com.br/" "produto/123/produto"),
            status_code=200,
        ),
    ]

    chamadas = []

    def fake_get(url, **kwargs):
        chamadas.append((url, kwargs))
        return respostas.pop(0)

    resultado = resolver_redirects_requests_publicos(
        "https://tidd.ly/abc",
        dominios_iniciais=("tidd.ly",),
        dominios_finais=("kabum.com.br",),
        timeout_segundos=1,
        http_get=fake_get,
        dns_resolver=dns_global,
    )

    try:
        assert resultado.url_final == ("https://www.kabum.com.br/" "produto/123/produto")

        assert all(kwargs["allow_redirects"] is False for _, kwargs in chamadas)
    finally:
        resultado.resposta.close()


def test_redirect_publico_rejeita_resposta_final_em_host_publico_errado():
    respostas = [
        RespostaFake(
            url="https://tidd.ly/abc",
            status_code=302,
            location="https://tracking.example/click",
        ),
        RespostaFake(
            url="https://tracking.example/click",
            status_code=200,
        ),
    ]

    def fake_get(url, **kwargs):
        del url, kwargs
        return respostas.pop(0)

    with pytest.raises(
        UrlRedeNaoPermitida,
        match="host_final_fora_da_allowlist",
    ):
        resolver_redirects_requests_publicos(
            "https://tidd.ly/abc",
            dominios_iniciais=("tidd.ly",),
            dominios_finais=("kabum.com.br",),
            timeout_segundos=1,
            http_get=fake_get,
            dns_resolver=dns_global,
        )


def test_resolver_padrao_aliexpress_usa_guard_e_preserva_url_final(
    monkeypatch,
):
    resposta = RespostaFake(
        url=("https://www.aliexpress.com/" "item/1005001234567890.html"),
        status_code=200,
    )

    capturado = {}

    def fake_guard(url, **kwargs):
        capturado["url"] = url
        capturado["kwargs"] = kwargs

        return SimpleNamespace(
            resposta=resposta,
            url_final=resposta.url,
        )

    monkeypatch.setattr(
        processador_aliexpress_social_scout,
        "resolver_redirects_requests_publicos",
        fake_guard,
    )

    destino = (
        processador_aliexpress_social_scout.ProcessadorAliExpressSocialScout._resolver_url_padrao(
            "https://s.click.aliexpress.com/e/teste"
        )
    )

    assert destino == resposta.url
    assert capturado["kwargs"]["dominios_iniciais"] == ("aliexpress.com",)
    assert capturado["kwargs"]["dominios_finais"] == ("aliexpress.com",)
    assert resposta.closed is True


def test_resolver_padrao_kabum_usa_guard_e_exige_final_kabum(
    monkeypatch,
):
    resposta = RespostaFake(
        url=("https://www.kabum.com.br/" "produto/123/produto"),
        status_code=200,
    )

    capturado = {}

    def fake_guard(url, **kwargs):
        capturado["url"] = url
        capturado["kwargs"] = kwargs

        return SimpleNamespace(
            resposta=resposta,
            url_final=resposta.url,
        )

    monkeypatch.setattr(
        processador_kabum_social_scout,
        "resolver_redirects_requests_publicos",
        fake_guard,
    )

    destino = processador_kabum_social_scout.ProcessadorKabumSocialScout._resolver_url_padrao(
        "https://tidd.ly/teste"
    )

    assert destino == resposta.url
    assert capturado["kwargs"]["dominios_iniciais"] == ("tidd.ly",)
    assert capturado["kwargs"]["dominios_finais"] == ("kabum.com.br",)
    assert resposta.closed is True
