import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    Browser,
    BrowserContext,
    ElementHandle,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


ENDERECO_CDP = "http://127.0.0.1:9222"

PASTA_RELATORIOS = Path("relatorios")
NOME_BASE_RELATORIO = "mapa_pagina_mercado_livre"

PALAVRAS_IMPORTANTES = (
    "afiliado",
    "afiliados",
    "comissão",
    "comissao",
    "compartilhar",
    "copiar",
    "produto",
    "produtos",
    "ganho",
    "ganhos",
    "recomendar",
    "recomendado",
    "recomendados",
    "selecionado",
    "selecionados",
    "link",
    "oferta",
    "ofertas",
)


def obter_contexto(browser: Browser) -> BrowserContext:
    """Retorna o primeiro contexto disponível no Chrome conectado."""

    if not browser.contexts:
        raise RuntimeError(
            "Nenhum contexto foi encontrado no Chrome conectado."
        )

    return browser.contexts[0]


def listar_paginas(contexto: BrowserContext) -> None:
    """Exibe todas as abas abertas no Chrome dedicado."""

    print()
    print("Abas encontradas:")
    print()

    for indice, pagina in enumerate(contexto.pages, start=1):
        try:
            titulo = pagina.title()
        except Exception:
            titulo = "Título indisponível"

        print(f"[{indice}] {titulo}")
        print(f"    {pagina.url}")
        print()


