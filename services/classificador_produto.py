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
    """Classifica primeiro o produto principal e depois os componentes citados.

    A regra central desta versão é simples: um notebook com RTX continua sendo
    um notebook; um PC completo com Ryzen continua sendo um computador; um kit
    de upgrade continua sendo um kit. Só quando não existe uma identidade
    principal explícita usamos a pontuação por termos de componente.
    """

    REGRAS_IDENTIDADE_PRINCIPAL: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "Kit upgrade",
            (
                "kit upgrade",
                "kit processador",
                "kit placa mae",
                "kit cpu",
            ),
        ),
        (
            "Notebook",
            (
                "notebook",
                "ultrabook",
                "laptop",
                "acer nitro",
                "lenovo legion",
                "dell g15",
                "rog strix",
                "alienware",
            ),
        ),
        (
            "Computador e Mini PC",
            (
                "pc gamer",
                "computador gamer",
                "computador completo",
                "pc completo",
                "desktop gamer",
                "mini pc",
            ),
        ),
        (
            "Console",
            (
                "playstation 5",
                "playstation 4",
                "xbox series",
                "xbox one",
                "nintendo switch",
                "steam deck",
                "rog ally",
                "console portatil",
                "console",
            ),
        ),
        (
            "Realidade virtual",
            ("meta quest", "oculos vr", "headset vr", "realidade virtual"),
        ),
        (
            "TV",
            ("smart tv", "televisor", "tv qled", "tv oled", "tv 4k"),
        ),
        (
            "Celular",
            (
                "smartphone",
                "celular",
                "galaxy s",
                "galaxy a",
                "iphone",
                "redmi note",
                "poco ",
                "moto edge",
                "moto g",
            ),
        ),
        (
            "Tablet e e-reader",
            ("tablet", "galaxy tab", "ipad", "kindle", "e-reader", "ereader"),
        ),
        (
            "Monitor",
            (
                "monitor gamer",
                "monitor ips",
                "monitor oled",
                "monitor ultrawide",
                "monitor curvo",
                "monitor led",
            ),
        ),
        (
            "Projetor",
            ("projetor", "mini projetor"),
        ),
        (
            "Impressão",
            (
                "impressora laser",
                "impressora termica",
                "impressora de etiquetas",
                "multifuncional",
                "impressora tanque",
            ),
        ),
    )

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
            "core ultra",
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
            "x870",
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
            "nas",
        ),
        "Fonte e energia": (
            "fonte atx",
            "fonte modular",
            "fonte semi modular",
            "fonte de alimentacao",
            "power supply",
            "80 plus",
            "nobreak",
            "filtro de linha",
            "protetor dps",
        ),
        "Gabinete": (
            "gabinete",
            "mid tower",
            "full tower",
            "mini tower",
            "case gamer",
            "gabinete aquario",
            "gabinete mesh",
        ),
        "Refrigeração de PC": (
            "water cooler",
            "air cooler",
            "aio liquid cooler",
            "cooler para processador",
            "cooler cpu",
            "ventoinha",
            "fan para gabinete",
            "fan argb",
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
        "TV": ("smart tv", "televisor", "tv led", "tv qled", "tv oled", "tv 4k"),
        "Projetor": ("projetor", "mini projetor", "projetor portatil", "projetor 4k"),
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
        "Tablet e e-reader": ("tablet", "galaxy tab", "ipad", "kindle", "e-reader", "ereader"),
        "Notebook": (
            "notebook gamer",
            "laptop gamer",
            "notebook",
            "ultrabook",
            "rog strix",
            "acer nitro",
            "lenovo legion",
            "dell g15",
            "alienware",
        ),
        "Computador e Mini PC": ("pc gamer", "computador gamer", "desktop gamer", "mini pc"),
        "Kit upgrade": ("kit upgrade", "kit processador", "kit placa mae", "kit cpu"),
        "Mouse e mousepad": (
            "mouse",
            "mouse gamer",
            "mouse sem fio",
            "mouse otico",
            "mouse optico",
            "mouse para jogos",
            "mousepad",
            "mouse pad",
            "deskmat",
        ),
        "Teclado": (
            "teclado",
            "teclado gamer",
            "teclado mecanico",
            "teclado magnetico",
            "teclado sem fio",
            "teclado tkl",
            "teclado low profile",
            "hall effect",
            "switch mecanico",
            "keycaps",
        ),
        "Áudio": (
            "headset",
            "fone gamer",
            "fone de ouvido",
            "fone bluetooth",
            "earbuds",
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
            "microfone dinamico",
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
            "8bitdo",
            "gamesir",
        ),
        "Console": (
            "playstation 5",
            "playstation 4",
            "ps5",
            "ps4",
            "xbox series",
            "xbox one",
            "nintendo switch",
            "steam deck",
            "rog ally",
            "console portatil",
            "console",
        ),
        "Realidade virtual": ("meta quest", "oculos vr", "headset vr", "realidade virtual"),
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
            "switch gigabit",
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
            "force feedback",
        ),
        "Mobiliário e ergonomia": (
            "cadeira gamer",
            "cadeira ergonomica",
            "cadeira de escritorio",
            "cadeira presidente",
            "mesa gamer",
            "mesa escritorio",
            "apoio para pes",
        ),
        "Suportes e conectividade": (
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
        "Carregamento e mobilidade": (
            "power bank",
            "carregador gan",
            "carregador usb c",
            "carregador magsafe",
            "carregador sem fio",
        ),
        "Wearables": ("smartwatch", "smartband", "relogio inteligente", "pulseira inteligente"),
        "Casa inteligente": (
            "lampada inteligente",
            "tomada inteligente",
            "echo dot",
            "alexa",
            "camera wifi",
            "camera ip",
            "fechadura inteligente",
            "sensor inteligente",
        ),
        "Climatização e conforto": (
            "ventilador",
            "ventilador de torre",
            "climatizador",
            "ar condicionado",
            "ar-condicionado",
            "frigobar",
            "umidificador",
            "desumidificador",
        ),
        "Automação doméstica": ("aspirador robo", "robo aspirador", "robo passa pano"),
        "Iluminação de setup": (
            "fita led",
            "fita rgb",
            "light bar",
            "barra de luz para monitor",
            "luminaria rgb",
        ),
        "Maker e bancada": (
            "impressora 3d",
            "filamento pla",
            "filamento petg",
            "raspberry pi",
            "arduino",
            "esp32",
            "estacao de solda",
            "ferro de solda",
            "kit chave de precisao",
            "chave de precisao",
            "multimetro digital",
            "fonte de bancada",
        ),
        "Câmeras e drones": (
            "camera de acao",
            "action cam",
            "gopro",
            "drone com camera",
            "drone dji",
            "camera mirrorless",
        ),
        "Impressão": (
            "impressora laser",
            "impressora termica",
            "impressora de etiquetas",
            "impressora tanque",
            "multifuncional",
        ),
        "Suplementos": (
            "creatina monohidratada",
            "creatina",
            "creatine",
            "whey protein",
            "whey",
            "protein powder",
            "pre treino",
            "pre-treino",
            "pre workout",
            "beta alanina",
            "glutamina",
            "bcaa",
            "hipercalorico",
            "barra proteica",
            "protein bar",
        ),
        "Energ\u00e9ticos": (
            "energetico",
            "energy drink",
            "monster energy",
            "red bull",
            "tnt energy",
            "baly energy",
            "fusion energy",
        ),
        "Caf\u00e9": (
            "cafe em graos",
            "cafe moido",
            "cafe soluvel",
            "cafe especial",
            "capsula de cafe",
            "capsulas de cafe",
            "capsula nespresso",
            "capsula dolce gusto",
            "cafe 3 coracoes",
            "cafe melitta",
            "cafe",
        ),
        "Chocolate e snacks": (
            "lacta",
            "garoto",
            "kitkat",
            "bis",
            "talento",
            "ouro branco",
            "sonho de valsa",
            "hersheys",
            "hershey",
            "nestle",
            "barra de chocolate",
            "chocolate lacta",
            "chocolate nestle",
            "chocolate hershey",
            "kitkat",
            "oreo",
            "chocolate",
        ),
    }

    TERMOS_GAMER: tuple[str, ...] = ("gamer", "gaming", "rgb", "argb", "esports", "e-sports")

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
        "rx 580",
        "rx 6600",
        "rx 6650",
        "rx 6700",
        "rx 6750",
        "rx 7600",
        "rx 7700",
        "rx 7800",
        "rx 7900",
        "rx 9060",
        "rx 9070",
        "ryzen 3",
        "ryzen 5",
        "ryzen 7",
        "ryzen 9",
        "core i5",
        "core i7",
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
        "almofada headset",
        "headband",
        "earpad",
        "case para controle",
        "skin adesiva",
        "suporte veicular",
        "controle remoto reposicao",
        "capa para controle",
        "adesivo para controle",
        "pelicula para smartwatch",
        "pulseira para smartwatch",
        "capa para tablet",
        "capa para kindle",
        "tinta para impressora",
        "cartucho de tinta",
        "toner compativel",
        "cabo reposicao headset",
        "cabo para headset",
        "microfone reposicao headset",
    )

    MARCADORES_COMPONENTE_KIT: tuple[str, ...] = (
        "ryzen",
        "core i3",
        "core i5",
        "core i7",
        "core i9",
        "placa mae",
        "a520",
        "b450",
        "b550",
        "a620",
        "b650",
        "h610",
        "b760",
        "ddr4",
        "ddr5",
        "memoria",
        "ram",
        "cooler",
    )

    TERMOS_ACESSORIO_CONSOLE: tuple[str, ...] = (
        "headset",
        "fone",
        "ssd",
        "nvme",
        "controle",
        "gamepad",
        "joystick",
        "suporte",
        "base",
        "dock",
        "cabo",
        "carregador",
        "adaptador",
        "capa",
        "skin",
        "volante",
        "pedal",
        "mouse",
        "teclado",
        "microfone",
        "placa de captura",
    )

    def classificar(self, oferta: Oferta) -> ResultadoClassificacaoProduto:
        nome_normalizado = self._normalizar_texto(oferta.nome)

        termos_bloqueados = self._localizar_termos(nome_normalizado, self.TERMOS_BLOQUEADOS)
        if termos_bloqueados:
            return ResultadoClassificacaoProduto(
                eh_nicho=False,
                categoria=None,
                relevancia=0,
                termos_encontrados=termos_bloqueados,
                motivo="Produto pertence a uma categoria bloqueada para o canal.",
            )

        categoria_principal, termos_principais = self._identificar_identidade_principal(
            nome_normalizado
        )

        if categoria_principal is not None:
            categoria = categoria_principal
            termos_categoria = termos_principais
            identidade_explicita = True
        else:
            categoria, termos_categoria = self._identificar_categoria(nome_normalizado)
            identidade_explicita = False

        if categoria is None:
            return ResultadoClassificacaoProduto(
                eh_nicho=False,
                categoria=None,
                relevancia=0,
                termos_encontrados=[],
                motivo="Nenhuma categoria de hardware, eletrônico ou produto gamer foi identificada.",
            )

        termos_gamer = self._localizar_termos(nome_normalizado, self.TERMOS_GAMER)
        termos_modelo = self._localizar_termos(nome_normalizado, self.TERMOS_MODELO_HARDWARE)

        relevancia = 55.0
        relevancia += min(len(termos_categoria) * 8, 24)
        if identidade_explicita:
            relevancia += 12
        if termos_gamer:
            relevancia += 10
        if termos_modelo:
            relevancia += 11
        relevancia = min(relevancia, 100)

        termos_encontrados = list(dict.fromkeys(termos_categoria + termos_gamer + termos_modelo))

        origem = "identidade principal" if identidade_explicita else "termos do título"

        return ResultadoClassificacaoProduto(
            eh_nicho=True,
            categoria=categoria,
            relevancia=round(relevancia, 2),
            termos_encontrados=termos_encontrados,
            motivo=(
                f"Produto classificado como '{categoria}' por {origem}, "
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

    def _identificar_identidade_principal(self, texto: str) -> tuple[str | None, list[str]]:
        # 1) Kits de upgrade, mesmo sem a expressão "kit upgrade".
        if self._eh_kit_upgrade(texto):
            termos = ["kit"]
            termos.extend(self._localizar_termos(texto, self.MARCADORES_COMPONENTE_KIT)[:4])
            return "Kit upgrade", list(dict.fromkeys(termos))

        # 2) Produto explícito logo no começo do título.
        inicio = self._categoria_explicita_no_inicio(texto)
        if inicio is not None:
            return inicio

        # 3) PCs/computadores completos.
        if self._eh_computador_principal(texto):
            termos = self._localizar_termos(
                texto,
                (
                    "pc gamer",
                    "computador gamer",
                    "computador completo",
                    "pc completo",
                    "computador",
                    "desktop",
                    "pc",
                ),
            )
            return "Computador e Mini PC", termos or ["computador"]

        # 4) Notebook apenas quando notebook é o produto vendido.
        if self._eh_notebook_principal(texto):
            termos = self._localizar_termos(
                texto,
                (
                    "notebook",
                    "ultrabook",
                    "laptop",
                    "acer nitro",
                    "lenovo legion",
                    "dell g15",
                    "rog strix",
                    "alienware",
                ),
            )
            return "Notebook", termos or ["notebook"]

        # 5) Suportes/bases/docks para consoles continuam sendo acessórios.
        if self._eh_suporte_console(texto):
            return "Suportes e conectividade", ["suporte", "console"]

        # 6) Regras explícitas restantes, sem tratar console aqui.
        for categoria, termos in self.REGRAS_IDENTIDADE_PRINCIPAL:
            if categoria in {
                "Kit upgrade",
                "Notebook",
                "Computador e Mini PC",
                "Console",
            }:
                continue

            encontrados = self._localizar_termos(texto, termos)
            if encontrados:
                return categoria, encontrados

        # 7) Console só quando ele próprio é o item anunciado.
        if self._eh_console_principal(texto):
            termos = self._localizar_termos(
                texto,
                (
                    "playstation 5",
                    "playstation 4",
                    "ps5",
                    "ps4",
                    "xbox series",
                    "xbox one",
                    "nintendo switch",
                    "steam deck",
                    "rog ally",
                    "console",
                ),
            )
            return "Console", termos

        return None, []

    def _categoria_explicita_no_inicio(self, texto: str) -> tuple[str, list[str]] | None:
        regras: tuple[tuple[str, str], ...] = (
            (
                "Suplementos",
                r"^(?:creatina|creatine|whey|pre treino|pre-treino|"
                r"beta alanina|glutamina|bcaa|hipercalorico|barra proteica)\b",
            ),
            (
                "Energ\u00e9ticos",
                r"^(?:energetico|energy drink|monster energy|red bull|"
                r"tnt energy|baly energy|fusion energy)\b",
            ),
            (
                "Caf\u00e9",
                r"^(?:cafe|capsula de cafe|capsulas de cafe|"
                r"capsula nespresso|capsula dolce gusto)\b",
            ),
            (
                "Chocolate e snacks",
                r"^(?:chocolate|barra de chocolate|kitkat|oreo)\b",
            ),
            ("Armazenamento", r"^(?:ssd|nvme|hd|disco solido)\b"),
            ("Processador", r"^(?:processador|cpu)\b"),
            ("Memória RAM", r"^(?:memoria ram|memoria ddr|ram)\b"),
            ("Placa de vídeo", r"^(?:placa de video|placa grafica|gpu)\b"),
            ("Placa-mãe", r"^(?:placa mae|motherboard)\b"),
            ("Áudio", r"^(?:headset|fone de ouvido|fone gamer|earbuds)\b"),
            ("Controle", r"^(?:controle|gamepad|joystick|dualsense|dualshock)\b"),
            ("Suportes e conectividade", r"^(?:suporte|base|dock)\b"),
        )

        for categoria, padrao in regras:
            match = re.search(padrao, texto)
            if match:
                return categoria, [match.group(0)]

        return None

    def _eh_kit_upgrade(self, texto: str) -> bool:
        if not self._contem_termo(texto, "kit"):
            return False

        if any(
            self._contem_termo(texto, termo)
            for termo in ("kit teclado", "kit mouse", "kit gamer teclado")
        ):
            return False

        marcadores = set(self._localizar_termos(texto, self.MARCADORES_COMPONENTE_KIT))

        chipsets = set(
            re.findall(
                r"\b(?:a520m?|b450m?|b550m?|a620m?|b650m?|h610m?|b760m?)\b",
                texto,
            )
        )

        return len(marcadores) + len(chipsets) >= 2

    def _eh_computador_principal(self, texto: str) -> bool:
        if self._localizar_termos(
            texto,
            (
                "pc gamer",
                "computador gamer",
                "computador completo",
                "pc completo",
                "desktop gamer",
                "mini pc",
            ),
        ):
            return True

        if re.search(r"^(?:[^ ]+\s+){0,3}(?:computador|desktop|pc)\b", texto):
            return True

        if re.search(r"\b(?:para|p/?)\s*(?:pc|computador|desktop)\b", texto):
            return False

        return False

    def _eh_notebook_principal(self, texto: str) -> bool:
        if self._localizar_termos(
            texto,
            ("acer nitro", "lenovo legion", "dell g15", "rog strix", "alienware"),
        ):
            return True

        if re.search(r"^(?:[^ ]+\s+){0,3}(?:notebook|ultrabook|laptop)\b", texto):
            return True

        if re.search(r"\b(?:para|p/?)\s*(?:notebook|laptop|ultrabook)\b", texto):
            return False

        if re.search(
            r"^(?:ssd|nvme|processador|cpu|memoria|ram|carregador|suporte)\b.*" r"\bnotebook\b",
            texto,
        ):
            return False

        return self._contem_termo(texto, "notebook")

    def _eh_suporte_console(self, texto: str) -> bool:
        if not re.search(r"^(?:suporte|base|dock)\b", texto):
            return False

        return re.search(r"\b(?:ps4|ps5|playstation|xbox)\b", texto) is not None

    def _eh_console_principal(self, texto: str) -> bool:
        dispositivos = (
            "playstation 5",
            "playstation 4",
            "ps5",
            "ps4",
            "xbox series",
            "xbox one",
            "nintendo switch",
            "steam deck",
            "rog ally",
        )

        if not self._localizar_termos(texto, dispositivos):
            return False

        if self._localizar_termos(texto, self.TERMOS_ACESSORIO_CONSOLE):
            return False

        if re.search(
            r"\b(?:para|compativel com|funciona (?:no|em))\s+"
            r"(?:o\s+)?(?:ps4|ps5|playstation|xbox)\b",
            texto,
        ):
            return False

        return True

    def _identificar_categoria(self, texto: str) -> tuple[str | None, list[str]]:
        melhor_categoria: str | None = None
        melhores_termos: list[str] = []
        for categoria, termos in self.CATEGORIAS.items():
            encontrados = self._localizar_termos(texto, termos)
            if len(encontrados) > len(melhores_termos):
                melhor_categoria = categoria
                melhores_termos = encontrados
        return melhor_categoria, melhores_termos

    def _localizar_termos(self, texto: str, termos: tuple[str, ...]) -> list[str]:
        encontrados: list[str] = []
        for termo in termos:
            termo_normalizado = self._normalizar_texto(termo)
            if self._contem_termo(texto, termo_normalizado):
                encontrados.append(termo)
        return encontrados

    @staticmethod
    def _contem_termo(texto: str, termo: str) -> bool:
        padrao = r"(?<![a-z0-9])" + re.escape(termo) + r"(?![a-z0-9])"
        return re.search(padrao, texto) is not None

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        texto_sem_acentos = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caractere)
        )
        texto_normalizado = texto_sem_acentos.lower()
        texto_normalizado = re.sub(r"[^a-z0-9.+/\- ]", " ", texto_normalizado)
        texto_normalizado = re.sub(r"\s+", " ", texto_normalizado)
        return texto_normalizado.strip()
