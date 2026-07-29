import json
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    Browser,
    ElementHandle,
    Locator,
    Page,
    sync_playwright,
)
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

URL_CDP = "http://127.0.0.1:9222"

PASTA_DATABASE = Path("database")
PASTA_DEBUG = Path("debug")

ARQUIVO_CATEGORIAS = PASTA_DATABASE / "categorias_afiliados_ml.json"
SCREENSHOT_ABERTO = PASTA_DEBUG / "categorias_afiliados_aberto.png"
SCREENSHOT_FINAL = PASTA_DEBUG / "categorias_afiliados_final.png"
ARQUIVO_TEXTO_DEBUG = PASTA_DEBUG / "categorias_afiliados_textos.txt"

MAXIMO_DE_SCROLLS = 80
MAXIMO_SEM_NOVIDADE = 4
ESPERA_ENTRE_SCROLLS_MS = 700


def obter_pagina_afiliados(browser: Browser) -> Page:
    if not browser.contexts:
        raise RuntimeError("Nenhum contexto do Chrome foi encontrado.")

    contexto = browser.contexts[0]

    paginas = [pagina for pagina in contexto.pages if not pagina.is_closed()]

    if not paginas:
        raise RuntimeError("Nenhuma aba aberta foi encontrada no Chrome.")

    for pagina in reversed(paginas):
        url = pagina.url.lower()

        if "/afiliados/hub" in url:
            return pagina

    for pagina in reversed(paginas):
        url = pagina.url.lower()

        if "mercadolivre.com.br/afiliados" in url:
            return pagina

    raise RuntimeError(
        "Não encontrei a Central de Afiliados aberta. "
        "Abra a página do painel e execute novamente."
    )


def localizar_secao_produtos(page: Page) -> Locator:
    titulo = page.get_by_text(
        "Produtos selecionados para você",
        exact=True,
    )

    if titulo.count() == 0:
        raise RuntimeError("Não encontrei a seção " "'Produtos selecionados para você'.")

    titulo_visivel = None

    for indice in range(titulo.count()):
        candidato = titulo.nth(indice)

        if candidato.is_visible():
            titulo_visivel = candidato
            break

    if titulo_visivel is None:
        raise RuntimeError("O título da seção de produtos existe, " "mas não está visível.")

    secao_handle = page.evaluate_handle(
        """
        (titulo) => {
            let atual = titulo;

            while (atual && atual !== document.body) {
                const texto = (atual.innerText || "").trim();

                const temCategorias = texto.includes("Categorias");
                const temGanhosExtras = texto.includes("Ganhos extras");
                const temMaisVendidos = texto.includes("Mais vendidos");
                const temBusca = texto.includes("Busque produtos");

                if (
                    temCategorias &&
                    temGanhosExtras &&
                    temMaisVendidos &&
                    temBusca
                ) {
                    return atual;
                }

                atual = atual.parentElement;
            }

            return titulo.parentElement;
        }
        """,
        titulo_visivel.element_handle(),
    )

    elemento = secao_handle.as_element()

    if elemento is None:
        raise RuntimeError("Não consegui identificar o contêiner da seção.")

    return (
        page.locator("xpath=//*")
        .filter(
            has=page.get_by_text(
                "Produtos selecionados para você",
                exact=True,
            )
        )
        .first
    )


