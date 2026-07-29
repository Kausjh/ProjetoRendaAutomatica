import json
import re
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

TITULO_SECAO = "Produtos selecionados para você"
TEXTO_BOTAO_COMPARTILHAR = "Compartilhar"

PASTA_DEBUG = Path("debug/mapear_card_produto_ml")

ARQUIVO_RESULTADO = PASTA_DEBUG / "estrutura_card_produto.json"

ARQUIVO_HTML = PASTA_DEBUG / "card_produto.html"

ARQUIVO_TEXTO = PASTA_DEBUG / "card_produto_texto.txt"

SCREENSHOT_PAGINA = PASTA_DEBUG / "pagina_com_card.png"

SCREENSHOT_CARD = PASTA_DEBUG / "card_produto.png"

MAXIMO_NIVEIS_ANCESTRAIS = 12


def limpar_texto(texto: str) -> str:
    return " ".join(texto.replace("\u00a0", " ").split()).strip()


def obter_pagina_afiliados(browser: Browser) -> Page:
    paginas: list[Page] = []

    for contexto in browser.contexts:
        for pagina in contexto.pages:
            if not pagina.is_closed():
                paginas.append(pagina)

    if not paginas:
        raise RuntimeError("Nenhuma aba aberta foi encontrada no Chrome.")

    for pagina in reversed(paginas):
        url = pagina.url.casefold()

        if "/afiliados/hub" in url:
            return pagina

    for pagina in reversed(paginas):
        url = pagina.url.casefold()

        if "mercadolivre.com.br" in url and "afiliados" in url:
            return pagina

    raise RuntimeError(
        "Não encontrei a Central de Afiliados aberta. "
        "Abra o painel do Mercado Livre antes de executar."
    )


def localizar_titulo_secao(page: Page) -> Locator:
    candidatos = page.get_by_text(
        TITULO_SECAO,
        exact=True,
    )

    for indice in range(candidatos.count()):
        candidato = candidatos.nth(indice)

        try:
            if candidato.is_visible():
                return candidato
        except PlaywrightError:
            continue

    raise RuntimeError(f"Não encontrei a seção '{TITULO_SECAO}'.")


def localizar_botoes_compartilhar_da_secao(
    page: Page,
    titulo_secao: Locator,
) -> list[Locator]:
    titulo_secao.scroll_into_view_if_needed()
    page.wait_for_timeout(700)

    caixa_titulo = titulo_secao.bounding_box()

    if caixa_titulo is None:
        raise RuntimeError("Não consegui obter a posição da seção.")

    candidatos = page.get_by_text(
        TEXTO_BOTAO_COMPARTILHAR,
        exact=True,
    )

    encontrados: list[dict[str, Any]] = []

    for indice in range(candidatos.count()):
        candidato = candidatos.nth(indice)

        try:
            if not candidato.is_visible():
                continue

            caixa = candidato.bounding_box()

            if caixa is None:
                continue

            abaixo_do_titulo = caixa["y"] > caixa_titulo["y"] + caixa_titulo["height"]

            if not abaixo_do_titulo:
                continue

            encontrados.append(
                {
                    "locator": candidato,
                    "y": caixa["y"],
                    "x": caixa["x"],
                }
            )

        except PlaywrightError:
            continue

    encontrados.sort(
        key=lambda item: (
            item["y"],
            item["x"],
        )
    )

    return [item["locator"] for item in encontrados]


