# 63.8738, -149.7525

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoPrecoAliExpress:
    produto_id: str
    preco_brl: float | None
    moeda: str | None
    url_produto: str | None
    valido: bool
    motivo: str

    preco_normal_brl: float | None = None
    moeda_normal: str | None = None

    preco_promocional_brl: float | None = None
    moeda_promocional: str | None = None

    preco_novo_usuario_brl: float | None = None
    moeda_novo_usuario: str | None = None

    promocao_novo_usuario: bool = False
    sku_id: str | None = None

    @property
    def preco(self) -> float | None:
        if not self.valido:
            return None

        return self.preco_brl

    @property
    def preco_normal(self) -> float | None:
        return self.preco_normal_brl

    @property
    def preco_promocional(self) -> float | None:
        return self.preco_promocional_brl

    @property
    def preco_novo_usuario(self) -> float | None:
        return self.preco_novo_usuario_brl


class ValidadorPrecoAliExpress:
    def validar_html(
        self,
        produto_id: str,
        url_final: str,
        html: str,
        pdp_texto: str | None = None,
        exigir_pdp: bool = False,
    ) -> ResultadoPrecoAliExpress:
        produto_id = str(produto_id).strip()

        if not produto_id:
            return self._rejeitar(
                produto_id,
                "produto_id ausente",
            )

        if not produto_id.isdigit():
            return self._rejeitar(
                produto_id,
                "produto_id invalido",
            )

        if not _url_aliexpress(url_final):
            return self._rejeitar(
                produto_id,
                ("pagina final nao pertence " "ao AliExpress"),
            )

        if not _url_contem_produto(
            url_final,
            produto_id,
        ):
            return self._rejeitar(
                produto_id,
                ("produto_id diverge da " "pagina final"),
            )

        oferta_json_ld = _extrair_oferta_json_ld(
            html=html,
            produto_id=produto_id,
        )

        if oferta_json_ld is None:
            return self._rejeitar(
                produto_id,
                ("preco BRL confiavel nao " "encontrado no JSON-LD"),
            )

        (
            preco_json_ld,
            url_json_ld,
        ) = oferta_json_ld

        if pdp_texto is None:
            if exigir_pdp:
                return self._rejeitar(
                    produto_id,
                    ("resposta PDP nao foi " "capturada"),
                )

            return ResultadoPrecoAliExpress(
                produto_id=produto_id,
                preco_brl=preco_json_ld,
                moeda="BRL",
                url_produto=(url_json_ld or url_final),
                valido=True,
                motivo=("preco BRL confirmado " "por JSON-LD"),
            )

        dados_pdp = _carregar_json_pdp(pdp_texto)

        if dados_pdp is None:
            if exigir_pdp:
                return self._rejeitar(
                    produto_id,
                    ("resposta PDP invalida " "ou nao interpretavel"),
                )

            return ResultadoPrecoAliExpress(
                produto_id=produto_id,
                preco_brl=preco_json_ld,
                moeda="BRL",
                url_produto=(url_json_ld or url_final),
                valido=True,
                motivo=("preco BRL confirmado " "por JSON-LD; PDP invalida"),
            )

        return self._validar_com_pdp(
            produto_id=produto_id,
            url_final=(url_json_ld or url_final),
            preco_json_ld=(preco_json_ld),
            dados_pdp=dados_pdp,
        )

    def _validar_com_pdp(
        self,
        produto_id: str,
        url_final: str,
        preco_json_ld: float,
        dados_pdp: object,
    ) -> ResultadoPrecoAliExpress:
        if not isinstance(
            dados_pdp,
            dict,
        ):
            return self._rejeitar(
                produto_id,
                "estrutura PDP invalida",
            )

        resultado = dados_pdp.get("data", {}).get("result", {})

        if not isinstance(
            resultado,
            dict,
        ):
            return self._rejeitar(
                produto_id,
                ("resultado PDP " "nao encontrado"),
            )

        price = resultado.get(
            "PRICE",
            {},
        )

        if not isinstance(
            price,
            dict,
        ):
            price = {}

        sku_id = _texto(price.get("selectedSkuId")) or None

        product_id_pdp = _texto(price.get("productId"))

        if product_id_pdp and product_id_pdp != produto_id:
            return self._rejeitar(
                produto_id,
                ("produto_id diverge " "da resposta PDP"),
            )

        target = price.get(
            "targetSkuPriceInfo",
            {},
        )

        if not isinstance(
            target,
            dict,
        ):
            target = {}

        original = target.get(
            "originalPrice",
            {},
        )

        if not isinstance(
            original,
            dict,
        ):
            original = {}

        moeda_normal = _texto(original.get("currency")).upper() or None

        preco_normal = _decimal_positivo(original.get("value"))

        preco_sale = _extrair_preco_brl_formatado(target.get("salePriceString"))

        if preco_sale is not None and abs(preco_sale - preco_json_ld) > 0.05:
            return self._rejeitar(
                produto_id,
                ("preco JSON-LD diverge " "do SKU selecionado"),
            )

        promocao_novo_usuario = _promocao_exclusiva_novo_usuario(resultado)

        if promocao_novo_usuario:
            if preco_normal is None or moeda_normal != "BRL":
                return self._rejeitar(
                    produto_id,
                    ("promocao de novo usuario " "detectada sem preco normal " "BRL confiavel"),
                )

            return ResultadoPrecoAliExpress(
                produto_id=produto_id,
                preco_brl=preco_normal,
                moeda="BRL",
                url_produto=url_final,
                valido=True,
                motivo=(
                    "preco normal BRL confirmado; "
                    "preco de novo usuario "
                    "preservado separadamente"
                ),
                preco_normal_brl=(preco_normal),
                moeda_normal="BRL",
                preco_promocional_brl=(preco_json_ld),
                moeda_promocional="BRL",
                preco_novo_usuario_brl=(preco_json_ld),
                moeda_novo_usuario="BRL",
                promocao_novo_usuario=True,
                sku_id=sku_id,
            )

        preco_promocional = None
        moeda_promocional = None

        if (
            preco_normal is not None
            and moeda_normal == "BRL"
            and preco_json_ld < preco_normal - 0.01
        ):
            preco_promocional = preco_json_ld
            moeda_promocional = "BRL"

        return ResultadoPrecoAliExpress(
            produto_id=produto_id,
            preco_brl=preco_json_ld,
            moeda="BRL",
            url_produto=url_final,
            valido=True,
            motivo=("preco atual BRL confirmado " "para o SKU selecionado"),
            preco_normal_brl=(preco_normal if moeda_normal == "BRL" else None),
            moeda_normal=("BRL" if (preco_normal is not None and moeda_normal == "BRL") else None),
            preco_promocional_brl=(preco_promocional),
            moeda_promocional=(moeda_promocional),
            preco_novo_usuario_brl=None,
            moeda_novo_usuario=None,
            promocao_novo_usuario=False,
            sku_id=sku_id,
        )

    @staticmethod
    def _rejeitar(
        produto_id: str,
        motivo: str,
    ) -> ResultadoPrecoAliExpress:
        return ResultadoPrecoAliExpress(
            produto_id=produto_id,
            preco_brl=None,
            moeda=None,
            url_produto=None,
            valido=False,
            motivo=motivo,
        )


