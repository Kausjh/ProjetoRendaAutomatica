from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)


ENDERECO_CDP = "http://127.0.0.1:9222"


def obter_contexto(browser: Browser) -> BrowserContext:
    """Retorna o contexto padrão do Chrome conectado."""

    contextos = browser.contexts

    if not contextos:
        raise RuntimeError(
            "O Chrome conectado não possui nenhum contexto disponível."
        )

    return contextos[0]


def obter_pagina(contexto: BrowserContext) -> Page:
    """Retorna uma página existente ou cria uma nova."""

    paginas = contexto.pages

    if paginas:
        return paginas[0]

    return contexto.new_page()


def executar_teste(playwright: Playwright) -> None:
    print("=" * 60)
    print("Teste de conexão com o Chrome por CDP")
    print("=" * 60)
    print()
    print(f"Conectando em: {ENDERECO_CDP}")

    browser = playwright.chromium.connect_over_cdp(
        ENDERECO_CDP,
        timeout=30_000,
    )

    try:
        contexto = obter_contexto(browser)
        pagina = obter_pagina(contexto)

        print()
        print("Conexão realizada com sucesso.")
        print(f"Quantidade de páginas abertas: {len(contexto.pages)}")
        print(f"Página atual: {pagina.url}")

        try:
            titulo = pagina.title()
        except Exception:
            titulo = "Não foi possível ler o título."

        print(f"Título: {titulo}")
        print()
        print(
            "O Playwright está conectado ao Chrome que você abriu "
            "manualmente."
        )
        print()
        input("Pressione ENTER para encerrar o teste...")

    finally:
        browser.close()


def main() -> None:
    try:
        with sync_playwright() as playwright:
            executar_teste(playwright)

    except Exception as erro:
        print()
        print("Falha ao conectar ao Chrome.")
        print()
        print(f"Tipo: {type(erro).__name__}")
        print(f"Detalhes: {erro}")
        print()
        print(
            "Confirme que o Chrome foi aberto com a porta 9222 "
            "e continua em execução."
        )
        raise


if __name__ == "__main__":
    main()