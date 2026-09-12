from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class CondicoesPromocionais:
    pix: bool = False
    app_only: bool = False
    vip: bool = False
    valor_minimo_compra: float | None = None
    expiracao: str | None = None

    def como_campos_validacao(self) -> dict[str, object]:
        return {
            "promocao_pix_marketplace": self.pix,
            "promocao_app_only_marketplace": self.app_only,
            "promocao_vip_marketplace": self.vip,
            "valor_minimo_compra_promocao_marketplace": (self.valor_minimo_compra),
            "expiracao_promocao_marketplace": self.expiracao,
        }


def interpretar_condicoes_promocionais(
    *,
    tipo_preco_oficial: str | None,
    preco_valido_ate: str | None,
    evidencia_oficial: str,
) -> CondicoesPromocionais:
    evidencia = str(evidencia_oficial or "").strip()
    normalizado = _normalizar(evidencia)
    tipo_preco = str(tipo_preco_oficial or "").strip().casefold()

    pix = tipo_preco == "pix" or bool(
        re.search(
            r"\b(?:no|via|com|por)\s+pix\b" r"|\bpreco\s+(?:no\s+)?pix\b",
            normalizado,
        )
    )

    app_only = bool(
        re.search(
            r"\b(?:somente|apenas|exclusiv[oa])\s+"
            r"(?:no|pelo|via|do)\s+app\b"
            r"|\bapp\s*[- ]?\s*only\b",
            normalizado,
        )
    )

    vip = bool(
        re.search(
            r"\b(?:shopee\s+)?vip\b" r"|\bcliente\s+vip\b",
            normalizado,
        )
    )

    minimo = _extrair_minimo(evidencia)

    expiracao = str(preco_valido_ate or "").strip() or None

    if expiracao is None:
        expiracao = _extrair_expiracao(evidencia)

    return CondicoesPromocionais(
        pix=pix,
        app_only=app_only,
        vip=vip,
        valor_minimo_compra=minimo,
        expiracao=expiracao,
    )


def _normalizar(texto: str) -> str:
    sem_acento = "".join(
        c
        for c in unicodedata.normalize(
            "NFKD",
            str(texto or ""),
        )
        if not unicodedata.combining(c)
    )

    return (
        re.sub(
            r"\s+",
            " ",
            sem_acento,
        )
        .strip()
        .casefold()
    )


def _dinheiro_br(valor: str) -> float | None:
    bruto = re.sub(
        r"\s+",
        "",
        str(valor or ""),
    )

    if not bruto:
        return None

    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    else:
        partes = bruto.split(".")

        if len(partes) > 1 and all(len(parte) == 3 for parte in partes[1:]):
            bruto = "".join(partes)

    try:
        numero = float(bruto)
    except ValueError:
        return None

    if numero <= 0:
        return None

    return round(numero, 2)


def _extrair_minimo(
    evidencia: str,
) -> float | None:
    padroes = (
        (r"(?:minimo|minima)" r"(?:\s+de\s+compra)?" r"\s*:?\s*R\$\s*" r"([\d.]+(?:,\d{2})?)"),
        (
            r"(?:compras?|pedidos?)\s+"
            r"(?:a\s+partir\s+de|acima\s+de|"
            r"maiores?\s+que)\s+"
            r"R\$\s*"
            r"([\d.]+(?:,\d{2})?)"
        ),
    )

    for padrao in padroes:
        match = re.search(
            padrao,
            evidencia,
            flags=re.IGNORECASE,
        )

        if match is not None:
            valor = _dinheiro_br(match.group(1))

            if valor is not None:
                return valor

    return None


def _extrair_expiracao(
    evidencia: str,
) -> str | None:
    padroes = (
        (
            r"\b(?:valido|valida|oferta)"
            r"\s+ate\s+"
            r"(\d{1,2}/\d{1,2}"
            r"(?:/\d{2,4})?"
            r"(?:\s+(?:as|ate)\s+"
            r"\d{1,2}(?::\d{2})?h?)?)"
        ),
        (
            r"\bexpira(?:\s+em|\s+as|\s*:)?\s*"
            r"(\d{1,2}/\d{1,2}"
            r"(?:/\d{2,4})?"
            r"(?:\s+(?:as|ate)\s+"
            r"\d{1,2}(?::\d{2})?h?)?)"
        ),
    )

    for padrao in padroes:
        match = re.search(
            padrao,
            evidencia,
            flags=re.IGNORECASE,
        )

        if match is not None:
            return match.group(1).strip()

    return None