def obter_ancestrais_do_botao(
    page: Page,
    botao: Locator,
) -> list[dict[str, Any]]:
    elemento = botao.element_handle()

    if elemento is None:
        raise RuntimeError("Não consegui acessar o botão Compartilhar.")

    ancestrais = page.evaluate(
        """
        ({ elemento, maximoNiveis }) => {
            const resultado = [];
            let atual = elemento;

            for (
                let nivel = 0;
                atual && nivel <= maximoNiveis;
                nivel += 1
            ) {
                const caixa = atual.getBoundingClientRect();
                const estilo = getComputedStyle(atual);

                const texto = (
                    atual.innerText ||
                    atual.textContent ||
                    ""
                )
                    .replace(/\\s+/g, " ")
                    .trim();

                const links = [
                    ...atual.querySelectorAll("a[href]")
                ].map(link => ({
                    texto: (
                        link.innerText ||
                        link.textContent ||
                        link.getAttribute("aria-label") ||
                        ""
                    )
                        .replace(/\\s+/g, " ")
                        .trim(),
                    href: link.href,
                    classe: link.className || "",
                    ariaLabel:
                        link.getAttribute("aria-label"),
                    title:
                        link.getAttribute("title")
                }));

                const imagens = [
                    ...atual.querySelectorAll("img")
                ].map(imagem => ({
                    src:
                        imagem.currentSrc ||
                        imagem.src ||
                        "",
                    alt:
                        imagem.getAttribute("alt"),
                    title:
                        imagem.getAttribute("title"),
                    width:
                        imagem.naturalWidth ||
                        imagem.width,
                    height:
                        imagem.naturalHeight ||
                        imagem.height
                }));

                const botoes = [
                    ...atual.querySelectorAll("button")
                ].map(botao => ({
                    texto: (
                        botao.innerText ||
                        botao.textContent ||
                        ""
                    )
                        .replace(/\\s+/g, " ")
                        .trim(),
                    ariaLabel:
                        botao.getAttribute("aria-label"),
                    title:
                        botao.getAttribute("title"),
                    classe:
                        botao.className || ""
                }));

                const atributos = {};

                for (const atributo of atual.attributes) {
                    atributos[atributo.name] =
                        atributo.value;
                }

                resultado.push({
                    nivel,
                    tag: atual.tagName,
                    id: atual.id || null,
                    classe:
                        typeof atual.className === "string"
                            ? atual.className
                            : "",
                    atributos,
                    texto,
                    textoTamanho: texto.length,
                    x: caixa.x,
                    y: caixa.y,
                    largura: caixa.width,
                    altura: caixa.height,
                    display: estilo.display,
                    position: estilo.position,
                    overflowX: estilo.overflowX,
                    overflowY: estilo.overflowY,
                    links,
                    imagens,
                    botoes,
                    htmlTamanho:
                        atual.outerHTML.length
                });

                atual = atual.parentElement;
            }

            return resultado;
        }
        """,
        {
            "elemento": elemento,
            "maximoNiveis": MAXIMO_NIVEIS_ANCESTRAIS,
        },
    )

    return ancestrais


def pontuar_ancestral(
    ancestral: dict[str, Any],
) -> float:
    texto = ancestral.get("texto", "")
    largura = ancestral.get("largura", 0)
    altura = ancestral.get("altura", 0)
    links = ancestral.get("links", [])
    imagens = ancestral.get("imagens", [])
    botoes = ancestral.get("botoes", [])
    nivel = ancestral.get("nivel", 0)

    pontuacao = 0.0

    if "Compartilhar" in texto:
        pontuacao += 10

    if re.search(r"R\$\s*[\d.,]+", texto):
        pontuacao += 12

    if "%" in texto:
        pontuacao += 3

    if links:
        pontuacao += 4

    if imagens:
        pontuacao += 5

    if any(botao.get("texto") == "Compartilhar" for botao in botoes):
        pontuacao += 8

    if 180 <= largura <= 700:
        pontuacao += 6

    if 180 <= altura <= 1_000:
        pontuacao += 6

    if 40 <= len(texto) <= 1_500:
        pontuacao += 6

    if len(texto) > 3_000:
        pontuacao -= 20

    if largura > 1_200:
        pontuacao -= 12

    if altura > 2_000:
        pontuacao -= 12

    pontuacao -= nivel * 0.2

    return pontuacao


