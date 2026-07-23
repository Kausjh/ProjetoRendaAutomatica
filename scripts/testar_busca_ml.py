import re
from typing import Iterable

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


ENDERECO_CDP = "http://127.0.0.1:9222"
TERMO_PESQUISA = "Ryzen 7 5700X"


def obter_contexto(browser: Browser) -> BrowserContext:
    """Retorna o contexto principal do Chrome conectado."""

    contextos = browser.contexts

    if not contextos:
        raise RuntimeError(
            "O Chrome conectado não possui nenhum contexto disponível."
        )

    return contextos[0]


def listar_paginas(contexto: BrowserContext) -> None:
    """Mostra as páginas atualmente abertas no Chrome dedicado."""

    print()
    print("Páginas encontradas no Chrome:")
    print()

    for indice, pagina in enumerate(contexto.pages, start=1):
        try:
            titulo = pagina.title()
        except Exception:
            titulo = "Título indisponível"

        print(f"[{indice}] {titulo}")
        print(f"    {pagina.url}")


def escolher_pagina_mercado_livre(
    contexto: BrowserContext,
) -> Page:
    """
    Escolhe uma página aberta do Mercado Livre.

    Dá preferência para páginas que aparentem pertencer
    ao painel de afiliados.
    """

    paginas_ml: list[Page] = []

    for pagina in contexto.pages:
        url = pagina.url.lower()

        if (
            "mercadolivre.com.br" in url
            or "mercadolibre.com" in url
        ):
            paginas_ml.append(pagina)

    if not paginas_ml:
        raise RuntimeError(
            "Nenhuma página do Mercado Livre foi encontrada.\n"
            "Abra o painel de afiliados no Chrome dedicado "
            "e execute o teste novamente."
        )

    palavras_afiliacao = (
        "afili",
        "partner",
        "creator",
        "monetiza",
    )

    for pagina in paginas_ml:
        url = pagina.url.lower()

        if any(
            palavra in url
            for palavra in palavras_afiliacao
        ):
            return pagina

    return paginas_ml[-1]


def locator_utilizavel(locator: Locator) -> bool:
    """Verifica se um locator aponta para um campo utilizável."""

    try:
        if locator.count() == 0:
            return False

        elemento = locator.first

        return (
            elemento.is_visible()
            and elemento.is_enabled()
        )

    except Exception:
        return False


def candidatos_campo_busca(
    pagina: Page,
) -> Iterable[tuple[str, Locator]]:
    """
    Retorna estratégias de localização do campo de pesquisa.

    Os seletores mais semânticos são tentados primeiro.
    """

    padrao_busca = re.compile(
        r"buscar|busca|pesquisar|pesquisa|produto",
        re.IGNORECASE,
    )

    yield (
        "campo por placeholder",
        pagina.get_by_placeholder(padrao_busca),
    )

    yield (
        "campo por nome acessível",
        pagina.get_by_role(
            "textbox",
            name=padrao_busca,
        ),
    )

    yield (
        "input do tipo search",
        pagina.locator('input[type="search"]'),
    )

    yield (
        "input com placeholder relacionado a busca",
        pagina.locator(
            'input[placeholder*="bus" i], '
            'input[placeholder*="pesq" i], '
            'input[placeholder*="produto" i]'
        ),
    )

    yield (
        "campo de texto visível",
        pagina.locator(
            'input[type="text"]:visible'
        ),
    )


def encontrar_campo_busca(
    pagina: Page,
) -> tuple[str, Locator]:
    """Localiza o campo de pesquisa do painel."""

    for descricao, locator in candidatos_campo_busca(pagina):
        if locator_utilizavel(locator):
            return descricao, locator.first

    raise RuntimeError(
        "Não foi possível localizar automaticamente "
        "o campo de pesquisa do painel."
    )


