from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

PADRAO_DINHEIRO = re.compile(
    r"R\$\s*([\d.]+(?:,\d{1,2})?)",
    flags=re.IGNORECASE,
)

PADRAO_DESCONTO = re.compile(
    r"(\d{1,3})\s*%\s*(?:OFF)?",
    flags=re.IGNORECASE,
)


def limpar_espacos(texto: str | None) -> str:
    if not texto:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(texto),
    ).strip()


def converter_numero_brasileiro(
    valor: str | int | float | None,
) -> float | None:
    if valor is None:
        return None

    if isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float)):
        numero = float(valor)

        if numero <= 0:
            return None

        return numero

    texto = limpar_espacos(str(valor))

    if not texto:
        return None

    texto = texto.replace("R$", "")
    texto = texto.replace("%", "")
    texto = texto.replace(" ", "")

    if "," in texto and "." in texto:
        texto = texto.replace(".", "")
        texto = texto.replace(",", ".")

    elif "," in texto:
        texto = texto.replace(",", ".")

    texto = re.sub(
        r"[^0-9.\-]",
        "",
        texto,
    )

    if not texto:
        return None

    try:
        numero = float(texto)
    except ValueError:
        return None

    if numero <= 0:
        return None

    return round(numero, 2)


def extrair_precos_monetarios(
    texto: str | None,
) -> list[float]:
    texto_limpo = limpar_espacos(texto)

    if not texto_limpo:
        return []

    precos: list[float] = []

    for correspondencia in PADRAO_DINHEIRO.finditer(texto_limpo):
        numero = converter_numero_brasileiro(correspondencia.group(1))

        if numero is None:
            continue

        if numero not in precos:
            precos.append(numero)

    return precos


def extrair_preco(
    texto: str | int | float | None,
) -> float | None:
    if isinstance(texto, (int, float)):
        return converter_numero_brasileiro(texto)

    precos = extrair_precos_monetarios(str(texto or ""))

    if precos:
        return precos[0]

    return converter_numero_brasileiro(texto)


def extrair_desconto(
    texto: str | int | float | None,
) -> float | None:
    if texto is None:
        return None

    if isinstance(texto, (int, float)):
        desconto = float(texto)
    else:
        texto_limpo = limpar_espacos(str(texto))

        correspondencia = PADRAO_DESCONTO.search(texto_limpo)

        if not correspondencia:
            return None

        desconto = float(correspondencia.group(1))

    if desconto <= 0 or desconto >= 100:
        return None

    return round(desconto, 2)


def calcular_desconto(
    preco_atual: float | None,
    preco_anterior: float | None,
) -> float | None:
    if preco_atual is None:
        return None

    if preco_anterior is None:
        return None

    if preco_atual <= 0:
        return None

    if preco_anterior <= preco_atual:
        return None

    desconto = ((preco_anterior - preco_atual) / preco_anterior) * 100

    if desconto <= 0 or desconto >= 100:
        return None

    return round(desconto, 2)


def inferir_preco_anterior(
    texto_card: str | None,
    preco_atual: float | None,
) -> float | None:
    if preco_atual is None:
        return None

    precos = extrair_precos_monetarios(texto_card)

    candidatos = [preco for preco in precos if preco > preco_atual]

    if not candidatos:
        return None

    return min(candidatos)


def extrair_id_produto(
    link: str | None,
) -> str:
    link_limpo = limpar_espacos(link)

    if not link_limpo:
        return ""

    padroes = (
        r"\b(MLB[-_]?\d+)\b",
        r"/p/(MLB\d+)",
        r"/(MLB\d+)",
    )

    for padrao in padroes:
        correspondencia = re.search(
            padrao,
            link_limpo,
            flags=re.IGNORECASE,
        )

        if correspondencia:
            return correspondencia.group(1).replace("-", "").replace("_", "").upper()

    return ""


def normalizar_link(
    link: str | None,
) -> str:
    link_limpo = limpar_espacos(link)

    if not link_limpo:
        return ""

    if link_limpo.startswith("//"):
        link_limpo = f"https:{link_limpo}"

    if not link_limpo.startswith(("http://", "https://")):
        return link_limpo

    partes = urlsplit(link_limpo)

    return urlunsplit(
        (
            partes.scheme,
            partes.netloc,
            partes.path,
            partes.query,
            "",
        )
    )


def criar_chave_unica(
    produto: dict[str, Any],
) -> str:
    produto_id = limpar_espacos(
        str(produto.get("id_produto") or produto.get("produto_id") or produto.get("id") or "")
    )

    if produto_id:
        return f"id:{produto_id.lower()}"

    link = normalizar_link(str(produto.get("link") or produto.get("url") or ""))

    if link:
        link_sem_parametros = link.split("?")[0]

        return "link:" f"{link_sem_parametros.lower()}"

    titulo = limpar_espacos(
        str(produto.get("titulo") or produto.get("nome") or produto.get("title") or "")
    ).lower()

    preco = produto.get("preco")

    if titulo:
        return f"titulo:{titulo}|" f"preco:{preco}"

    return ""


def montar_produto(
    titulo: str,
    preco_texto: str,
    link: str,
    imagem: str,
    categoria: str,
    preco_anterior_texto: str = "",
    desconto_texto: str = "",
    texto_card: str = "",
) -> dict[str, Any]:
    titulo_limpo = limpar_espacos(titulo)
    link_normalizado = normalizar_link(link)
    imagem_limpa = limpar_espacos(imagem)
    categoria_limpa = limpar_espacos(categoria)

    preco_atual = extrair_preco(preco_texto)

    preco_anterior = extrair_preco(preco_anterior_texto)

    if preco_anterior is None:
        preco_anterior = inferir_preco_anterior(
            texto_card=texto_card,
            preco_atual=preco_atual,
        )

    if preco_atual is not None and preco_anterior is not None and preco_anterior <= preco_atual:
        preco_anterior = None

    desconto = extrair_desconto(desconto_texto)

    if desconto is None:
        desconto = extrair_desconto(texto_card)

    if desconto is None:
        desconto = calcular_desconto(
            preco_atual=preco_atual,
            preco_anterior=preco_anterior,
        )

    produto = {
        "id_produto": extrair_id_produto(link_normalizado),
        "titulo": titulo_limpo,
        "preco": preco_atual,
        "preco_anterior": preco_anterior,
        "desconto": desconto,
        "link": link_normalizado,
        "imagem": imagem_limpa,
        "categoria": categoria_limpa,
    }

    return produto