def escolher_card(
    ancestrais: list[dict[str, Any]],
) -> dict[str, Any]:
    avaliados: list[dict[str, Any]] = []

    for ancestral in ancestrais:
        item = dict(ancestral)
        item["pontuacao_card"] = pontuar_ancestral(ancestral)
        avaliados.append(item)

    candidatos = [
        item
        for item in avaliados
        if (item["nivel"] >= 1 and item["largura"] >= 150 and item["altura"] >= 100)
    ]

    if not candidatos:
        raise RuntimeError("Não encontrei um ancestral adequado " "para representar o card.")

    candidatos.sort(
        key=lambda item: item["pontuacao_card"],
        reverse=True,
    )

    return candidatos[0]


def localizar_elemento_por_nivel(
    botao: Locator,
    nivel: int,
) -> ElementHandle:
    elemento = botao.element_handle()

    if elemento is None:
        raise RuntimeError("Não consegui acessar o botão.")

    atual = elemento

    for _ in range(nivel):
        pai = atual.evaluate_handle("elemento => elemento.parentElement").as_element()

        if pai is None:
            raise RuntimeError("O ancestral esperado não existe.")

        atual = pai

    return atual


def coletar_detalhes_card(
    page: Page,
    card: ElementHandle,
) -> dict[str, Any]:
    return page.evaluate(
        """
        (card) => {
            function limpar(texto) {
                return (texto || "")
                    .replace(/\\s+/g, " ")
                    .trim();
            }

            function atributos(elemento) {
                const resultado = {};

                for (const atributo of elemento.attributes) {
                    resultado[atributo.name] =
                        atributo.value;
                }

                return resultado;
            }

            function caminhoCss(elemento) {
                const partes = [];
                let atual = elemento;

                while (
                    atual &&
                    atual.nodeType === Node.ELEMENT_NODE &&
                    partes.length < 8
                ) {
                    let parte =
                        atual.tagName.toLowerCase();

                    if (atual.id) {
                        parte += `#${atual.id}`;
                        partes.unshift(parte);
                        break;
                    }

                    const classes = [
                        ...atual.classList
                    ].slice(0, 3);

                    if (classes.length) {
                        parte +=
                            "." + classes.join(".");
                    }

                    partes.unshift(parte);
                    atual = atual.parentElement;
                }

                return partes.join(" > ");
            }

            const todos = [
                card,
                ...card.querySelectorAll("*")
            ];

            const elementos = todos.map(
                (elemento, indice) => {
                    const caixa =
                        elemento.getBoundingClientRect();

                    return {
                        indice,
                        tag: elemento.tagName,
                        texto: limpar(
                            elemento.innerText ||
                            elemento.textContent
                        ),
                        atributos:
                            atributos(elemento),
                        classe:
                            typeof elemento.className
                            === "string"
                                ? elemento.className
                                : "",
                        caminhoCss:
                            caminhoCss(elemento),
                        x: caixa.x,
                        y: caixa.y,
                        largura: caixa.width,
                        altura: caixa.height
                    };
                }
            );

            const links = [
                ...card.querySelectorAll("a[href]")
            ].map((link, indice) => ({
                indice,
                texto: limpar(
                    link.innerText ||
                    link.textContent
                ),
                href: link.href,
                atributos: atributos(link),
                caminhoCss: caminhoCss(link)
            }));

            const imagens = [
                ...card.querySelectorAll("img")
            ].map((imagem, indice) => ({
                indice,
                src:
                    imagem.currentSrc ||
                    imagem.src ||
                    "",
                alt:
                    imagem.getAttribute("alt"),
                title:
                    imagem.getAttribute("title"),
                atributos:
                    atributos(imagem),
                caminhoCss:
                    caminhoCss(imagem)
            }));

            const botoes = [
                ...card.querySelectorAll("button")
            ].map((botao, indice) => ({
                indice,
                texto: limpar(
                    botao.innerText ||
                    botao.textContent
                ),
                ariaLabel:
                    botao.getAttribute("aria-label"),
                title:
                    botao.getAttribute("title"),
                atributos:
                    atributos(botao),
                caminhoCss:
                    caminhoCss(botao)
            }));

            const textosComPreco = elementos.filter(
                item =>
                    /R\\$\\s*[\\d.,]+/.test(item.texto)
                    && item.texto.length <= 300
            );

            const textosComPercentual =
                elementos.filter(
                    item =>
                        /\\d+[,.]?\\d*\\s*%/.test(
                            item.texto
                        )
                        && item.texto.length <= 300
                );

            const candidatosTitulo =
                elementos.filter(
                    item =>
                        item.texto.length >= 10
                        && item.texto.length <= 250
                        && !item.texto.includes(
                            "Compartilhar"
                        )
                        && !/^R\\$/.test(item.texto)
                        && !/^\\d+[,.]?\\d*\\s*%$/.test(
                            item.texto
                        )
                        && [
                            "H1",
                            "H2",
                            "H3",
                            "H4",
                            "P",
                            "SPAN",
                            "DIV",
                            "A"
                        ].includes(item.tag)
                );

            const caixa =
                card.getBoundingClientRect();

            return {
                tag: card.tagName,
                id: card.id || null,
                classe:
                    typeof card.className === "string"
                        ? card.className
                        : "",
                atributos: atributos(card),
                caminhoCss: caminhoCss(card),
                texto: limpar(card.innerText),
                html: card.outerHTML,
                caixa: {
                    x: caixa.x,
                    y: caixa.y,
                    largura: caixa.width,
                    altura: caixa.height
                },
                links,
                imagens,
                botoes,
                textosComPreco,
                textosComPercentual,
                candidatosTitulo,
                elementos
            };
        }
        """,
        card,
    )