def escolher_pagina_mercado_livre(
    contexto: BrowserContext,
) -> Page:
    """
    Escolhe a página do Mercado Livre mais adequada.

    Dá preferência para páginas da Central de Afiliados.
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
            "Nenhuma aba do Mercado Livre foi encontrada.\n"
            "Abra a Central de Afiliados no Chrome dedicado "
            "e execute o script novamente."
        )

    palavras_prioritarias = (
        "afiliado",
        "affiliate",
        "creator",
        "monetiza",
    )

    for pagina in paginas_ml:
        url = pagina.url.lower()

        if any(
            palavra in url
            for palavra in palavras_prioritarias
        ):
            return pagina

    return paginas_ml[-1]


def texto_limpo(texto: str | None) -> str:
    """Normaliza textos para facilitar a leitura do relatório."""

    if not texto:
        return ""

    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def limitar_texto(
    texto: str | None,
    limite: int = 500,
) -> str:
    """Limita textos muito grandes."""

    texto_normalizado = texto_limpo(texto)

    if len(texto_normalizado) <= limite:
        return texto_normalizado

    return texto_normalizado[:limite] + "..."


def ler_atributos(
    elemento: ElementHandle,
) -> dict[str, str]:
    """Obtém atributos HTML relevantes do elemento."""

    nomes_atributos = (
        "id",
        "class",
        "name",
        "type",
        "role",
        "href",
        "title",
        "value",
        "placeholder",
        "aria-label",
        "aria-labelledby",
        "aria-describedby",
        "aria-expanded",
        "aria-haspopup",
        "aria-controls",
        "data-testid",
        "data-test-id",
        "data-id",
        "data-component",
        "data-index",
    )

    atributos: dict[str, str] = {}

    for nome in nomes_atributos:
        try:
            valor = elemento.get_attribute(nome)

            if valor:
                atributos[nome] = limitar_texto(
                    valor,
                    limite=300,
                )

        except Exception:
            continue

    return atributos


def elemento_visivel(
    elemento: ElementHandle,
) -> bool:
    """Verifica se o elemento está visível."""

    try:
        return elemento.is_visible()
    except Exception:
        return False


def obter_texto_elemento(
    elemento: ElementHandle,
) -> str:
    """Obtém texto visível ou conteúdo textual do elemento."""

    try:
        texto = elemento.inner_text(timeout=2_000)

        if texto:
            return limitar_texto(texto)

    except Exception:
        pass

    try:
        texto = elemento.text_content()

        if texto:
            return limitar_texto(texto)

    except Exception:
        pass

    return ""


def obter_tag_elemento(
    elemento: ElementHandle,
) -> str:
    """Obtém o nome da tag HTML."""

    try:
        return elemento.evaluate(
            "(elemento) => elemento.tagName.toLowerCase()"
        )
    except Exception:
        return "desconhecida"


def obter_html_resumido(
    elemento: ElementHandle,
    limite: int = 1000,
) -> str:
    """Obtém o HTML externo resumido do elemento."""

    try:
        html = elemento.evaluate(
            "(elemento) => elemento.outerHTML"
        )

        html = re.sub(r"\s+", " ", html).strip()

        if len(html) > limite:
            html = html[:limite] + "..."

        return html

    except Exception:
        return ""


def mapear_elementos(
    pagina: Page,
    seletor: str,
    categoria: str,
    somente_visiveis: bool = True,
    limite: int = 500,
) -> list[dict[str, Any]]:
    """Mapeia elementos encontrados por um seletor CSS."""

    resultados: list[dict[str, Any]] = []

    locator = pagina.locator(seletor)
    quantidade_total = locator.count()

    quantidade_analisada = min(
        quantidade_total,
        limite,
    )

    for indice in range(quantidade_analisada):
        try:
            elemento = locator.nth(indice).element_handle()

            if elemento is None:
                continue

            visivel = elemento_visivel(elemento)

            if somente_visiveis and not visivel:
                continue

            resultado = {
                "categoria": categoria,
                "indice": indice,
                "tag": obter_tag_elemento(elemento),
                "visivel": visivel,
                "texto": obter_texto_elemento(elemento),
                "atributos": ler_atributos(elemento),
                "html_resumido": obter_html_resumido(elemento),
            }

            resultados.append(resultado)

        except Exception as erro:
            resultados.append(
                {
                    "categoria": categoria,
                    "indice": indice,
                    "erro": str(erro),
                }
            )

    return resultados


def mapear_textos_importantes(
    pagina: Page,
) -> list[dict[str, Any]]:
    """Procura elementos contendo palavras relevantes."""

    resultados: list[dict[str, Any]] = []
    elementos = pagina.locator("body *")
    quantidade = min(elementos.count(), 5_000)

    textos_ja_adicionados: set[str] = set()

    for indice in range(quantidade):
        try:
            elemento = elementos.nth(indice).element_handle()

            if elemento is None:
                continue

            if not elemento_visivel(elemento):
                continue

            texto = obter_texto_elemento(elemento)

            if not texto:
                continue

            texto_minusculo = texto.lower()

            palavras_encontradas = [
                palavra
                for palavra in PALAVRAS_IMPORTANTES
                if palavra in texto_minusculo
            ]

            if not palavras_encontradas:
                continue

            chave_unica = (
                f"{obter_tag_elemento(elemento)}|{texto[:300]}"
            )

            if chave_unica in textos_ja_adicionados:
                continue

            textos_ja_adicionados.add(chave_unica)

            resultados.append(
                {
                    "indice": indice,
                    "tag": obter_tag_elemento(elemento),
                    "texto": texto,
                    "palavras_encontradas": palavras_encontradas,
                    "atributos": ler_atributos(elemento),
                    "html_resumido": obter_html_resumido(elemento),
                }
            )

        except Exception:
            continue

    return resultados


def mapear_frames(
    pagina: Page,
) -> list[dict[str, Any]]:
    """Lista os frames e iframes presentes na página."""

    resultados: list[dict[str, Any]] = []

    for indice, frame in enumerate(pagina.frames):
        try:
            resultados.append(
                {
                    "indice": indice,
                    "nome": frame.name,
                    "url": frame.url,
                }
            )
        except Exception as erro:
            resultados.append(
                {
                    "indice": indice,
                    "erro": str(erro),
                }
            )

    return resultados


def montar_relatorio(
    pagina: Page,
) -> dict[str, Any]:
    """Executa o mapeamento completo da página."""

    print()
    print("Mapeando frames...")
    frames = mapear_frames(pagina)

    print("Mapeando botões...")
    botoes = mapear_elementos(
        pagina,
        seletor='button, [role="button"]',
        categoria="botao",
    )

    print("Mapeando campos de entrada...")
    campos = mapear_elementos(
        pagina,
        seletor=(
            "input, textarea, select, "
            '[contenteditable="true"], '
            '[role="textbox"], '
            '[role="searchbox"], '
            '[role="combobox"]'
        ),
        categoria="campo",
    )

    print("Mapeando links...")
    links = mapear_elementos(
        pagina,
        seletor="a[href]",
        categoria="link",
    )

    print("Mapeando elementos com data-testid...")
    testids = mapear_elementos(
        pagina,
        seletor=(
            "[data-testid], "
            "[data-test-id], "
            "[data-id], "
            "[data-component]"
        ),
        categoria="elemento_identificado",
    )

    print("Mapeando elementos ARIA...")
    elementos_aria = mapear_elementos(
        pagina,
        seletor=(
            "[aria-label], "
            "[aria-labelledby], "
            "[aria-describedby], "
            "[aria-expanded], "
            "[aria-haspopup], "
            "[role]"
        ),
        categoria="elemento_aria",
    )

    print("Procurando palavras importantes...")
    textos_importantes = mapear_textos_importantes(pagina)

    try:
        titulo = pagina.title()
    except Exception:
        titulo = "Título indisponível"

    return {
        "gerado_em": datetime.now().isoformat(),
        "pagina": {
            "url": pagina.url,
            "titulo": titulo,
        },
        "resumo": {
            "frames": len(frames),
            "botoes": len(botoes),
            "campos": len(campos),
            "links": len(links),
            "elementos_testid": len(testids),
            "elementos_aria": len(elementos_aria),
            "textos_importantes": len(textos_importantes),
        },
        "frames": frames,
        "botoes": botoes,
        "campos": campos,
        "links": links,
        "elementos_testid": testids,
        "elementos_aria": elementos_aria,
        "textos_importantes": textos_importantes,
    }


def formatar_atributos(
    atributos: dict[str, str],
) -> str:
    """Formata atributos para o relatório de texto."""

    if not atributos:
        return "Nenhum atributo relevante"

    linhas = []

    for nome, valor in atributos.items():
        linhas.append(f"      {nome}: {valor}")

    return "\n".join(linhas)


def formatar_secao(
    titulo: str,
    itens: list[dict[str, Any]],
) -> str:
    """Formata uma seção do relatório textual."""

    linhas: list[str] = []

    linhas.append("")
    linhas.append("=" * 100)
    linhas.append(titulo)
    linhas.append("=" * 100)
    linhas.append("")

    if not itens:
        linhas.append("Nenhum elemento encontrado.")
        return "\n".join(linhas)

    for numero, item in enumerate(itens, start=1):
        linhas.append(f"[{numero}]")

        if "erro" in item:
            linhas.append(f"  ERRO: {item['erro']}")
            linhas.append("")
            continue

        if "categoria" in item:
            linhas.append(
                f"  Categoria: {item.get('categoria', '')}"
            )

        linhas.append(
            f"  Índice original: {item.get('indice', '')}"
        )
        linhas.append(f"  Tag: {item.get('tag', '')}")

        if "visivel" in item:
            linhas.append(
                f"  Visível: {item.get('visivel', '')}"
            )

        if item.get("texto"):
            linhas.append(f"  Texto: {item['texto']}")

        if item.get("palavras_encontradas"):
            linhas.append(
                "  Palavras encontradas: "
                + ", ".join(item["palavras_encontradas"])
            )

        linhas.append("  Atributos:")
        linhas.append(
            formatar_atributos(
                item.get("atributos", {})
            )
        )

        if item.get("html_resumido"):
            linhas.append("  HTML resumido:")
            linhas.append(
                f"      {item['html_resumido']}"
            )

        linhas.append("")

    return "\n".join(linhas)


def salvar_relatorios(
    relatorio: dict[str, Any],
    pagina: Page,
) -> tuple[Path, Path, Path]:
    """Salva relatório JSON, TXT e captura de tela."""

    PASTA_RELATORIOS.mkdir(
        parents=True,
        exist_ok=True,
    )

    horario = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    caminho_json = PASTA_RELATORIOS / (
        f"{NOME_BASE_RELATORIO}_{horario}.json"
    )

    caminho_txt = PASTA_RELATORIOS / (
        f"{NOME_BASE_RELATORIO}_{horario}.txt"
    )

    caminho_imagem = PASTA_RELATORIOS / (
        f"{NOME_BASE_RELATORIO}_{horario}.png"
    )

    with caminho_json.open(
        "w",
        encoding="utf-8",
    ) as arquivo_json:
        json.dump(
            relatorio,
            arquivo_json,
            ensure_ascii=False,
            indent=2,
        )

    linhas_txt: list[str] = []

    linhas_txt.append(
        "MAPA DA PÁGINA DO MERCADO LIVRE"
    )
    linhas_txt.append("=" * 100)
    linhas_txt.append("")
    linhas_txt.append(
        f"Gerado em: {relatorio['gerado_em']}"
    )
    linhas_txt.append(
        f"Título: {relatorio['pagina']['titulo']}"
    )
    linhas_txt.append(
        f"URL: {relatorio['pagina']['url']}"
    )
    linhas_txt.append("")
    linhas_txt.append("RESUMO")
    linhas_txt.append("-" * 100)

    for nome, quantidade in relatorio["resumo"].items():
        linhas_txt.append(
            f"{nome}: {quantidade}"
        )

    linhas_txt.append(
        formatar_secao(
            "FRAMES",
            relatorio["frames"],
        )
    )

    linhas_txt.append(
        formatar_secao(
            "BOTÕES",
            relatorio["botoes"],
        )
    )

    linhas_txt.append(
        formatar_secao(
            "CAMPOS",
            relatorio["campos"],
        )
    )

    linhas_txt.append(
        formatar_secao(
            "LINKS",
            relatorio["links"],
        )
    )

    linhas_txt.append(
        formatar_secao(
            "ELEMENTOS COM IDENTIFICADORES",
            relatorio["elementos_testid"],
        )
    )

    linhas_txt.append(
        formatar_secao(
            "ELEMENTOS ARIA",
            relatorio["elementos_aria"],
        )
    )

    linhas_txt.append(
        formatar_secao(
            "TEXTOS IMPORTANTES",
            relatorio["textos_importantes"],
        )
    )

    with caminho_txt.open(
        "w",
        encoding="utf-8",
    ) as arquivo_txt:
        arquivo_txt.write(
            "\n".join(linhas_txt)
        )

    try:
        pagina.screenshot(
            path=str(caminho_imagem),
            full_page=True,
            timeout=30_000,
        )
    except Exception as erro:
        print()
        print(
            "Não foi possível salvar a captura completa "
            f"da página: {erro}"
        )

    return (
        caminho_json,
        caminho_txt,
        caminho_imagem,
    )


def mostrar_resumo(
    relatorio: dict[str, Any],
) -> None:
    """Mostra um resumo do mapeamento no terminal."""

    print()
    print("=" * 60)
    print("RESUMO DO MAPEAMENTO")
    print("=" * 60)
    print()

    for nome, quantidade in relatorio["resumo"].items():
        print(f"{nome}: {quantidade}")

    print()
    print("Textos importantes encontrados:")
    print()

    textos_importantes = relatorio[
        "textos_importantes"
    ]

    if not textos_importantes:
        print(
            "Nenhum texto relevante foi encontrado."
        )
        return

    for indice, item in enumerate(
        textos_importantes[:30],
        start=1,
    ):
        texto = item.get("texto", "")
        palavras = ", ".join(
            item.get(
                "palavras_encontradas",
                [],
            )
        )

        print(f"[{indice}] {texto}")
        print(f"    Palavras: {palavras}")
        print()


def executar_teste(
    playwright: Playwright,
) -> None:
    """Conecta ao Chrome e mapeia a página atual."""

    print("=" * 60)
    print("Scanner da página do Mercado Livre")
    print("=" * 60)
    print()
    print(
        f"Conectando ao Chrome em: {ENDERECO_CDP}"
    )

    browser = playwright.chromium.connect_over_cdp(
        ENDERECO_CDP,
        timeout=30_000,
    )

    contexto = obter_contexto(browser)

    listar_paginas(contexto)

    pagina = escolher_pagina_mercado_livre(
        contexto
    )

    pagina.bring_to_front()

    print("Página escolhida:")
    print(pagina.url)
    print()

    try:
        pagina.wait_for_load_state(
            "domcontentloaded",
            timeout=15_000,
        )
    except PlaywrightTimeoutError:
        print(
            "Aviso: a página não confirmou o carregamento, "
            "mas o mapeamento continuará."
        )

    pagina.wait_for_timeout(2_000)

    relatorio = montar_relatorio(pagina)

    mostrar_resumo(relatorio)

    caminhos = salvar_relatorios(
        relatorio,
        pagina,
    )

    print()
    print("=" * 60)
    print("RELATÓRIOS SALVOS")
    print("=" * 60)
    print()
    print(f"JSON: {caminhos[0].resolve()}")
    print(f"TXT:  {caminhos[1].resolve()}")
    print(f"PNG:  {caminhos[2].resolve()}")
    print()

    input(
        "Pressione ENTER para encerrar o scanner..."
    )


def main() -> None:
    try:
        with sync_playwright() as playwright:
            executar_teste(playwright)

    except Exception as erro:
        print()
        print("=" * 60)
        print("FALHA NO MAPEAMENTO")
        print("=" * 60)
        print()
        print(f"Tipo: {type(erro).__name__}")
        print(f"Detalhes: {erro}")
        print()
        print(
            "Confirme se o Chrome dedicado está aberto "
            "com a porta 9222 e se a Central de Afiliados "
            "está visível."
        )
        raise


if __name__ == "__main__":
    main()