def localizar_botao_categorias_afiliados(page: Page) -> Locator:
    titulo = page.get_by_text(
        "Produtos selecionados para você",
        exact=True,
    ).first

    titulo.scroll_into_view_if_needed()
    page.wait_for_timeout(300)

    botoes = page.get_by_text(
        "Categorias",
        exact=True,
    )

    candidatos: list[dict[str, Any]] = []

    caixa_titulo = titulo.bounding_box()

    if caixa_titulo is None:
        raise RuntimeError("Não consegui obter a posição do título da seção.")

    for indice in range(botoes.count()):
        elemento = botoes.nth(indice)

        try:
            if not elemento.is_visible():
                continue

            caixa = elemento.bounding_box()

            if caixa is None:
                continue

            centro_x = caixa["x"] + caixa["width"] / 2
            centro_y = caixa["y"] + caixa["height"] / 2

            centro_titulo_x = caixa_titulo["x"] + caixa_titulo["width"] / 2
            parte_inferior_titulo = caixa_titulo["y"] + caixa_titulo["height"]

            distancia_vertical = centro_y - parte_inferior_titulo
            distancia_horizontal = abs(centro_x - centro_titulo_x)

            abaixo_do_titulo = distancia_vertical > 0
            perto_da_secao = distancia_vertical < 180

            candidatos.append(
                {
                    "locator": elemento,
                    "indice": indice,
                    "x": caixa["x"],
                    "y": caixa["y"],
                    "distancia_vertical": distancia_vertical,
                    "distancia_horizontal": distancia_horizontal,
                    "valido": abaixo_do_titulo and perto_da_secao,
                }
            )

        except PlaywrightError:
            continue

    candidatos_validos = [candidato for candidato in candidatos if candidato["valido"]]

    if not candidatos_validos:
        detalhes = "\n".join(
            (
                f"índice={item['indice']} "
                f"x={item['x']:.0f} "
                f"y={item['y']:.0f} "
                f"distância vertical="
                f"{item['distancia_vertical']:.0f}"
            )
            for item in candidatos
        )

        raise RuntimeError(
            "Não consegui identificar o botão Categorias "
            "do painel de afiliados.\n"
            f"Candidatos encontrados:\n{detalhes}"
        )

    candidatos_validos.sort(
        key=lambda item: (
            item["distancia_vertical"],
            item["distancia_horizontal"],
        )
    )

    escolhido = candidatos_validos[0]

    print(
        "[OK] Botão Categorias do painel localizado: "
        f"x={escolhido['x']:.0f}, "
        f"y={escolhido['y']:.0f}"
    )

    return escolhido["locator"]


def filtro_parece_aberto(
    page: Page,
    botao: Locator,
) -> bool:
    aria_expanded = botao.get_attribute("aria-expanded")

    if aria_expanded == "true":
        return True

    classe = botao.get_attribute("class") or ""

    if any(
        termo in classe.lower()
        for termo in (
            "active",
            "selected",
            "opened",
            "expanded",
        )
    ):
        return True

    caixa_botao = botao.bounding_box()

    if caixa_botao is None:
        return False

    resultado = page.evaluate(
        """
        ({x, y, width, height}) => {
            const elementos = [
                ...document.querySelectorAll(
                    '[role="dialog"], ' +
                    '[role="menu"], ' +
                    '[role="listbox"], ' +
                    '[class*="popover"], ' +
                    '[class*="dropdown"], ' +
                    '[class*="modal"]'
                )
            ];

            function visivel(elemento) {
                const estilo = getComputedStyle(elemento);
                const caixa = elemento.getBoundingClientRect();

                return (
                    estilo.display !== "none" &&
                    estilo.visibility !== "hidden" &&
                    caixa.width > 0 &&
                    caixa.height > 0
                );
            }

            const centroBotaoX = x + width / 2;
            const centroBotaoY = y + height / 2;

            for (const elemento of elementos) {
                if (!visivel(elemento)) {
                    continue;
                }

                const caixa = elemento.getBoundingClientRect();
                const texto = (elemento.innerText || "").trim();

                if (!texto) {
                    continue;
                }

                const centroX = caixa.x + caixa.width / 2;
                const centroY = caixa.y + caixa.height / 2;

                const distancia = Math.hypot(
                    centroX - centroBotaoX,
                    centroY - centroBotaoY
                );

                if (
                    distancia < 700 &&
                    caixa.height > 80 &&
                    texto.split("\\n").length >= 3
                ) {
                    return true;
                }
            }

            return false;
        }
        """,
        caixa_botao,
    )

    return bool(resultado)


def abrir_filtro(
    page: Page,
    botao: Locator,
) -> None:
    if filtro_parece_aberto(page, botao):
        print("[INFO] O filtro já parece estar aberto.")
        return

    botao.scroll_into_view_if_needed()
    page.wait_for_timeout(300)

    botao.click()
    page.wait_for_timeout(1200)

    print("[OK] Filtro de categorias do painel aberto.")


