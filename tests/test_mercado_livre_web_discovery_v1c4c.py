# 63.8738, -149.7525

from __future__ import annotations

import pytest

from services.scout.mercado_livre_web_discovery import (
    ErroDiscoveryMercadoLivre,
    MercadoLivreWebDiscovery,
)


class ElementoFake:
    def __init__(
        self,
        *,
        texto="",
        atributos=None,
        quantidade=1,
    ):
        self.texto = texto
        self.atributos = dict(atributos or {})
        self.quantidade = quantidade

    @property
    def first(self):
        return self

    def count(self):
        return self.quantidade

    def inner_text(
        self,
        timeout=None,
    ):
        return self.texto

    def get_attribute(
        self,
        nome,
    ):
        return self.atributos.get(nome)


class VazioFake(ElementoFake):
    def __init__(self):
        super().__init__(
            quantidade=0,
        )


class CardFake:
    def __init__(
        self,
        titulo,
        link,
    ):
        self.titulo = titulo
        self.link = link

    def locator(
        self,
        seletor,
    ):
        if seletor in (
            "a.poly-component__title",
            "h3.poly-component__title-wrapper a",
            "a.ui-search-item__group__element",
            "a[href*='produto.mercadolivre.com.br']",
            "a[href*='mercadolivre.com.br']",
        ):
            return ElementoFake(
                texto=self.titulo,
                atributos={
                    "href": self.link,
                },
            )

        if seletor in (
            "h3.poly-component__title-wrapper",
            "h2.ui-search-item__title",
            ".ui-search-item__title",
        ):
            return ElementoFake(
                texto=self.titulo,
            )

        return VazioFake()


class ColecaoFake:
    def __init__(
        self,
        cards,
    ):
        self.cards = list(cards)

    def count(self):
        return len(self.cards)

    def nth(
        self,
        indice,
    ):
        return self.cards[indice]


class PaginaFake:
    def __init__(
        self,
        cards=None,
        *,
        titulo="Mercado Livre",
        corpo="Resultados encontrados",
    ):
        self.cards = list(cards or [])
        self.titulo_pagina = titulo
        self.corpo = corpo
        self.url_aberta = None
        self.fechada = False
        self.timeout_padrao = None

    def set_default_timeout(
        self,
        timeout,
    ):
        self.timeout_padrao = timeout

    def goto(
        self,
        url,
        *,
        wait_until,
        timeout,
    ):
        self.url_aberta = url

    def wait_for_load_state(
        self,
        estado,
        *,
        timeout,
    ):
        return None

    def wait_for_selector(
        self,
        seletor,
        *,
        state,
        timeout,
    ):
        return None

    def locator(
        self,
        seletor,
    ):
        if seletor == "body":
            return ElementoFake(
                texto=self.corpo,
            )

        if seletor == "li.ui-search-layout__item":
            return ColecaoFake(
                self.cards,
            )

        return ColecaoFake([])

    def title(self):
        return self.titulo_pagina

    def is_closed(self):
        return self.fechada

    def close(self):
        self.fechada = True


class RespostaHttpFake:
    def __init__(
        self,
        status,
    ):
        self.status = status


class PaginaHttp403Fake(PaginaFake):
    def goto(
        self,
        url,
        *,
        wait_until,
        timeout,
    ):
        self.url_aberta = url

        return RespostaHttpFake(
            403,
        )


class ContextoFake:
    def __init__(
        self,
        pagina,
    ):
        self.pagina = pagina

    def new_page(self):
        return self.pagina


class PlaywrightContextFake:
    def __enter__(self):
        return object()

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False


def _discovery_com_pagina(
    pagina,
):
    contexto = ContextoFake(
        pagina,
    )

    chamadas = []

    def conectar(
        playwright,
        endpoint,
    ):
        chamadas.append(endpoint)

        return (
            object(),
            contexto,
            object(),
        )

    discovery = MercadoLivreWebDiscovery(
        endpoint_cdp="http://127.0.0.1:9222",
        playwright_factory=PlaywrightContextFake,
        conectar_fn=conectar,
    )

    return discovery, chamadas


def test_discovery_extrai_ids_links_e_titulos_sem_rede():
    pagina = PaginaFake(
        [
            CardFake(
                "SSD NVMe 1TB",
                ("https://produto.mercadolivre.com.br/" "MLB-1234567890-ssd-nvme-_JM"),
            ),
            CardFake(
                "SSD NVMe 2TB",
                ("https://www.mercadolivre.com.br/" "ssd-nvme/p/MLB9876543210"),
            ),
        ]
    )

    discovery, chamadas = _discovery_com_pagina(pagina)

    resultados = discovery.descobrir(
        "SSD NVMe",
        limite=2,
    )

    assert [item.identificador_ml for item in resultados] == [
        "MLB1234567890",
        "MLB9876543210",
    ]

    assert [item.titulo for item in resultados] == [
        "SSD NVMe 1TB",
        "SSD NVMe 2TB",
    ]

    assert pagina.url_aberta == ("https://lista.mercadolivre.com.br/" "SSD-NVMe")

    assert pagina.fechada is True

    assert chamadas == ["http://127.0.0.1:9222"]


def test_discovery_remove_identificador_duplicado():
    link = "https://produto.mercadolivre.com.br/" "MLB-1234567890-produto-_JM"

    pagina = PaginaFake(
        [
            CardFake(
                "Produto A",
                link,
            ),
            CardFake(
                "Produto A duplicado",
                link,
            ),
        ]
    )

    discovery, _ = _discovery_com_pagina(pagina)

    resultados = discovery.descobrir(
        "produto",
        limite=5,
    )

    assert len(resultados) == 1

    assert resultados[0].identificador_ml == "MLB1234567890"


def test_discovery_http_403_vira_erro_controlado():
    pagina = PaginaHttp403Fake()

    discovery, _ = _discovery_com_pagina(pagina)

    with pytest.raises(
        ErroDiscoveryMercadoLivre,
        match="mercado_livre_web_http_403",
    ):
        discovery.descobrir(
            "SSD NVMe",
            limite=1,
        )

    assert pagina.fechada is True


def test_discovery_detecta_bloqueio():
    pagina = PaginaFake(
        [],
        titulo="Access denied",
        corpo="atividade incomum",
    )

    discovery, _ = _discovery_com_pagina(pagina)

    with pytest.raises(
        ErroDiscoveryMercadoLivre,
        match="mercado_livre_web_bloqueado",
    ):
        discovery.descobrir(
            "SSD NVMe",
            limite=1,
        )

    assert pagina.fechada is True


@pytest.mark.parametrize(
    ("consulta", "limite"),
    [
        ("", 1),
        ("   ", 1),
        ("SSD", 0),
        ("SSD", -1),
        ("SSD", True),
        ("SSD", 1.5),
    ],
)
def test_discovery_rejeita_entrada_invalida(
    consulta,
    limite,
):
    discovery = MercadoLivreWebDiscovery(
        playwright_factory=PlaywrightContextFake,
    )

    with pytest.raises(ValueError):
        discovery.descobrir(
            consulta,
            limite=limite,
        )
