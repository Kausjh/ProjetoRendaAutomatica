# 63.8738, -149.7525

from __future__ import annotations

from types import SimpleNamespace

import pytest

from models.mensagem_social_scout import MensagemSocialScout
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from services.scout.seguranca_redirect_http import (
    UrlRedeNaoPermitida,
    resolver_redirects_requests,
    validar_url_http_permitida,
)
from services.scout.social_scout_destino_resolver import (
    ResolvedorDestinoSocialScout,
)


class RespostaFake:
    def __init__(
        self,
        *,
        url: str,
        status_code: int,
        location: str | None = None,
        text: str = "",
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.headers = {}
        self.text = text
        self.closed = False

        if location is not None:
            self.headers["Location"] = location

    def close(self) -> None:
        self.closed = True

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_guard_rejeita_host_fora_da_allowlist():
    with pytest.raises(UrlRedeNaoPermitida):
        validar_url_http_permitida(
            "http://127.0.0.1/admin",
            dominios_permitidos=("meli.la",),
        )


def test_guard_rejeita_credenciais_e_porta_nao_padrao():
    with pytest.raises(UrlRedeNaoPermitida):
        validar_url_http_permitida(
            "https://usuario:senha@meli.la/x",
            dominios_permitidos=("meli.la",),
        )

    with pytest.raises(UrlRedeNaoPermitida):
        validar_url_http_permitida(
            "https://meli.la:8080/x",
            dominios_permitidos=("meli.la",),
        )


def test_guard_nao_segue_redirect_para_host_nao_permitido():
    chamadas = []

    def fake_get(url, **kwargs):
        chamadas.append((url, kwargs))
        return RespostaFake(
            url=url,
            status_code=302,
            location="http://127.0.0.1/admin",
        )

    with pytest.raises(UrlRedeNaoPermitida):
        resolver_redirects_requests(
            "https://meli.la/abc",
            dominios_permitidos=(
                "meli.la",
                "mercadolivre.com.br",
            ),
            timeout_segundos=1,
            http_get=fake_get,
        )

    assert len(chamadas) == 1
    assert chamadas[0][1]["allow_redirects"] is False


def test_guard_segue_redirect_somente_dentro_da_allowlist():
    respostas = [
        RespostaFake(
            url="https://meli.la/abc",
            status_code=302,
            location="https://www.mercadolivre.com.br/MLB-123",
        ),
        RespostaFake(
            url="https://www.mercadolivre.com.br/MLB-123",
            status_code=200,
        ),
    ]

    chamadas = []

    def fake_get(url, **kwargs):
        chamadas.append((url, kwargs))
        return respostas.pop(0)

    resultado = resolver_redirects_requests(
        "https://meli.la/abc",
        dominios_permitidos=(
            "meli.la",
            "mercadolivre.com.br",
        ),
        timeout_segundos=1,
        http_get=fake_get,
    )

    try:
        assert resultado.url_final == ("https://www.mercadolivre.com.br/MLB-123")
        assert resultado.urls_visitadas == (
            "https://meli.la/abc",
            "https://www.mercadolivre.com.br/MLB-123",
        )
        assert all(kwargs["allow_redirects"] is False for _, kwargs in chamadas)
    finally:
        resultado.resposta.close()


class IdentificadorFake:
    def identificar(self, url):
        del url
        return SimpleNamespace(
            id_produto="MLB1234567890",
            id_anuncio="MLB1234567890",
        )


def _mensagem():
    return MensagemSocialScout(
        fonte="community_discovery",
        chat_id="conta_teste",
        message_id=123,
        chat_titulo="Community Discovery",
        texto="https://meli.la/social123",
        links=("https://meli.la/social123",),
    )


def _deteccao(*, titulo: str, motivo: str):
    return ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo=titulo,
        marketplace="mercado_livre",
        links=("https://meli.la/social123",),
        motivo=motivo,
    )


def test_link_only_comunitario_nao_exige_titulo_social_de_origem():
    resolvedor = ResolvedorDestinoSocialScout(
        identificador_mercado_livre=IdentificadorFake(),
    )

    resolvedor._extrair_cards_destacados = lambda conteudo: (
        "https://www.mercadolivre.com.br/MLB-1234567890-produto",
    )

    resultado = resolvedor._classificar_pagina_social(
        mensagem=_mensagem(),
        deteccao=_deteccao(
            titulo="",
            motivo="community_discovery_link_only",
        ),
        url_original="https://meli.la/social123",
        url_social="https://www.mercadolivre.com.br/social/teste",
        conteudo=('<meta property="og:title" ' 'content="Produto oficial Mercado Livre">'),
        http_status=200,
    )

    assert resultado.status == "resolvido"
    assert resultado.id_produto == "MLB1234567890"


def test_social_scout_normal_preserva_protecao_titulo_divergente():
    resolvedor = ResolvedorDestinoSocialScout(
        identificador_mercado_livre=IdentificadorFake(),
    )

    resultado = resolvedor._classificar_pagina_social(
        mensagem=_mensagem(),
        deteccao=_deteccao(
            titulo="Notebook Gamer RTX",
            motivo="oferta_social_detectada",
        ),
        url_original="https://meli.la/social123",
        url_social="https://www.mercadolivre.com.br/social/teste",
        conteudo=('<meta property="og:title" ' 'content="Geladeira Frost Free">'),
        http_status=200,
    )

    assert resultado.status == "nao_suportado"
    assert resultado.motivo == "pagina_social_titulo_divergente"