def localizar_painel_do_filtro(
    page: Page,
    botao: Locator,
) -> ElementHandle:
    caixa_botao = botao.bounding_box()

    if caixa_botao is None:
        raise RuntimeError("Não consegui obter a posição do botão Categorias.")

    handle = page.evaluate_handle(
        """
        ({x, y, width, height}) => {
            function visivel(elemento) {
                const estilo = getComputedStyle(elemento);
                const caixa = elemento.getBoundingClientRect();

                return (
                    estilo.display !== "none" &&
                    estilo.visibility !== "hidden" &&
                    caixa.width > 0 &&
                    caixa.height > 0
                );
            }

            const seletores = [
                '[role="dialog"]',
                '[role="menu"]',
                '[role="listbox"]',
                '[class*="popover"]',
                '[class*="dropdown"]',
                '[class*="modal"]',
                '[class*="filter"]',
                '[class*="andes"]'
            ];

            const elementos = [
                ...document.querySelectorAll(
                    seletores.join(",")
                )
            ];

            const centroBotaoX = x + width / 2;
            const centroBotaoY = y + height / 2;

            const candidatos = [];

            for (const elemento of elementos) {
                if (!visivel(elemento)) {
                    continue;
                }

                const caixa = elemento.getBoundingClientRect();
                const texto = (elemento.innerText || "").trim();

                if (!texto) {
                    continue;
                }

                const linhas = texto
                    .split("\\n")
                    .map(linha => linha.trim())
                    .filter(Boolean);

                if (linhas.length < 3) {
                    continue;
                }

                if (caixa.height < 80 || caixa.width < 120) {
                    continue;
                }

                const centroX = caixa.x + caixa.width / 2;
                const centroY = caixa.y + caixa.height / 2;

                const distancia = Math.hypot(
                    centroX - centroBotaoX,
                    centroY - centroBotaoY
                );

                let pontuacao = 0;

                if (distancia < 400) pontuacao += 15;
                else if (distancia < 700) pontuacao += 8;

                if (caixa.y >= y - 80) pontuacao += 5;

                if (
                    texto.toLowerCase().includes("categoria")
                ) {
                    pontuacao += 5;
                }

                pontuacao += Math.min(linhas.length, 20);

                candidatos.push({
                    elemento,
                    pontuacao,
                    area: caixa.width * caixa.height
                });
            }

            candidatos.sort((a, b) => {
                if (b.pontuacao !== a.pontuacao) {
                    return b.pontuacao - a.pontuacao;
                }

                return a.area - b.area;
            });

            if (candidatos.length > 0) {
                return candidatos[0].elemento;
            }

            return null;
        }
        """,
        caixa_botao,
    )

    painel = handle.as_element()

    if painel is not None:
        return painel

    print("[AVISO] Não encontrei um painel específico. " "Usarei a área visível próxima ao botão.")

    fallback = page.evaluate_handle(
        """
        ({x, y, width, height}) => {
            const pontoX = x + width / 2;
            const pontoY = y + height + 60;

            return (
                document.elementFromPoint(pontoX, pontoY) ||
                document.body
            );
        }
        """,
        caixa_botao,
    ).as_element()

    if fallback is None:
        raise RuntimeError("Não consegui localizar o painel do filtro.")

    return fallback


def localizar_container_scroll(
    page: Page,
    painel: ElementHandle,
) -> ElementHandle:
    handle = page.evaluate_handle(
        """
        (raiz) => {
            function visivel(elemento) {
                const estilo = getComputedStyle(elemento);
                const caixa = elemento.getBoundingClientRect();

                return (
                    estilo.display !== "none" &&
                    estilo.visibility !== "hidden" &&
                    caixa.width > 0 &&
                    caixa.height > 0
                );
            }

            function podeRolar(elemento) {
                const estilo = getComputedStyle(elemento);

                return (
                    visivel(elemento) &&
                    elemento.scrollHeight >
                        elemento.clientHeight + 4 &&
                    (
                        estilo.overflowY === "auto" ||
                        estilo.overflowY === "scroll" ||
                        estilo.overflowY === "overlay"
                    )
                );
            }

            const elementos = [
                raiz,
                ...raiz.querySelectorAll("*")
            ];

            const rolaveis = elementos.filter(podeRolar);

            if (rolaveis.length === 0) {
                return raiz;
            }

            rolaveis.sort((a, b) => {
                const capacidadeA =
                    a.scrollHeight - a.clientHeight;

                const capacidadeB =
                    b.scrollHeight - b.clientHeight;

                return capacidadeB - capacidadeA;
            });

            return rolaveis[0];
        }
        """,
        painel,
    )

    elemento = handle.as_element()

    if elemento is None:
        raise RuntimeError("Não consegui identificar o contêiner rolável.")

    return elemento


