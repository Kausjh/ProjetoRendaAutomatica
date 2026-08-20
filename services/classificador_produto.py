# 63.8738, -149.7525

import re
import unicodedata
from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True)
class ResultadoClassificacaoProduto:
    eh_nicho: bool
    categoria: str | None
    relevancia: float
    termos_encontrados: list[str]
    motivo: str


class ClassificadorProduto:
    """
    Classifica ofertas relacionadas a hardware, periféricos,
    computadores, consoles, eletrônicos de setup e produtos gamer.

    A classificação é baseada no nome da oferta.

    O termo "gamer" isoladamente não é suficiente para aprovar
    uma oferta. O produto também precisa pertencer a uma categoria
    relevante.
    """

    CATEGORIAS: dict[str, tuple[str, ...]] = {
        "Placa de vídeo": (
            "placa de video",
            "gpu",
            "geforce",
            "radeon",
            "rtx",
            "gtx",
            "arc a",
        ),
        "Processador": (
            "processador",
            "cpu",
            "ryzen",
            "core i3",
            "core i5",
            "core i7",
            "core i9",
            "threadripper",
        ),
        "Placa-mãe": (
            "placa mae",
            "motherboard",
            "a520",
            "b450",
            "b550",
            "x570",
            "a620",
            "b650",
            "x670",
            "h610",
            "b660",
            "b760",
            "z690",
            "z790",
        ),
        "Memória RAM": (
            "memoria ram",
            "memoria ddr",
            "ddr4",
            "ddr5",
            "sodimm",
            "dimm",
        ),
        "Armazenamento": (
            "ssd",
            "nvme",
            "m.2",
            "hd interno",
            "hd externo",
            "disco rigido",
            "hard disk",
            "cartao de memoria",
            "pen drive",
        ),
        "Fonte": (
            "fonte atx",
            "fonte modular",
            "fonte semi modular",
            "fonte de alimentacao",
            "power supply",
            "80 plus",
            "nobreak",
            "estabilizador",
        ),
        "Gabinete": (
            "gabinete",
            "mid tower",
            "full tower",
            "mini tower",
            "case gamer",
        ),
        "Refrigeração": (
            "water cooler",
            "air cooler",
            "cooler para processador",
            "cooler cpu",
            "ventoinha",
            "fan para gabinete",
            "pasta termica",
        ),
        "Monitor": (
            "monitor gamer",
            "monitor led",
            "monitor ips",
            "monitor oled",
            "monitor ultrawide",
            "monitor curvo",
            "monitor",
        ),
        "TV": (
            "smart tv",
            "televisor",
            "tv led",
            "tv qled",
            "tv oled",
            "tv 4k",
        ),
        "Celular": (
            "smartphone",
            "celular",
            "galaxy",
            "iphone",
            "redmi",
            "poco",
            "moto g",
            "moto edge",
        ),
        "Notebook gamer": (
            "notebook gamer",
            "laptop gamer",
            "rog strix",
            "acer nitro",
            "lenovo legion",
            "dell g15",
            "alienware",
        ),
        "Computador gamer": (
            "pc gamer",
            "computador gamer",
            "desktop gamer",
        ),
        "Mouse": (
            "mouse",
            "mouse gamer",
            "mouse sem fio",
            "mouse otico",
            "mouse optico",
            "mouse para jogos",
            "mousepad",
            "mouse pad",
        ),
        "Teclado": (
            "teclado",
            "teclado gamer",
            "teclado mecanico",
            "teclado magnetico",
            "teclado sem fio",
            "switch mecanico",
            "keycaps",
        ),
        "Headset e áudio": (
            "headset",
            "fone gamer",
            "fone de ouvido",
            "fone bluetooth",
            "caixa de som",
            "soundbar",
            "sound bar",
            "interface de audio",
        ),
        "Microfone": (
            "microfone",
            "microfone gamer",
            "microfone usb",
            "microfone condensador",
            "microfone de lapela",
        ),
        "Controle": (
            "controle xbox",
            "controle playstation",
            "controle para pc",
            "controle sem fio",
            "gamepad",
            "joystick",
            "dualsense",
            "dualshock",
        ),
        "Console": (
            "playstation 5",
            "playstation 4",
            "xbox series",
            "xbox one",
            "nintendo switch",
            "steam deck",
            "console",
        ),
        "Rede": (
            "roteador gamer",
            "roteador wi-fi",
            "roteador wifi",
            "roteador",
            "placa de rede",
            "adaptador wi-fi",
            "adaptador wifi",
            "cabo de rede",
            "repetidor de sinal",
            "mesh",
        ),
        "Streaming e captura": (
            "placa de captura",
            "capture card",
            "stream deck",
            "webcam",
            "ring light",
            "iluminador led",
        ),
        "Simulação": (
            "volante gamer",
            "pedal gamer",
            "cambio gamer",
            "cockpit gamer",
            "simulador de corrida",
        ),
        "Mobiliário gamer": (
            "cadeira gamer",
            "mesa gamer",
            "cadeira de escritorio",
        ),
        "Suportes e acessórios": (
            "suporte para monitor",
            "suporte de monitor",
            "suporte articulado",
            "suporte para microfone",
            "braco articulado",
            "suporte para notebook",
            "suporte para headset",
            "suporte de parede tv",
            "hub usb",
            "dock station",
            "adaptador usb c",
            "organizador de cabos",
        ),
    }

    TERMOS_GAMER: tuple[str, ...] = (
        "gamer",
        "gaming",
        "rgb",
        "argb",
        "esports",
        "e-sports",
    )

    TERMOS_MODELO_HARDWARE: tuple[str, ...] = (
        "rtx 3050",
        "rtx 3060",
        "rtx 3070",
        "rtx 3080",
        "rtx 3090",
        "rtx 4060",
        "rtx 4070",
        "rtx 4080",
        "rtx 4090",
        "rtx 5060",
        "rtx 5070",
        "rtx 5080",
        "rtx 5090",
        "rx 6600",
        "rx 6650",
        "rx 6700",
        "rx 6750",
        "rx 7600",
        "rx 7700",
        "rx 7800",
        "rx 7900",
        "ryzen 3",
        "ryzen 5",
        "ryzen 7",
        "ryzen 9",
        "ddr4",
        "ddr5",
        "nvme",
        "pcie 4.0",
        "pcie 5.0",
        "144hz",
        "165hz",
        "180hz",
        "200hz",
        "240hz",
        "360hz",
    )

    TERMOS_BLOQUEADOS: tuple[str, ...] = (
        "camiseta",
        "camisa",
        "caneca",
        "chaveiro",
        "adesivo",
        "boneco",
        "pelucia",
        "livro",
        "poster",
        "quadro decorativo",
        "fantasia",
        "mochila escolar",
        "capa para celular",
        "capinha",
        "pelicula",
        "espuma almofada",
        "almofada para fone",
        "earpad",
        "case para controle",
        "skin adesiva",
        "suporte veicular",
    )

    def classificar(self, oferta: Oferta) -> ResultadoClassificacaoProduto:
        nome_normalizado = self._normalizar_texto(oferta.nome)

        termos_bloqueados = self._localizar_termos(
            texto=nome_normalizado, termos=self.TERMOS_BLOQUEADOS
        )

        if termos_bloqueados:
            return ResultadoClassificacaoProduto(
                eh_nicho=False,
                categoria=None,
                relevancia=0,
                termos_encontrados=termos_bloqueados,
                motivo=("Produto pertence a uma categoria bloqueada " "para o canal."),
            )

        categoria, termos_categoria = self._identificar_categoria(nome_normalizado)

        if categoria is None:
            return ResultadoClassificacaoProduto(
                eh_nicho=False,
                categoria=None,
                relevancia=0,
                termos_encontrados=[],
                motivo=(
                    "Nenhuma categoria de hardware, eletrônico "
                    "ou produto gamer foi identificada."
                ),
            )

        termos_gamer = self._localizar_termos(texto=nome_normalizado, termos=self.TERMOS_GAMER)

        termos_modelo = self._localizar_termos(
            texto=nome_normalizado, termos=self.TERMOS_MODELO_HARDWARE
        )

        relevancia = 55.0

        relevancia += min(len(termos_categoria) * 8, 24)

        if termos_gamer:
            relevancia += 10

        if termos_modelo:
            relevancia += 11

        relevancia = min(relevancia, 100)

        termos_encontrados = list(dict.fromkeys(termos_categoria + termos_gamer + termos_modelo))

        return ResultadoClassificacaoProduto(
            eh_nicho=True,
            categoria=categoria,
            relevancia=round(relevancia, 2),
            termos_encontrados=termos_encontrados,
            motivo=(
                f"Produto classificado como '{categoria}' "
                f"com relevância de {relevancia:.2f}/100."
            ),
        )

    def aplicar_classificacao(self, oferta: Oferta) -> ResultadoClassificacaoProduto:
        resultado = self.classificar(oferta)

        oferta.eh_nicho = resultado.eh_nicho
        oferta.categoria = resultado.categoria
        oferta.relevancia_nicho = resultado.relevancia
        oferta.termos_nicho = resultado.termos_encontrados
        oferta.motivo_classificacao = resultado.motivo

        return resultado

    def _identificar_categoria(self, texto: str) -> tuple[str | None, list[str]]:
        melhor_categoria: str | None = None
        melhores_termos: list[str] = []

        for categoria, termos in self.CATEGORIAS.items():
            termos_encontrados = self._localizar_termos(texto=texto, termos=termos)

            if len(termos_encontrados) > len(melhores_termos):
                melhor_categoria = categoria
                melhores_termos = termos_encontrados

        return melhor_categoria, melhores_termos

    def _localizar_termos(self, texto: str, termos: tuple[str, ...]) -> list[str]:
        encontrados: list[str] = []

        for termo in termos:
            termo_normalizado = self._normalizar_texto(termo)

            if self._contem_termo(texto=texto, termo=termo_normalizado):
                encontrados.append(termo)

        return encontrados

    def _contem_termo(self, texto: str, termo: str) -> bool:
        padrao = r"(?<![a-z0-9])" + re.escape(termo) + r"(?![a-z0-9])"

        return re.search(padrao, texto) is not None

    def _normalizar_texto(self, texto: str) -> str:
        texto_sem_acentos = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caractere)
        )

        texto_normalizado = texto_sem_acentos.lower()

        texto_normalizado = re.sub(r"[^a-z0-9.+\- ]", " ", texto_normalizado)

        texto_normalizado = re.sub(r"\s+", " ", texto_normalizado)

        return texto_normalizado.strip()