class _JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)

        self._capturando = False
        self._partes: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:
        if tag.lower() != "script":
            return

        atributos = {str(chave).lower(): str(valor or "").lower() for chave, valor in attrs}

        if atributos.get("type") == "application/ld+json":
            self._capturando = True
            self._partes = []

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._capturando:
            self._partes.append(data)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if tag.lower() != "script" or not self._capturando:
            return

        bruto = "".join(self._partes).strip()

        if bruto:
            self.scripts.append(bruto)

        self._capturando = False
        self._partes = []


def _extrair_oferta_json_ld(
    html: str,
    produto_id: str,
) -> tuple[float, str | None] | None:
    parser = _JsonLdParser()

    try:
        parser.feed(html or "")
    except Exception:
        return None

    for bruto in parser.scripts:
        try:
            dados = json.loads(bruto)
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            continue

        for objeto in _percorrer_json(dados):
            if not isinstance(
                objeto,
                dict,
            ):
                continue

            ofertas = objeto.get("offers")

            for oferta in _normalizar_ofertas(ofertas):
                moeda = _texto(oferta.get("priceCurrency")).upper()

                if moeda != "BRL":
                    continue

                preco = _decimal_positivo(oferta.get("price"))

                if preco is None:
                    continue

                url = _texto(oferta.get("url"))

                if url:
                    if not _url_aliexpress(url):
                        continue

                    if not _url_contem_produto(
                        url,
                        produto_id,
                    ):
                        continue

                return (
                    preco,
                    url or None,
                )

    return None