def limpar_texto(texto: str) -> str:
    return " ".join(texto.replace("\u00a0", " ").split()).strip()


def texto_valido(texto: str) -> bool:
    texto = limpar_texto(texto)

    if len(texto) < 2 or len(texto) > 100:
        return False

    texto_minusculo = texto.casefold()

    ignorar = {
        "categorias",
        "categoria",
        "filtrar",
        "aplicar",
        "cancelar",
        "fechar",
        "limpar",
        "limpar filtros",
        "ganhos extras",
        "mais vendidos",
        "mais relevantes",
        "produtos selecionados para você",
        "busque produtos",
        "buscar produtos",
        "ver resultados",
    }

    if texto_minusculo in ignorar:
        return False

    if texto_minusculo.startswith("r$"):
        return False

    if texto.replace("%", "").isdigit():
        return False

    return True


def coletar_textos(
    page: Page,
    container: ElementHandle,
) -> set[str]:
    textos = page.evaluate(
        """
        (raiz) => {
            function visivel(elemento) {
                const estilo = getComputedStyle(elemento);
                const caixa = elemento.getBoundingClientRect();

                return (
                    estilo.display !== "none" &&
                    estilo.visibility !== "hidden" &&
                    caixa.width > 0 &&
                    caixa.height > 0
                );
            }

            const seletores = [
                'label',
                'button',
                'li',
                '[role="option"]',
                '[role="menuitem"]',
                '[role="menuitemradio"]',
                '[role="menuitemcheckbox"]',
                '[role="checkbox"]',
                '[role="radio"]',
                'input + span',
                'input + label'
            ];

            const encontrados = [];

            for (
                const elemento of raiz.querySelectorAll(
                    seletores.join(",")
                )
            ) {
                if (!visivel(elemento)) {
                    continue;
                }

                const texto = (
                    elemento.innerText ||
                    elemento.textContent ||
                    elemento.getAttribute("aria-label") ||
                    ""
                ).trim();

                if (texto) {
                    encontrados.push(texto);
                }
            }

            return encontrados;
        }
        """,
        container,
    )

    resultado: set[str] = set()

    for texto in textos:
        for linha in texto.splitlines():
            linha_limpa = limpar_texto(linha)

            if texto_valido(linha_limpa):
                resultado.add(linha_limpa)

    return resultado


def obter_scroll(
    page: Page,
    container: ElementHandle,
) -> dict[str, Any]:
    return page.evaluate(
        """
        (elemento) => ({
            scrollTop: elemento.scrollTop,
            scrollHeight: elemento.scrollHeight,
            clientHeight: elemento.clientHeight,
            fim:
                elemento.scrollTop +
                elemento.clientHeight >=
                elemento.scrollHeight - 5
        })
        """,
        container,
    )


def executar_scroll(
    page: Page,
    container: ElementHandle,
) -> dict[str, Any]:
    return page.evaluate(
        """
        (elemento) => {
            const antes = elemento.scrollTop;

            const distancia = Math.max(
                Math.floor(elemento.clientHeight * 0.7),
                120
            );

            elemento.scrollTop =
                elemento.scrollTop + distancia;

            return {
                antes,
                depois: elemento.scrollTop,
                scrollHeight: elemento.scrollHeight,
                clientHeight: elemento.clientHeight,
                fim:
                    elemento.scrollTop +
                    elemento.clientHeight >=
                    elemento.scrollHeight - 5
            };
        }
        """,
        container,
    )


