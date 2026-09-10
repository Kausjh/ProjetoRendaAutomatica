import ast
import inspect
import textwrap

from scrapers.mercado_livre_scraper import (
    MercadoLivreScraper,
)


def _arvore_buscar_ofertas():
    fonte = inspect.getsource(MercadoLivreScraper.buscar_ofertas)

    return ast.parse(textwrap.dedent(fonte))


def _close_de(
    arvore,
    nome,
):
    encontrados = []

    for node in ast.walk(arvore):
        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        funcao = node.func

        if not (
            isinstance(
                funcao,
                ast.Attribute,
            )
            and funcao.attr == "close"
            and isinstance(
                funcao.value,
                ast.Name,
            )
            and funcao.value.id == nome
        ):
            continue

        encontrados.append(node)

    return encontrados


def test_mercado_livre_nao_fecha_browser_cdp_compartilhado():
    arvore = _arvore_buscar_ofertas()

    assert (
        _close_de(
            arvore,
            "navegador",
        )
        == []
    )


def test_mercado_livre_continua_fechando_somente_pagina_propria():
    arvore = _arvore_buscar_ofertas()

    closes_pagina = _close_de(
        arvore,
        "pagina",
    )

    assert len(closes_pagina) == 1