def _carregar_json_pdp(
    texto: str,
) -> object | None:
    texto = str(texto or "").strip()

    if not texto:
        return None

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if inicio < 0 or fim <= inicio:
        return None

    try:
        return json.loads(texto[inicio : fim + 1])
    except json.JSONDecodeError:
        return None


def _promocao_exclusiva_novo_usuario(
    resultado: dict,
) -> bool:
    banner = resultado.get(
        "PRICE_BANNER",
        {},
    )

    if not isinstance(
        banner,
        dict,
    ):
        return False

    textos: list[str] = []

    for chave in (
        "atmosphereCode",
        "supplementaryText",
    ):
        valor = banner.get(chave)

        if valor is not None:
            textos.append(str(valor))

    target = banner.get(
        "targetSkuBanner",
        {},
    )

    if isinstance(
        target,
        dict,
    ):
        for chave in (
            "atmosphereCode",
            "supplementaryText",
        ):
            valor = target.get(chave)

            if valor is not None:
                textos.append(str(valor))

    conjunto = " ".join(textos).casefold()

    indicadores = (
        "new_user",
        "new-user",
        "new user",
        "novo usu?rio",
        "novo usuario",
        "novo comprador",
    )

    return any(indicador in conjunto for indicador in indicadores)


def _extrair_preco_brl_formatado(
    valor: object,
) -> float | None:
    texto = _texto(valor)

    if not texto:
        return None

    achado = re.search(
        r"R\$\s*" r"(\d+(?:\.\d{3})*(?:,\d{1,2})?)",
        texto,
    )

    if not achado:
        return None

    numero = achado.group(1).replace(".", "").replace(",", ".")

    return _decimal_positivo(numero)


def _percorrer_json(
    valor: object,
):
    yield valor

    if isinstance(
        valor,
        dict,
    ):
        for filho in valor.values():
            yield from _percorrer_json(filho)

    elif isinstance(
        valor,
        list,
    ):
        for filho in valor:
            yield from _percorrer_json(filho)


def _normalizar_ofertas(
    ofertas: object,
) -> list[dict]:
    if isinstance(
        ofertas,
        dict,
    ):
        return [ofertas]

    if isinstance(
        ofertas,
        list,
    ):
        return [
            item
            for item in ofertas
            if isinstance(
                item,
                dict,
            )
        ]

    return []


def _texto(
    valor: object,
) -> str:
    if valor is None:
        return ""

    return str(valor).strip()


def _decimal_positivo(
    valor: object,
) -> float | None:
    texto = _texto(valor)

    if not texto:
        return None

    try:
        numero = float(texto)
    except (
        TypeError,
        ValueError,
    ):
        return None

    if numero <= 0:
        return None

    return round(
        numero,
        2,
    )


def _url_aliexpress(
    url: str,
) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False

    return host == "aliexpress.com" or host.endswith(".aliexpress.com")


def _url_contem_produto(
    url: str,
    produto_id: str,
) -> bool:
    try:
        caminho = urlparse(url).path.lower()
    except ValueError:
        return False

    return f"/item/{produto_id}.html" in caminho