def resumir_candidatos(
    detalhes: dict[str, Any],
) -> dict[str, Any]:
    precos = detalhes.get(
        "textosComPreco",
        [],
    )

    percentuais = detalhes.get(
        "textosComPercentual",
        [],
    )

    titulos = detalhes.get(
        "candidatosTitulo",
        [],
    )

    links = detalhes.get("links", [])
    imagens = detalhes.get("imagens", [])

    return {
        "possiveis_titulos": [
            {
                "texto": item["texto"],
                "tag": item["tag"],
                "caminho_css": item["caminhoCss"],
            }
            for item in titulos[:30]
        ],
        "possiveis_precos": [
            {
                "texto": item["texto"],
                "tag": item["tag"],
                "caminho_css": item["caminhoCss"],
            }
            for item in precos[:30]
        ],
        "possiveis_percentuais": [
            {
                "texto": item["texto"],
                "tag": item["tag"],
                "caminho_css": item["caminhoCss"],
            }
            for item in percentuais[:30]
        ],
        "links": [
            {
                "texto": item["texto"],
                "href": item["href"],
                "caminho_css": item["caminhoCss"],
            }
            for item in links
        ],
        "imagens": [
            {
                "src": item["src"],
                "alt": item["alt"],
                "caminho_css": item["caminhoCss"],
            }
            for item in imagens
        ],
    }


