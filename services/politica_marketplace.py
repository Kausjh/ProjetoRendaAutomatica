# 63.8738, -149.7525

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True, slots=True)
class ResultadoPoliticaMarketplace:
    permitido: bool
    tier: str
    motivo: str


class PoliticaMarketplace:
    """Regua editorial especifica de cada marketplace."""

    TIER_NUCLEO = "nucleo"
    TIER_ADJACENTE = "adjacente"
    TIER_SECUNDARIO = "secundario"

    CATEGORIAS_NUCLEO = frozenset(
        {
            "Placa de vídeo",
            "Processador",
            "Placa-mãe",
            "Memória RAM",
            "Armazenamento",
            "Fonte e energia",
            "Gabinete",
            "Refrigeração de PC",
            "Monitor",
            "Notebook",
            "Computador e Mini PC",
            "Mouse e mousepad",
            "Teclado",
            "Áudio",
            "Microfone",
            "Controle",
            "Console",
            "Realidade virtual",
            "Rede",
            "Streaming e captura",
            "Simulação",
            "Suportes e conectividade",
            "Carregamento e mobilidade",
        }
    )

    CATEGORIAS_SECUNDARIAS = frozenset(
        {
            "Suplementos",
            "Energéticos",
            "Café",
            "Chocolate e snacks",
            "Climatização e conforto",
            "Automação doméstica",
        }
    )

    CATEGORIAS_ALIEXPRESS_PERMITIDAS = frozenset(
        {
            "Processador",
            "Memória RAM",
            "Armazenamento",
            "Refrigeração de PC",
            "Mouse e mousepad",
            "Teclado",
            "Áudio",
            "Microfone",
            "Controle",
            "Rede",
            "Streaming e captura",
            "Suportes e conectividade",
            "Carregamento e mobilidade",
            "Maker e bancada",
            "Celular",
            "Tablet e e-reader",
            "Wearables",
        }
    )

    RUIDOS_ALIEXPRESS = (
        "cocktail",
        "strainer",
        "bar tool",
        "kitchen tool",
        "kitchen utensil",
        "power inverter",
        "solar inverter",
        "car inverter",
        "distribution box",
        "junction box",
        "plastic enclosure",
        "office home media",
    )

    MARCADORES_QUALIDADE_ALIEXPRESS = {
        "Processador": (
            "ryzen 5",
            "ryzen 7",
            "ryzen 9",
            "intel core i5",
            "intel core i7",
            "intel core i9",
            "core ultra",
        ),
        "Memória RAM": (
            "kingston",
            "crucial",
            "corsair",
            "xpg",
            "adata",
            "teamgroup",
            "team group",
            "asgard",
            "gloway",
            "juhor",
        ),
        "Armazenamento": (
            "kingston",
            "crucial",
            "lexar",
            "samsung",
            "western digital",
            "kioxia",
            "sandisk",
            "netac",
            "kingspec",
            "fanxiang",
            "orico",
            "movespeed",
        ),
        "Refrigeração de PC": (
            "thermalright",
            "deepcool",
            "id-cooling",
            "id cooling",
            "jonsbo",
            "cooler master",
            "noctua",
        ),
        "Mouse e mousepad": (
            "attack shark",
            "ajazz",
            "vxe",
            "vgn",
            "delux",
            "darmoshark",
            "mchose",
            "zaopin",
            "logitech",
            "razer",
            "pulsar",
            "paw3395",
            "paw3950",
        ),
        "Teclado": (
            "aula",
            "ajazz",
            "keychron",
            "akko",
            "monsgeek",
            "leobog",
            "epomaker",
            "womier",
            "royal kludge",
            "redragon",
            "hall effect",
            "magnetic keyboard",
            "mechanical keyboard",
        ),
        "Áudio": (
            "soundpeats",
            "qcy",
            "moondrop",
            "truthear",
            "kz ",
            "trn ",
            "edifier",
            "haylou",
            "baseus",
            "soundcore",
            "1more",
            "iem",
        ),
        "Microfone": (
            "fifine",
            "maono",
            "boya",
            "hollyland",
            "ulanzi",
            "rode",
        ),
        "Controle": (
            "8bitdo",
            "gamesir",
            "flydigi",
            "easysmx",
            "gulikit",
            "machenike",
        ),
        "Rede": (
            "tp-link",
            "tplink",
            "xiaomi",
            "ugreen",
            "comfast",
            "wifi 6",
            "wi-fi 6",
            "wifi 7",
            "wi-fi 7",
            "2.5g",
            "10g",
        ),
        "Streaming e captura": (
            "elgato",
            "avermedia",
            "ugreen",
            "hollyland",
            "capture card",
            "video capture",
            "4k capture",
        ),
        "Suportes e conectividade": (
            "ugreen",
            "baseus",
            "orico",
            "anker",
            "hub usb",
            "usb hub",
            "type c hub",
            "usb c hub",
            "dock station",
            "docking station",
            "thunderbolt",
            "nvme enclosure",
            "ssd enclosure",
        ),
        "Carregamento e mobilidade": (
            "baseus",
            "ugreen",
            "anker",
            "essager",
            "toocki",
            "samsung",
            "xiaomi",
            "gan",
            "power bank",
        ),
        "Maker e bancada": (
            "m5stack",
            "esp32",
            "raspberry pi",
            "arduino",
            "soldering",
            "multimeter",
            "screwdriver",
            "component tester",
            "pcb tester",
        ),
        "Celular": (
            "xiaomi",
            "poco",
            "redmi",
            "nubia",
            "oneplus",
            "realme",
            "honor",
        ),
        "Tablet e e-reader": (
            "xiaomi",
            "redmi",
            "lenovo",
            "oneplus",
            "honor",
        ),
        "Wearables": (
            "xiaomi",
            "amazfit",
            "huawei",
            "haylou",
            "redmi",
        ),
    }

    RELEVANCIA_MINIMA_ALIEXPRESS = 60.0
    COLD_START_MINIMO_ALIEXPRESS = 84.0

    PONTUACAO_MINIMA_SECUNDARIO = 72.0
    QUEDA_MINIMA_SECUNDARIO_PERCENTUAL = 15.0
    REGISTROS_MINIMOS_SECUNDARIO = 3

    @classmethod
    def analisar(cls, oferta: Oferta) -> ResultadoPoliticaMarketplace:
        categoria = oferta.categoria or ""
        tier = cls.tier_categoria(categoria)
        marketplace = cls._marketplace(oferta)

        if marketplace != "aliexpress":
            return ResultadoPoliticaMarketplace(True, tier, "Politica geral do Radar.")

        if categoria not in cls.CATEGORIAS_ALIEXPRESS_PERMITIDAS:
            return ResultadoPoliticaMarketplace(
                False,
                tier,
                "Categoria fora da selecao estrita do AliExpress.",
            )

        texto = cls._normalizar(oferta.nome)

        for ruido in cls.RUIDOS_ALIEXPRESS:
            if cls._normalizar(ruido) in texto:
                return ResultadoPoliticaMarketplace(
                    False,
                    tier,
                    f"Ruido incompatível com o Radar: {ruido}.",
                )

        if float(oferta.relevancia_nicho or 0.0) < cls.RELEVANCIA_MINIMA_ALIEXPRESS:
            return ResultadoPoliticaMarketplace(
                False,
                tier,
                "Relevancia insuficiente no AliExpress.",
            )

        marcadores = cls.MARCADORES_QUALIDADE_ALIEXPRESS.get(categoria)
        if marcadores and not any(cls._normalizar(marcador) in texto for marcador in marcadores):
            return ResultadoPoliticaMarketplace(
                False,
                tier,
                "Sem marca, linha ou tecnologia de qualidade identificavel.",
            )

        return ResultadoPoliticaMarketplace(True, tier, "Selecao estrita aprovada.")

    @classmethod
    def tier_categoria(cls, categoria: str | None) -> str:
        if categoria in cls.CATEGORIAS_SECUNDARIAS:
            return cls.TIER_SECUNDARIO
        if categoria in cls.CATEGORIAS_NUCLEO:
            return cls.TIER_NUCLEO
        return cls.TIER_ADJACENTE

    @classmethod
    def eh_secundaria(cls, categoria: str | None) -> bool:
        return categoria in cls.CATEGORIAS_SECUNDARIAS

    @classmethod
    def secundaria_tem_promocao_forte(cls, pontuacao: float, resultado_historico) -> bool:
        if resultado_historico is None:
            return False
        if getattr(resultado_historico, "primeiro_registro", True):
            return False

        try:
            registros = int(getattr(resultado_historico, "quantidade_registros", 0) or 0)
            queda = abs(float(getattr(resultado_historico, "variacao_percentual", 0.0) or 0.0))
        except (TypeError, ValueError):
            return False

        return (
            registros >= cls.REGISTROS_MINIMOS_SECUNDARIO
            and bool(getattr(resultado_historico, "preco_caiu", False))
            and queda >= cls.QUEDA_MINIMA_SECUNDARIO_PERCENTUAL
            and bool(getattr(resultado_historico, "menor_preco_historico", False))
            and float(pontuacao) >= cls.PONTUACAO_MINIMA_SECUNDARIO
        )

    @staticmethod
    def _marketplace(oferta: Oferta) -> str:
        valor = oferta.marketplace or oferta.loja or ""
        chave = str(valor).strip().casefold()
        if "aliexpress" in chave:
            return "aliexpress"
        if "shopee" in chave:
            return "shopee"
        if "mercado" in chave and "livre" in chave:
            return "mercado_livre"
        return chave.replace(" ", "_")

    @staticmethod
    def _normalizar(texto: str) -> str:
        texto = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", str(texto))
            if not unicodedata.combining(caractere)
        )
        texto = texto.casefold()
        texto = re.sub(r"[^a-z0-9.+\- ]", " ", texto)
        return re.sub(r"\s+", " ", texto).strip()