def mapear_categorias(
    page: Page,
    container: ElementHandle,
) -> list[str]:
    page.evaluate(
        "(elemento) => elemento.scrollTop = 0",
        container,
    )

    page.wait_for_timeout(500)

    encontrados: set[str] = set()
    rodadas_sem_novidade = 0

    for rodada in range(1, MAXIMO_DE_SCROLLS + 1):
        textos_atuais = coletar_textos(
            page,
            container,
        )

        quantidade_anterior = len(encontrados)
        encontrados.update(textos_atuais)

        novas = len(encontrados) - quantidade_anterior

        if novas == 0:
            rodadas_sem_novidade += 1
        else:
            rodadas_sem_novidade = 0

        posicao = obter_scroll(
            page,
            container,
        )

        print(
            f"[ROLAGEM {rodada:02d}] "
            f"novas={novas} | "
            f"total={len(encontrados)} | "
            f"posição={posicao['scrollTop']}/"
            f"{posicao['scrollHeight']}"
        )

        if posicao["fim"] and rodadas_sem_novidade >= 2:
            print("[OK] Final da lista detectado.")
            break

        if rodadas_sem_novidade >= MAXIMO_SEM_NOVIDADE:
            print("[OK] Nenhum texto novo encontrado após " f"{MAXIMO_SEM_NOVIDADE} tentativas.")
            break

        resultado = executar_scroll(
            page,
            container,
        )

        if resultado["antes"] == resultado["depois"]:
            rodadas_sem_novidade += 1

        page.wait_for_timeout(ESPERA_ENTRE_SCROLLS_MS)

    return sorted(
        encontrados,
        key=str.casefold,
    )


def salvar_resultados(categorias: list[str]) -> None:
    PASTA_DATABASE.mkdir(
        parents=True,
        exist_ok=True,
    )

    PASTA_DEBUG.mkdir(
        parents=True,
        exist_ok=True,
    )

    conteudo = {
        "origem": ("Central de Afiliados - " "Produtos selecionados para você"),
        "quantidade": len(categorias),
        "categorias": categorias,
    }

    ARQUIVO_CATEGORIAS.write_text(
        json.dumps(
            conteudo,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    ARQUIVO_TEXTO_DEBUG.write_text(
        "\n".join(categorias),
        encoding="utf-8",
    )


def main() -> None:
    PASTA_DATABASE.mkdir(
        parents=True,
        exist_ok=True,
    )

    PASTA_DEBUG.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 65)
    print("MAPEAMENTO DO FILTRO DE CATEGORIAS DOS AFILIADOS")
    print("=" * 65)

    try:
        with sync_playwright() as playwright:
            print(f"[INFO] Conectando ao Chrome em {URL_CDP}...")

            browser = playwright.chromium.connect_over_cdp(URL_CDP)

            page = obter_pagina_afiliados(browser)

            page.bring_to_front()

            print(f"[INFO] Página: {page.title()}")
            print(f"[INFO] URL: {page.url}")

            localizar_secao_produtos(page)

            botao = localizar_botao_categorias_afiliados(page)

            abrir_filtro(
                page,
                botao,
            )

            page.screenshot(
                path=str(SCREENSHOT_ABERTO),
                full_page=False,
            )

            painel = localizar_painel_do_filtro(
                page,
                botao,
            )

            container = localizar_container_scroll(
                page,
                painel,
            )

            dimensoes = obter_scroll(
                page,
                container,
            )

            print(
                "[INFO] Contêiner localizado: "
                f"altura visível="
                f"{dimensoes['clientHeight']} | "
                f"altura total="
                f"{dimensoes['scrollHeight']}"
            )

            categorias = mapear_categorias(
                page,
                container,
            )

            page.screenshot(
                path=str(SCREENSHOT_FINAL),
                full_page=False,
            )

            salvar_resultados(categorias)

            print()
            print("=" * 65)
            print(f"ITENS ENCONTRADOS: {len(categorias)}")
            print("=" * 65)

            for indice, categoria in enumerate(
                categorias,
                start=1,
            ):
                print(f"{indice:02d}. {categoria}")

            print()
            print(f"[OK] JSON salvo em: " f"{ARQUIVO_CATEGORIAS}")
            print(f"[OK] Screenshot inicial: " f"{SCREENSHOT_ABERTO}")
            print(f"[OK] Screenshot final: " f"{SCREENSHOT_FINAL}")
            print(f"[OK] Textos brutos: " f"{ARQUIVO_TEXTO_DEBUG}")

    except PlaywrightTimeoutError as erro:
        print()
        print("[ERRO] A página demorou demais para responder.")
        print(f"[DETALHES] {erro}")

    except PlaywrightError as erro:
        print()
        print("[ERRO] Problema encontrado pelo Playwright.")
        print(f"[DETALHES] {erro}")

    except Exception as erro:
        print()
        print("[ERRO] Não foi possível mapear " "as categorias do painel.")
        print(f"[DETALHES] {erro}")


if __name__ == "__main__":
    main()
