# 63.8738, -149.7525

import json
from pathlib import Path

from playwright.sync_api import (
    Error as PlaywrightError,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.sync_api import (
    sync_playwright,
)

ENDPOINT_CDP = "http://127.0.0.1:9222"

URL_BUSCA = "https://www.kabum.com.br/busca/Ryzen%207"

ID_PRODUTO = "1053828"

SELETOR_CARD = (
    f'a[href^="/produto/{ID_PRODUTO}/"], '
    f'a[href="/produto/{ID_PRODUTO}"], '
    f'a[href*="/produto/{ID_PRODUTO}/"]'
)

PASTA_SAIDA = Path(r"C:\Projetos\ProjetoRendaAutomatica\diagnosticos")

ARQUIVO_HTML = PASTA_SAIDA / "kabum_5800x3d_card.html"
ARQUIVO_JSON = PASTA_SAIDA / "kabum_5800x3d_diagnostico.json"


def imprimir_titulo(titulo: str) -> None:
    print()
    print("=" * 100)
    print(titulo)
    print("=" * 100)


def imprimir_elementos(
    titulo: str,
    elementos: list[dict],
) -> None:
    imprimir_titulo(titulo)

    if not elementos:
        print("Nenhum elemento encontrado.")
        return

    for indice, elemento in enumerate(
        elementos,
        start=1,
    ):
        print()
        print("-" * 100)
        print(f"ELEMENTO {indice}")
        print("-" * 100)

        print(f"Tag: {elemento.get('tag')}")
        print(f"Texto: {elemento.get('texto')!r}")
        print(f"Classe: {elemento.get('classe')!r}")
        print(f"Oculto: {elemento.get('oculto')}")
        print(f"Display: {elemento.get('display')!r}")
        print(f"Visibility: {elemento.get('visibility')!r}")
        print(f"Opacity: {elemento.get('opacity')!r}")
        print(f"Text decoration: {elemento.get('textDecoration')!r}")
        print(f"Aria-hidden: {elemento.get('ariaHidden')!r}")
        print(f"OuterHTML: {elemento.get('outerHTML')}")


def main() -> None:
    print()
    print("INICIANDO DIAGNÓSTICO DO CARD DO RYZEN 7 5800X3D...")
    print()

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with sync_playwright() as playwright:
            navegador = playwright.chromium.connect_over_cdp(
                ENDPOINT_CDP,
                timeout=30000,
            )

            if navegador.contexts:
                contexto = navegador.contexts[0]
            else:
                contexto = navegador.new_context(
                    locale="pt-BR",
                )

            pagina = contexto.new_page()
            pagina.set_default_timeout(15000)

            try:
                print(f"Abrindo busca da KaBuM!: {URL_BUSCA}")

                pagina.goto(
                    URL_BUSCA,
                    wait_until="domcontentloaded",
                    timeout=45000,
                )

            except PlaywrightTimeoutError:
                print("A página demorou para carregar, " "mas o diagnóstico continuará.")

            pagina.wait_for_selector(
                'a[href^="/produto/"]',
                state="attached",
                timeout=20000,
            )

            pagina.wait_for_timeout(3000)

            cards_encontrados = pagina.locator(SELETOR_CARD).count()

            imprimir_titulo("LOCALIZAÇÃO DO CARD")

            print(f"ID procurado: {ID_PRODUTO}")

            print(f"Seletor utilizado: {SELETOR_CARD}")

            print(f"Cards encontrados: {cards_encontrados}")

            if cards_encontrados == 0:
                print()
                print("O card do produto não foi encontrado.")

                print("Confira se o produto ainda aparece " "na busca por Ryzen 7.")

                return

            card = pagina.locator(SELETOR_CARD).first

            dados = card.evaluate(
                """
                (card) => {
                    const analisarElemento = (elemento) => {
                        const estilo = window.getComputedStyle(
                            elemento
                        );

                        const retangulo = elemento
                            .getBoundingClientRect();

                        const oculto = (
                            estilo.display === "none"
                            || estilo.visibility === "hidden"
                            || estilo.opacity === "0"
                            || retangulo.width === 0
                            || retangulo.height === 0
                        );

                        return {
                            tag: elemento.tagName,
                            texto: (
                                elemento.innerText
                                || elemento.textContent
                                || ""
                            )
                                .replace(/\\s+/g, " ")
                                .trim(),

                            classe: elemento.className || null,

                            oculto: oculto,

                            display: estilo.display,
                            visibility: estilo.visibility,
                            opacity: estilo.opacity,

                            textDecoration:
                                estilo.textDecoration,

                            ariaHidden:
                                elemento.getAttribute(
                                    "aria-hidden"
                                ),

                            outerHTML: elemento.outerHTML,
                        };
                    };

                    const analisarLista = (seletor) => {
                        return Array
                            .from(
                                card.querySelectorAll(
                                    seletor
                                )
                            )
                            .map(analisarElemento);
                    };

                    const todosElementosComPreco = Array
                        .from(
                            card.querySelectorAll("*")
                        )
                        .filter((elemento) => {
                            const texto = (
                                elemento.innerText
                                || elemento.textContent
                                || ""
                            )
                                .replace(/\\s+/g, " ")
                                .trim();

                            const filhosComMesmoTexto = Array
                                .from(elemento.children)
                                .some((filho) => {
                                    const textoFilho = (
                                        filho.innerText
                                        || filho.textContent
                                        || ""
                                    )
                                        .replace(/\\s+/g, " ")
                                        .trim();

                                    return textoFilho === texto;
                                });

                            return (
                                /R\\$\\s*\\d/.test(texto)
                                && !filhosComMesmoTexto
                            );
                        })
                        .map(analisarElemento);

                    return {
                        href: card.getAttribute("href"),

                        textoCompleto: (
                            card.innerText
                            || ""
                        ).trim(),

                        textContentCompleto: (
                            card.textContent
                            || ""
                        ).trim(),

                        outerHTML: card.outerHTML,

                        lineThrough: analisarLista(
                            "span.line-through"
                        ),

                        todosLineThrough: analisarLista(
                            ".line-through"
                        ),

                        textDecorationLineThrough:
                            Array
                                .from(
                                    card.querySelectorAll("*")
                                )
                                .filter((elemento) => {
                                    const estilo =
                                        window.getComputedStyle(
                                            elemento
                                        );

                                    return estilo
                                        .textDecorationLine
                                        .includes(
                                            "line-through"
                                        );
                                })
                                .map(analisarElemento),

                        precosAtuaisExatos: analisarLista(
                            "span.text-base.font-semibold.text-gray-800"
                        ),

                        precosAtuaisAlternativos: analisarLista(
                            "span.font-semibold.text-gray-800"
                        ),

                        spans: analisarLista(
                            "span"
                        ),

                        elementosComPreco:
                            todosElementosComPreco,
                    };
                }
                """
            )

            imprimir_titulo("INFORMAÇÕES PRINCIPAIS DO CARD")

            print(f"Link: {dados.get('href')}")

            print()
            print("INNER TEXT COMPLETO:")
            print("-" * 100)
            print(
                dados.get(
                    "textoCompleto",
                    "",
                )
            )

            print()
            print("TEXT CONTENT COMPLETO:")
            print("-" * 100)
            print(
                dados.get(
                    "textContentCompleto",
                    "",
                )
            )

            imprimir_elementos(
                "SPAN.LINE-THROUGH",
                dados.get(
                    "lineThrough",
                    [],
                ),
            )

            imprimir_elementos(
                "TODOS OS ELEMENTOS COM CLASSE LINE-THROUGH",
                dados.get(
                    "todosLineThrough",
                    [],
                ),
            )

            imprimir_elementos(
                "ELEMENTOS COM TEXT-DECORATION LINE-THROUGH",
                dados.get(
                    "textDecorationLineThrough",
                    [],
                ),
            )

            imprimir_elementos(
                "PREÇOS ATUAIS PELO SELETOR EXATO",
                dados.get(
                    "precosAtuaisExatos",
                    [],
                ),
            )

            imprimir_elementos(
                "PREÇOS ATUAIS PELO SELETOR ALTERNATIVO",
                dados.get(
                    "precosAtuaisAlternativos",
                    [],
                ),
            )

            imprimir_elementos(
                "TODOS OS ELEMENTOS FINAIS QUE CONTÊM R$",
                dados.get(
                    "elementosComPreco",
                    [],
                ),
            )

            ARQUIVO_HTML.write_text(
                dados.get(
                    "outerHTML",
                    "",
                ),
                encoding="utf-8",
            )

            ARQUIVO_JSON.write_text(
                json.dumps(
                    dados,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            imprimir_titulo("ARQUIVOS GERADOS")

            print(f"HTML do card: {ARQUIVO_HTML}")

            print(f"Diagnóstico completo: {ARQUIVO_JSON}")

            print()
            print("DIAGNÓSTICO CONCLUÍDO.")

            pagina.close()
            navegador.close()

    except PlaywrightError as erro:
        print()
        print("ERRO DO PLAYWRIGHT:")

        print(erro)

        print()
        print("Confirme se o Chrome foi iniciado " "com a porta 9222.")

    except Exception as erro:
        print()
        print("ERRO INESPERADO:")

        print(f"{type(erro).__name__}: {erro}")


if __name__ == "__main__":
    main()