def mostrar_campos_visiveis(pagina: Page) -> None:
    """
    Mostra informações dos inputs visíveis.

    Isso serve como diagnóstico caso o campo de pesquisa
    não seja encontrado automaticamente.
    """

    print()
    print("Diagnóstico dos campos visíveis:")
    print()

    inputs = pagina.locator("input:visible")
    quantidade = inputs.count()

    if quantidade == 0:
        print("Nenhum input visível foi encontrado.")
        return

    for indice in range(quantidade):
        input_atual = inputs.nth(indice)

        try:
            tipo = input_atual.get_attribute("type")
            nome = input_atual.get_attribute("name")
            placeholder = input_atual.get_attribute(
                "placeholder"
            )
            aria_label = input_atual.get_attribute(
                "aria-label"
            )

            print(f"Input {indice + 1}:")
            print(f"  type: {tipo}")
            print(f"  name: {nome}")
            print(f"  placeholder: {placeholder}")
            print(f"  aria-label: {aria_label}")
            print()

        except Exception as erro:
            print(
                f"Não foi possível analisar o input "
                f"{indice + 1}: {erro}"
            )


def executar_busca(
    pagina: Page,
    termo: str,
) -> None:
    """Preenche o campo de pesquisa e executa a busca."""

    pagina.bring_to_front()

    try:
        pagina.wait_for_load_state(
            "domcontentloaded",
            timeout=20_000,
        )
    except PlaywrightTimeoutError:
        print()
        print(
            "Aviso: a página não informou o término do "
            "carregamento, mas o teste continuará."
        )

    descricao, campo = encontrar_campo_busca(pagina)

    print()
    print(f"Campo encontrado usando: {descricao}")
    print(f"Pesquisando: {termo}")

    campo.click()
    campo.fill(termo)
    campo.press("Enter")

    print()
    print("Busca enviada. Aguardando atualização da página...")

    pagina.wait_for_timeout(5_000)

    print()
    print("Resultado do teste:")
    print(f"URL atual: {pagina.url}")

    try:
        print(f"Título atual: {pagina.title()}")
    except Exception:
        print("Título atual: indisponível")

    botoes_compartilhar = pagina.get_by_role(
        "button",
        name=re.compile(
            r"compartilhar",
            re.IGNORECASE,
        ),
    )

    links_compartilhar = pagina.get_by_text(
        re.compile(
            r"compartilhar",
            re.IGNORECASE,
        ),
        exact=False,
    )

    quantidade_botoes = botoes_compartilhar.count()
    quantidade_textos = links_compartilhar.count()

    print(
        "Elementos encontrados com o texto "
        f"'Compartilhar': {max(quantidade_botoes, quantidade_textos)}"
    )

    if quantidade_botoes > 0 or quantidade_textos > 0:
        print()
        print(
            "SUCESSO: a pesquisa foi executada e foram "
            "encontrados elementos de compartilhamento."
        )
    else:
        print()
        print(
            "A busca foi enviada, mas nenhum botão "
            "'Compartilhar' foi localizado ainda."
        )
        print(
            "Observe a janela do Chrome para confirmar "
            "se os resultados apareceram."
        )


def executar_teste(playwright: Playwright) -> None:
    """Conecta ao Chrome e testa a busca no Mercado Livre."""

    print("=" * 60)
    print("Teste de busca no painel de afiliados do Mercado Livre")
    print("=" * 60)
    print()
    print(f"Conectando ao Chrome em: {ENDERECO_CDP}")

    browser = playwright.chromium.connect_over_cdp(
        ENDERECO_CDP,
        timeout=30_000,
    )

    contexto = obter_contexto(browser)

    listar_paginas(contexto)

    pagina = escolher_pagina_mercado_livre(contexto)

    print()
    print("Página escolhida:")
    print(pagina.url)

    try:
        executar_busca(
            pagina=pagina,
            termo=TERMO_PESQUISA,
        )

    except Exception:
        mostrar_campos_visiveis(pagina)
        raise

    print()
    input(
        "Pressione ENTER para encerrar o teste. "
        "O Chrome dedicado permanecerá aberto..."
    )


def main() -> None:
    try:
        with sync_playwright() as playwright:
            executar_teste(playwright)

    except Exception as erro:
        print()
        print("=" * 60)
        print("FALHA NO TESTE")
        print("=" * 60)
        print()
        print(f"Tipo: {type(erro).__name__}")
        print(f"Detalhes: {erro}")
        print()
        print(
            "Mantenha o Chrome dedicado aberto e deixe "
            "o painel de afiliados visível antes de testar."
        )
        raise


if __name__ == "__main__":
    main()