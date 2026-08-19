# 63.8738, -149.7525

"""Limpeza de títulos de produtos vindos dos marketplaces."""

import re

LIMITE_CARACTERES = 85

_UNIDADES = [
    (r"\b(\d+)\s*gb\b", r"\1GB"),
    (r"\b(\d+)\s*tb\b", r"\1TB"),
    (r"\b(\d+)\s*mb\b", r"\1MB"),
    (r"\b(\d+)\s*w\b", r"\1W"),
    (r"\b(\d+)\s*hz\b", r"\1Hz"),
    (r"\b(\d+(?:[.,]\d+)?)\s*ghz\b", r"\1GHz"),
    (r"\b(\d+)\s*mhz\b", r"\1MHz"),
    (r"\b(\d+)\s*mh\b", r"\1MHz"),
    (r"\b(\d+)\s*ms\b", r"\1ms"),
    (r"\b(\d+)\s*mm\b", r"\1mm"),
    (r"\b(\d+)\s*bits?\b", r"\1 bits"),
    (r"\b(\d+)\s*dpi\b", r"\1 DPI"),
]

_SIGLAS = [
    "DDR5",
    "DDR4",
    "DDR3",
    "GDDR7",
    "GDDR6X",
    "GDDR6",
    "GDDR5",
    "NVMe",
    "SSD",
    "HDD",
    "RAM",
    "DIMM",
    "SODIMM",
    "UDIMM",
    "PCIe",
    "USB",
    "HDMI",
    "RGB",
    "ARGB",
    "ATX",
    "RTX",
    "GTX",
    "AMD",
    "Intel",
    "NVIDIA",
    "MSI",
    "ASUS",
    "XFX",
    "PNY",
    "TUF",
    "AORUS",
    "OC",
    "GeForce",
    "Radeon",
    "Ryzen",
    "AM4",
    "AM5",
    "LGA",
    "ABNT2",
    "TKL",
    "IPS",
    "VA",
    "OLED",
    "QHD",
    "FHD",
    "UHD",
    "4K",
    "PS4",
    "PS5",
    "Xbox",
    "PC",
    "TB",
    "GB",
]

_PREPOSICOES = {
    "de",
    "da",
    "do",
    "das",
    "dos",
    "com",
    "sem",
    "para",
    "por",
    "em",
    "e",
    "a",
    "o",
    "no",
    "na",
}

_LIXO_FINAL = {"cor", "oem", "nf-e", "novo", "original", "envio", "imediato"}

_PADRAO_CODIGO_PECA = re.compile(
    r"\b(?=[A-Za-z0-9/\-]*\d)(?=[A-Za-z0-9/\-]*[A-Za-z])[A-Za-z0-9]+(?:[/\-][A-Za-z0-9]+)+\b"
)


def limpar_titulo(titulo: str) -> str:
    """Devolve uma versão apresentável do título do produto."""

    texto = titulo.strip()

    if not texto:
        return ""

    texto = _remover_codigos_de_peca(texto)
    texto = _normalizar_unidades(texto)
    texto = _corrigir_preposicoes(texto)
    texto = _restaurar_siglas(texto)
    texto = _limpar_pontuacao_solta(texto)
    texto = _truncar(texto)

    return texto


def _remover_codigos_de_peca(texto: str) -> str:
    """Remove ruído do FIM do título.

    Códigos de peça (SKU) ficam no final; modelos de produto ficam no
    meio. Por isso a limpeza acontece apenas a partir da última palavra,
    preservando identificadores como 'I5-12400F' ou 'B550M-PLUS'.
    """

    palavras = texto.split()

    while palavras:
        ultimo = palavras[-1].strip(" .,-")

        if ultimo.lower() in _LIXO_FINAL:
            palavras.pop()
            continue

        if _parece_codigo_de_peca(ultimo):
            palavras.pop()
            continue

        break

    if not palavras:
        return texto.strip(" .,-")

    return " ".join(palavras).strip(" .,-")


def _parece_codigo_de_peca(trecho: str) -> bool:
    if len(trecho) < 6:
        return False

    tem_digito = any(caractere.isdigit() for caractere in trecho)
    tem_letra = any(caractere.isalpha() for caractere in trecho)

    if not (tem_digito and tem_letra):
        return False

    if _PADRAO_CODIGO_PECA.fullmatch(trecho):
        return True

    if trecho.isalnum() and len(trecho) >= 9:
        digitos = sum(1 for caractere in trecho if caractere.isdigit())
        return digitos >= 4

    return False


def _normalizar_unidades(texto: str) -> str:
    for padrao, substituicao in _UNIDADES:
        texto = re.sub(padrao, substituicao, texto, flags=re.IGNORECASE)

    return texto


def _corrigir_preposicoes(texto: str) -> str:
    palavras = texto.split()
    resultado: list[str] = []

    for indice, palavra in enumerate(palavras):
        if indice > 0 and palavra.lower() in _PREPOSICOES:
            resultado.append(palavra.lower())
        else:
            resultado.append(palavra)

    return " ".join(resultado)


def _restaurar_siglas(texto: str) -> str:
    for sigla in _SIGLAS:
        texto = re.sub(
            rf"\b{re.escape(sigla)}\b",
            sigla,
            texto,
            flags=re.IGNORECASE,
        )

    return texto


def _limpar_pontuacao_solta(texto: str) -> str:
    texto = re.sub(r"\s{2,}", " ", texto)
    texto = re.sub(r"\s+([.,])", r"\1", texto)
    texto = re.sub(r"[.,]{2,}", ".", texto)

    return texto.strip(" .,-")


def _truncar(texto: str) -> str:
    if len(texto) <= LIMITE_CARACTERES:
        return texto

    corte = texto[:LIMITE_CARACTERES].rsplit(" ", 1)[0]

    return f"{corte.strip(' .,-')}..."
