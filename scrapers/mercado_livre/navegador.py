from __future__ import annotations

from playwright.sync_api import Browser, BrowserContext, Page, Playwright

ENDERECO_CDP = "http://127.0.0.1:9222"


def conectar_ao_chrome(
    playwright: Playwright,
    endereco_cdp: str = ENDERECO_CDP,
) -> tuple[Browser, BrowserContext, Page]:
    """
    Conecta ao Google Chrome já aberto com depuração remota.

    O Chrome deve ter sido iniciado com:
    --remote-debugging-port=9222
    """

    browser = playwright.chromium.connect_over_cdp(endereco_cdp)

    if not browser.contexts:
        raise RuntimeError("O Chrome foi encontrado, mas nenhum contexto de navegador está aberto.")

    contexto = browser.contexts[0]

    if not contexto.pages:
        raise RuntimeError("O Chrome foi encontrado, mas nenhuma aba está aberta.")

    pagina = encontrar_pagina_mercado_livre(contexto)

    return browser, contexto, pagina


def encontrar_pagina_mercado_livre(contexto: BrowserContext) -> Page:
    """
    Procura uma aba aberta do Mercado Livre.

    Caso não encontre, utiliza a última aba aberta.
    """

    for pagina in reversed(contexto.pages):
        url = pagina.url.lower()

        if "mercadolivre.com.br" in url:
            return pagina

    return contexto.pages[-1]