def salvar_resultados(
    ancestrais: list[dict[str, Any]],
    card_escolhido: dict[str, Any],
    detalhes_card: dict[str, Any],
) -> None:
    PASTA_DEBUG.mkdir(
        parents=True,
        exist_ok=True,
    )

    resultado = {
        "card_escolhido": {key: value for key, value in card_escolhido.items() if key != "html"},
        "resumo_extracao": resumir_candidatos(detalhes_card),
        "ancestrais_avaliados": [
            {
                **ancestral,
                "pontuacao_card": pontuar_ancestral(ancestral),
            }
            for ancestral in ancestrais
        ],
        "detalhes_card": {key: value for key, value in detalhes_card.items() if key != "html"},
    }

    ARQUIVO_RESULTADO.write_text(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    ARQUIVO_HTML.write_text(
        detalhes_card.get("html", ""),
        encoding="utf-8",
    )

    ARQUIVO_TEXTO.write_text(
        detalhes_card.get("texto", ""),
        encoding="utf-8",
    )


def main() -> None:
    PASTA_DEBUG.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 72)
    print("MAPEAMENTO DA ESTRUTURA DE UM CARD DE PRODUTO")
    print("=" * 72)

    try:
        with sync_playwright() as playwright:
            print(f"[INFO] Conectando ao Chrome em " f"{URL_CDP}...")

            browser = playwright.chromium.connect_over_cdp(URL_CDP)

            page = obter_pagina_afiliados(browser)
            page.bring_to_front()

            print(f"[INFO] Página: {page.title()}")
            print(f"[INFO] URL: {page.url}")

            titulo_secao = localizar_titulo_secao(page)

            botoes = localizar_botoes_compartilhar_da_secao(
                page,
                titulo_secao,
            )

            print("[INFO] Botões Compartilhar visíveis " f"encontrados: {len(botoes)}")

            if not botoes:
                raise RuntimeError(
                    "Nenhum botão Compartilhar foi " "encontrado na seção de produtos."
                )

            botao = botoes[0]

            botao.scroll_into_view_if_needed()
            page.wait_for_timeout(700)

            page.screenshot(
                path=str(SCREENSHOT_PAGINA),
                full_page=False,
            )

            print("[INFO] Analisando o primeiro produto " "visível...")

            ancestrais = obter_ancestrais_do_botao(
                page,
                botao,
            )

            card_escolhido = escolher_card(ancestrais)

            nivel = card_escolhido["nivel"]

            print("[OK] Ancestral escolhido como card:")
            print(f"     nível: {nivel}")
            print(f"     tag: {card_escolhido['tag']}")
            print(f"     classe: " f"{card_escolhido['classe']}")
            print(
                f"     tamanho: "
                f"{card_escolhido['largura']:.0f}x"
                f"{card_escolhido['altura']:.0f}"
            )
            print(f"     pontuação: " f"{card_escolhido['pontuacao_card']:.1f}")

            card = localizar_elemento_por_nivel(
                botao,
                nivel,
            )

            detalhes_card = coletar_detalhes_card(
                page,
                card,
            )

            card.screenshot(
                path=str(SCREENSHOT_CARD),
            )

            salvar_resultados(
                ancestrais,
                card_escolhido,
                detalhes_card,
            )

            resumo = resumir_candidatos(detalhes_card)

            print()
            print("=" * 72)
            print("RESUMO DO CARD")
            print("=" * 72)

            print("[INFO] Texto do card:")
            print(detalhes_card["texto"][:1_000])

            print()
            print("[INFO] Links encontrados: " f"{len(resumo['links'])}")

            for indice, link in enumerate(
                resumo["links"][:10],
                start=1,
            ):
                print(f"  {indice}. " f"{link['texto'] or '[sem texto]'}")
                print(f"     {link['href']}")

            print()
            print("[INFO] Possíveis preços: " f"{len(resumo['possiveis_precos'])}")

            for item in resumo["possiveis_precos"][:10]:
                print(f"  - {item['texto']}")

            print()
            print("[INFO] Possíveis percentuais: " f"{len(resumo['possiveis_percentuais'])}")

            for item in resumo["possiveis_percentuais"][:10]:
                print(f"  - {item['texto']}")

            print()
            print("=" * 72)
            print("ARQUIVOS GERADOS")
            print("=" * 72)
            print(f"[OK] Estrutura JSON: " f"{ARQUIVO_RESULTADO}")
            print(f"[OK] HTML do card: " f"{ARQUIVO_HTML}")
            print(f"[OK] Texto do card: " f"{ARQUIVO_TEXTO}")
            print(f"[OK] Screenshot do card: " f"{SCREENSHOT_CARD}")
            print(f"[OK] Screenshot da página: " f"{SCREENSHOT_PAGINA}")

    except PlaywrightTimeoutError as erro:
        print()
        print("[ERRO] A página demorou demais " "para responder.")
        print(f"[DETALHES] {erro}")

    except PlaywrightError as erro:
        print()
        print("[ERRO] O Playwright encontrou " "um problema.")
        print(f"[DETALHES] {erro}")

    except Exception as erro:
        print()
        print("[ERRO] Não foi possível mapear " "o card de produto.")
        print(f"[DETALHES] {erro}")


if __name__ == "__main__":
    main()
