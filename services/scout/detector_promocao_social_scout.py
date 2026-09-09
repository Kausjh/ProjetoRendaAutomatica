# 63.8738, -149.7525

from __future__ import annotations

import re
from urllib.parse import urlparse

from models.mensagem_social_scout import MensagemSocialScout
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)


class DetectorPromocaoSocialScout:
    OFERTA_PRODUTO = "oferta_produto"
    CUPOM_GERAL = "cupom_geral"
    IGNORAR = "ignorar"

    _PADRAO_MOEDA = r"R\$\s*([\d.]+(?:,\d{2})?)"

    _PADRAO_PRECO_GENERICO = re.compile(
        _PADRAO_MOEDA,
        flags=re.IGNORECASE,
    )

    _PADRAO_PRECO_ORIGINAL = re.compile(
        rf"\bDe\s*:\s*{_PADRAO_MOEDA}",
        flags=re.IGNORECASE,
    )

    _PADRAO_PRECO_OFERTA = re.compile(
        rf"\bPor\s*:\s*{_PADRAO_MOEDA}",
        flags=re.IGNORECASE,
    )

    _PADRAO_PRECO_CUPOM = re.compile(
        rf"{_PADRAO_MOEDA}\s*[-??]\s*" r".{0,50}?\bcupom\b",
        flags=re.IGNORECASE,
    )

    _PADRAO_DESCONTO_ANUNCIADO = re.compile(
        r"\((\d+(?:[.,]\d+)?)\s*%\s*OFF\)",
        flags=re.IGNORECASE,
    )

    _PADRAO_DESCONTO_CUPOM = re.compile(
        r"\bcupom\s+[A-Z0-9_-]+\s+de\s+" r"(\d+(?:[.,]\d+)?)\s*%\s*OFF",
        flags=re.IGNORECASE,
    )

    _PADRAO_CUPOM_ESPECIFICO = re.compile(
        r"\bcupom\s*:?\s*([A-Z0-9][A-Z0-9_-]{2,})",
        flags=re.IGNORECASE,
    )

    _PADRAO_CUPOM_GERAL = re.compile(
        r"R\$\s*[\d.]+(?:,\d{2})?\s*OFF\s+em\s+"
        r"R\$\s*[\d.]+(?:,\d{2})?\s*:\s*"
        r"([A-Z0-9][A-Z0-9_-]{2,})",
        flags=re.IGNORECASE,
    )

    @classmethod
    def detectar(
        cls,
        mensagem: MensagemSocialScout,
    ) -> ResultadoDeteccaoSocialScout:
        texto = mensagem.texto.strip()

        if not texto:
            return cls._ignorar(
                mensagem,
                "Mensagem sem texto.",
            )

        linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]

        if not linhas:
            return cls._ignorar(
                mensagem,
                "Mensagem sem conteudo textual util.",
            )

        titulo = linhas[0]
        marketplace = cls._detectar_marketplace(
            texto=texto,
            links=mensagem.links,
        )

        cupons_gerais = cls._extrair_cupons_gerais(texto)

        if cls._parece_cupom_geral(
            titulo=titulo,
            texto=texto,
            cupons=cupons_gerais,
        ):
            return ResultadoDeteccaoSocialScout(
                classificacao=cls.CUPOM_GERAL,
                utilizavel=True,
                titulo=titulo,
                marketplace=marketplace,
                cupons=cupons_gerais,
                links=mensagem.links,
                motivo=("Mensagem reconhecida como campanha " "ou conjunto geral de cupons."),
            )

        preco_original = cls._extrair_moeda(
            cls._PADRAO_PRECO_ORIGINAL,
            texto,
        )

        preco_oferta = cls._extrair_moeda(
            cls._PADRAO_PRECO_OFERTA,
            texto,
        )

        preco_com_cupom = cls._extrair_moeda(
            cls._PADRAO_PRECO_CUPOM,
            texto,
        )

        if preco_oferta is None and preco_com_cupom is None and preco_original is None:
            preco_oferta = cls._extrair_moeda(
                cls._PADRAO_PRECO_GENERICO,
                texto,
            )

        codigo_cupom = cls._extrair_primeiro(
            cls._PADRAO_CUPOM_ESPECIFICO,
            texto,
        )

        desconto_anunciado = cls._extrair_decimal(
            cls._PADRAO_DESCONTO_ANUNCIADO,
            texto,
        )

        desconto_cupom = cls._extrair_decimal(
            cls._PADRAO_DESCONTO_CUPOM,
            texto,
        )

        preco_final = preco_com_cupom if preco_com_cupom is not None else preco_oferta

        tem_indicio_preco = preco_oferta is not None or preco_com_cupom is not None

        tem_link = bool(mensagem.links)

        if tem_indicio_preco and tem_link:
            return ResultadoDeteccaoSocialScout(
                classificacao=cls.OFERTA_PRODUTO,
                utilizavel=True,
                titulo=titulo,
                marketplace=marketplace,
                preco_original=preco_original,
                preco_oferta=preco_oferta,
                preco_final=preco_final,
                desconto_anunciado_percentual=(desconto_anunciado),
                desconto_cupom_percentual=(desconto_cupom),
                codigo_cupom=codigo_cupom,
                cupons=((codigo_cupom,) if codigo_cupom else ()),
                links=mensagem.links,
                motivo=("Mensagem contem preco e link, " "compativel com oferta de produto."),
            )

        return cls._ignorar(
            mensagem,
            "Mensagem nao possui sinais suficientes " "de oferta de produto ou campanha geral.",
            titulo=titulo,
            marketplace=marketplace,
        )

    @classmethod
    def _parece_cupom_geral(
        cls,
        *,
        titulo: str,
        texto: str,
        cupons: tuple[str, ...],
    ) -> bool:
        titulo_normalizado = re.sub(
            r"^[^\w]+",
            "",
            titulo.casefold(),
        ).strip()

        if re.match(
            r"^(?:(?:novo|novos)\s+)?" r"(?:cupom|cupons)\b",
            titulo_normalizado,
        ):
            return True

        if len(cupons) >= 1:
            return True

        return False

    @classmethod
    def _extrair_cupons_gerais(
        cls,
        texto: str,
    ) -> tuple[str, ...]:
        resultado: list[str] = []

        for correspondencia in cls._PADRAO_CUPOM_GERAL.finditer(texto):
            codigo = correspondencia.group(1).strip().upper()

            if codigo not in resultado:
                resultado.append(codigo)

        return tuple(resultado)

    @staticmethod
    def _converter_moeda(
        valor: str,
    ) -> float:
        normalizado = valor.replace(".", "").replace(",", ".")

        return float(normalizado)

    @classmethod
    def _extrair_moeda(
        cls,
        padrao: re.Pattern[str],
        texto: str,
    ) -> float | None:
        correspondencia = padrao.search(texto)

        if correspondencia is None:
            return None

        return cls._converter_moeda(correspondencia.group(1))

    @staticmethod
    def _extrair_primeiro(
        padrao: re.Pattern[str],
        texto: str,
    ) -> str | None:
        correspondencia = padrao.search(texto)

        if correspondencia is None:
            return None

        return correspondencia.group(1).strip().upper()

    @staticmethod
    def _extrair_decimal(
        padrao: re.Pattern[str],
        texto: str,
    ) -> float | None:
        correspondencia = padrao.search(texto)

        if correspondencia is None:
            return None

        return float(correspondencia.group(1).replace(",", "."))

    @classmethod
    def _detectar_marketplace(
        cls,
        *,
        texto: str,
        links: tuple[str, ...],
    ) -> str | None:
        """Detecta a loja sem deixar links auxiliares contaminarem a oferta.

        Links de marketplaces suportados pelo Social Scout têm prioridade
        sobre links auxiliares de marketplaces ainda não suportados, como
        rodapés de Amazon Prime.

        Quando um encurtador não revela a loja, marcadores explícitos no
        texto podem identificar um marketplace suportado.
        """

        marketplaces_links: list[str] = []

        for link in links:
            try:
                dominio = (urlparse(str(link)).hostname or "").casefold()

            except ValueError:
                continue

            marketplace = None

            if (
                dominio == "meli.la"
                or dominio.endswith(".meli.la")
                or dominio == "mercadolivre.com.br"
                or dominio.endswith(".mercadolivre.com.br")
            ):
                marketplace = "mercado_livre"

            elif (
                dominio == "divulgadormagalu.com"
                or dominio == "magazineluiza.com.br"
                or dominio.endswith(".magazineluiza.com.br")
            ):
                marketplace = "magalu"

            elif dominio == "kabum.com.br" or dominio.endswith(".kabum.com.br"):
                marketplace = "kabum"

            elif (
                dominio == "amazon.com.br"
                or dominio.endswith(".amazon.com.br")
                or dominio == "amzn.to"
                or dominio == "link.amazon"
            ):
                marketplace = "amazon"

            elif dominio == "shopee.com.br" or dominio.endswith(".shopee.com.br"):
                marketplace = "shopee"

            elif dominio == "aliexpress.com" or dominio.endswith(".aliexpress.com"):
                marketplace = "aliexpress"

            if marketplace is not None and marketplace not in marketplaces_links:
                marketplaces_links.append(marketplace)

        suportados = {
            "mercado_livre",
            "shopee",
            "aliexpress",
            "kabum",
        }

        # Primeiro: qualquer link de marketplace realmente suportado.
        for marketplace in marketplaces_links:
            if marketplace in suportados:
                return marketplace

        texto_normalizado = texto.casefold()

        # Segundo: texto explícito de marketplace suportado.
        # Isso recupera, por exemplo:
        #   "ALERTA de Cupom kabum! ... Amazon Prime ..."
        # quando o link KaBuM está encurtado e o rodapé possui URL Amazon.
        marcadores_suportados = (
            ("mercado livre", "mercado_livre"),
            ("shopee", "shopee"),
            ("aliexpress", "aliexpress"),
            ("kabum", "kabum"),
        )

        for marcador, marketplace in marcadores_suportados:
            if marcador in texto_normalizado:
                return marketplace

        # Terceiro: marketplaces reconhecidos mas ainda sem processador.
        for marketplace in marketplaces_links:
            if marketplace in {
                "magalu",
                "amazon",
            }:
                return marketplace

        if "magalu" in texto_normalizado:
            return "magalu"

        if "amazon" in texto_normalizado:
            return "amazon"

        return None

    @classmethod
    def _ignorar(
        cls,
        mensagem: MensagemSocialScout,
        motivo: str,
        *,
        titulo: str = "",
        marketplace: str | None = None,
    ) -> ResultadoDeteccaoSocialScout:
        return ResultadoDeteccaoSocialScout(
            classificacao=cls.IGNORAR,
            utilizavel=False,
            titulo=titulo,
            marketplace=marketplace,
            links=mensagem.links,
            motivo=motivo,
        )
