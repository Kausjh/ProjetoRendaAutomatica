# 63.8738, -149.7525

import logging
import time
from datetime import datetime

from models.oferta import Oferta
from scrapers.base_scraper import BaseScraper
from services.scout.mercado_livre_catalog_api import (
    ClienteCatalogoMercadoLivre,
    ErroApiMercadoLivre,
    SnapshotCatalogoMercadoLivre,
)

logger = logging.getLogger(__name__)


class MercadoLivreScraper(BaseScraper):
    """
    Coleta produtos do Mercado Livre usando a API oficial de catálogo.

    Preserva a cobertura e a rotação de termos do Hunter sem depender
    de navegador para a descoberta tradicional do marketplace.
    """

    # Cobertura de busca
    #
    # Em vez de prender uma categoria a uma única marca (ex.: "Teclado
    # Redragon"), cada categoria possui uma cesta ampla de consultas:
    # termos genéricos, formatos/especificações e algumas marcas relevantes.
    #
    # Toda categoria é visitada em cada ciclo. Os termos dentro dela giram
    # a cada janela de 30 minutos. Categorias centrais recebem dois termos
    # por ciclo; as demais recebem um. Assim ampliamos o catálogo inteiro
    # sem executar centenas de buscas de uma vez.
    TERMOS_POR_CATEGORIA: dict[str, tuple[str, ...]] = {
        "Processadores AMD": (
            "Processador Ryzen",
            "Ryzen 5",
            "Ryzen 7",
            "Ryzen 9",
            "Ryzen AM4",
            "Ryzen AM5",
            "Ryzen X3D",
            "Ryzen com vídeo integrado",
        ),
        "Processadores Intel": (
            "Processador Intel Core",
            "Intel Core i3",
            "Intel Core i5",
            "Intel Core i7",
            "Intel Core i9",
            "Intel LGA 1700",
            "Intel Core Ultra desktop",
        ),
        "Placas de vídeo NVIDIA": (
            "Placa de vídeo NVIDIA",
            "RTX placa de vídeo",
            "GeForce RTX",
            "RTX 4060",
            "RTX 5060",
            "RTX 5070",
            "RTX 5070 Ti",
            "RTX 5080",
        ),
        "Placas de vídeo AMD": (
            "Placa de vídeo Radeon",
            "RX placa de vídeo",
            "Radeon RX",
            "RX 6600",
            "RX 7600",
            "RX 7800 XT",
            "RX 9060 XT",
            "RX 9070 XT",
        ),
        "Placas-mãe AMD": (
            "Placa mãe AMD",
            "Placa mãe AM4",
            "Placa mãe AM5",
            "Placa mãe B550",
            "Placa mãe B650",
            "Placa mãe X670",
            "Placa mãe X870",
        ),
        "Placas-mãe Intel": (
            "Placa mãe Intel",
            "Placa mãe LGA1700",
            "Placa mãe H610",
            "Placa mãe B760",
            "Placa mãe Z790",
            "Placa mãe Intel Core Ultra",
        ),
        "Memória RAM": (
            "Memória RAM",
            "Memória RAM DDR4",
            "Memória RAM DDR5",
            "Memória 16GB DDR4",
            "Memória 32GB DDR4",
            "Memória 32GB DDR5",
            "Memória SODIMM notebook",
            "Memória Corsair Kingston XPG",
        ),
        "Armazenamento": (
            "SSD",
            "SSD NVMe",
            "SSD SATA",
            "SSD NVMe 1TB",
            "SSD NVMe 2TB",
            "SSD PCIe 4.0",
            "SSD PCIe 5.0",
            "HD externo",
            "NAS armazenamento",
            "Pen drive USB 3.2",
        ),
        "Fontes e energia": (
            "Fonte ATX",
            "Fonte 80 Plus",
            "Fonte modular",
            "Fonte 650W",
            "Fonte 750W",
            "Fonte 850W",
            "Fonte Corsair",
            "Fonte MSI",
            "Fonte XPG",
            "Nobreak",
            "Filtro de linha DPS",
        ),
        "Gabinetes": (
            "Gabinete PC",
            "Gabinete gamer",
            "Gabinete aquário",
            "Gabinete mesh",
            "Gabinete mini tower",
            "Gabinete mid tower",
            "Gabinete branco gamer",
        ),
        "Refrigeração": (
            "Cooler processador",
            "Air cooler processador",
            "Water cooler",
            "Water cooler 240mm",
            "Water cooler 360mm",
            "AIO liquid cooler",
            "Fan ARGB gabinete",
            "Kit fans gabinete",
            "Pasta térmica",
        ),
        "Monitores": (
            "Monitor",
            "Monitor gamer",
            "Monitor IPS",
            "Monitor 144Hz",
            "Monitor 165Hz",
            "Monitor 180Hz",
            "Monitor 240Hz",
            "Monitor ultrawide",
            "Monitor OLED",
            "Monitor LG Samsung AOC Asus",
        ),
        "Teclados": (
            "Teclado",
            "Teclado mecânico",
            "Teclado gamer",
            "Teclado TKL",
            "Teclado 60%",
            "Teclado 75%",
            "Teclado sem fio",
            "Teclado low profile",
            "Teclado magnético hall effect",
            "Teclado Redragon",
            "Teclado Logitech",
            "Teclado HyperX",
            "Teclado Keychron",
            "Teclado Razer",
        ),
        "Mouses": (
            "Mouse",
            "Mouse gamer",
            "Mouse sem fio",
            "Mouse leve gamer",
            "Mouse competitivo FPS",
            "Mouse Logitech",
            "Mouse Razer",
            "Mouse HyperX",
            "Mouse Redragon",
            "Mouse Attack Shark",
        ),
        "Mousepads": (
            "Mousepad",
            "Mousepad gamer",
            "Mousepad speed",
            "Mousepad control",
            "Mousepad deskmat",
            "Mousepad grande",
        ),
        "Headsets e fones": (
            "Headset",
            "Headset gamer",
            "Headset sem fio",
            "Fone gamer",
            "Fone bluetooth",
            "Earbuds bluetooth",
            "Headset HyperX",
            "Headset Logitech",
            "Headset Razer",
            "Headset JBL",
        ),
        "Microfones e áudio creator": (
            "Microfone",
            "Microfone USB",
            "Microfone condensador",
            "Microfone dinâmico USB",
            "Interface de áudio USB",
            "Braço articulado microfone",
            "Microfone Fifine",
            "Microfone HyperX",
        ),
        "Webcams e captura": (
            "Webcam",
            "Webcam full hd",
            "Webcam 4k",
            "Placa de captura",
            "Capture card",
            "Stream deck",
            "Webcam Logitech",
        ),
        "Controles": (
            "Controle gamer",
            "Controle PC",
            "Controle Xbox",
            "Controle PlayStation",
            "DualSense",
            "Controle 8BitDo",
            "Controle Gamesir",
            "Controle sem fio hall effect",
        ),
        "Consoles": (
            "Console",
            "PlayStation 5",
            "Xbox Series S",
            "Xbox Series X",
            "Nintendo Switch",
            "Steam Deck",
            "ROG Ally",
            "Console portátil",
        ),
        "Simulação": (
            "Volante gamer",
            "Volante force feedback",
            "Pedal simulador",
            "Câmbio simulador",
            "Cockpit simulador",
            "Logitech G29",
            "Thrustmaster volante",
        ),
        "Realidade virtual": (
            "Óculos VR",
            "Headset VR",
            "Meta Quest",
            "Meta Quest 3",
            "Realidade virtual PC",
        ),
        "Notebooks": (
            "Notebook",
            "Notebook gamer",
            "Notebook Ryzen 5",
            "Notebook Ryzen 7",
            "Notebook Core i5",
            "Notebook Core i7",
            "Notebook RTX 4050",
            "Notebook RTX 4060",
            "Notebook Lenovo",
            "Notebook Acer",
            "Notebook Asus",
            "Notebook Dell",
        ),
        "Computadores e mini PCs": (
            "PC gamer",
            "Computador gamer",
            "PC Ryzen",
            "PC RTX",
            "Computador completo",
            "Mini PC",
            "Mini PC Ryzen",
            "Mini PC Intel N100",
        ),
        "Celulares": (
            "Smartphone",
            "Celular Samsung Galaxy",
            "Celular Xiaomi",
            "Celular Motorola",
            "iPhone",
            "Galaxy S",
            "Galaxy A",
            "Redmi Note",
            "Poco",
            "Moto Edge",
        ),
        "Tablets e e-readers": (
            "Tablet",
            "Tablet Samsung Galaxy Tab",
            "iPad",
            "Tablet Lenovo",
            "Tablet Xiaomi",
            "Kindle",
            "E-reader",
        ),
        "Wearables": (
            "Smartwatch",
            "Smartband",
            "Galaxy Watch",
            "Apple Watch",
            "Amazfit",
            "Mi Band",
        ),
        "TVs": (
            "Smart TV",
            "Smart TV 43",
            "Smart TV 50",
            "Smart TV 55",
            "Smart TV 65",
            "TV QLED",
            "TV OLED",
            "TV 4K",
        ),
        "Projetores": (
            "Projetor",
            "Projetor portátil",
            "Mini projetor",
            "Projetor full hd",
            "Projetor 4k",
        ),
        "Rede": (
            "Roteador",
            "Roteador wifi 6",
            "Roteador wifi 6E",
            "Roteador mesh",
            "Kit mesh wifi",
            "Repetidor wifi",
            "Adaptador wifi USB",
            "Placa de rede wifi",
            "Switch gigabit",
        ),
        "Conectividade": (
            "Hub USB",
            "Hub USB C",
            "Dock station USB C",
            "Adaptador USB C",
            "Adaptador HDMI USB C",
            "Cabo USB C 100W",
            "Leitor cartão USB C",
        ),
        "Carregamento": (
            "Power bank",
            "Power bank 20000mah",
            "Carregador GaN",
            "Carregador USB C",
            "Carregador USB C 65W",
            "Carregador sem fio",
            "Carregador MagSafe",
        ),
        "Mobiliário e ergonomia": (
            "Cadeira ergonômica",
            "Cadeira escritório",
            "Cadeira gamer",
            "Mesa gamer",
            "Mesa escritório",
            "Braço suporte monitor",
            "Suporte para monitor",
            "Suporte para notebook",
            "Apoio para pés ergonômico",
        ),
        "Iluminação de setup": (
            "Fita LED RGB",
            "Light bar monitor",
            "Luminária monitor",
            "Ring light",
            "Luminária RGB setup",
            "Painel LED RGB",
        ),
        "Casa inteligente": (
            "Lâmpada inteligente",
            "Tomada inteligente",
            "Echo Dot",
            "Alexa",
            "Câmera wifi",
            "Câmera IP",
            "Fechadura inteligente",
            "Sensor inteligente wifi",
        ),
        "Conforto e climatização": (
            "Ventilador",
            "Ventilador de torre",
            "Climatizador",
            "Ar condicionado inverter",
            "Ar condicionado portátil",
            "Umidificador",
            "Desumidificador",
            "Frigobar",
        ),
        "Automação doméstica": (
            "Aspirador robô",
            "Robô aspirador",
            "Robô passa pano",
            "Aspirador robô Xiaomi",
            "Aspirador robô Wap",
        ),
        "Maker e bancada": (
            "Impressora 3D",
            "Filamento PLA",
            "Filamento PETG",
            "Raspberry Pi",
            "Arduino kit",
            "ESP32 kit",
            "Estação de solda",
            "Ferro de solda",
            "Kit chave de precisão",
            "Multímetro digital",
            "Fonte de bancada",
        ),
        "Câmeras e drones": (
            "Câmera de ação",
            "Action cam",
            "GoPro",
            "Drone com câmera",
            "Drone DJI",
            "Câmera mirrorless",
            "Câmera Sony mirrorless",
        ),
        "Impressão": (
            "Impressora",
            "Impressora laser",
            "Impressora tanque de tinta",
            "Impressora térmica",
            "Impressora de etiquetas",
            "Multifuncional wifi",
        ),
        "Suplementos": (
            "Creatina monohidratada",
            "Creatina 300g",
            "Creatina 500g",
            "Whey protein",
            "Whey protein 900g",
            "Whey concentrado",
            "Pre treino",
            "Beta alanina",
            "Glutamina",
            "Barra proteica",
        ),
        "Energ\u00e9ticos": (
            "Energetico",
            "Energetico lata",
            "Monster Energy",
            "Monster Energy 473ml",
            "Red Bull",
            "Red Bull 250ml",
            "TNT Energy",
            "Baly Energy",
        ),
        "Caf\u00e9": (
            "Cafe em graos",
            "Cafe em graos 1kg",
            "Cafe moido",
            "Cafe moido 500g",
            "Cafe especial",
            "Capsula Nespresso",
            "Capsula Dolce Gusto",
            "Cafe 3 Coracoes",
            "Cafe Melitta",
        ),
        "Chocolate e snacks": (
            "Chocolate",
            "Barra de chocolate",
            "Chocolate Lacta",
            "Chocolate Nestle",
            "Chocolate Hershey's",
            "KitKat",
            "Oreo",
        ),
    }

    CATEGORIAS_PRIORITARIAS: frozenset[str] = frozenset(
        {
            "Processadores AMD",
            "Processadores Intel",
            "Placas de vídeo NVIDIA",
            "Placas de vídeo AMD",
            "Placas-mãe AMD",
            "Placas-mãe Intel",
            "Memória RAM",
            "Armazenamento",
            "Fontes e energia",
            "Monitores",
            "Teclados",
            "Mouses",
            "Headsets e fones",
            "Notebooks",
            "Controles",
            "Consoles",
            "Celulares",
        }
    )

    CATEGORIAS_SECUNDARIAS: frozenset[str] = frozenset(
        {
            "Suplementos",
            "Energéticos",
            "Café",
            "Chocolate e snacks",
        }
    )

    CATEGORIAS_ADJACENTES_POR_CICLO = 8

    TERMOS_PADRAO = [termos[0] for termos in TERMOS_POR_CATEGORIA.values() if termos]

    @classmethod
    def _obter_termos_padrao_rotativos(
        cls,
        momento: datetime | None = None,
    ) -> list[str]:
        agora = momento or datetime.now()
        janela = agora.toordinal() * 48 + agora.hour * 2 + (1 if agora.minute >= 30 else 0)
        selecionados: list[str] = []

        for deslocamento, (categoria, termos) in enumerate(cls.TERMOS_POR_CATEGORIA.items()):
            if categoria not in cls.CATEGORIAS_PRIORITARIAS or not termos:
                continue
            indice = (janela + deslocamento) % len(termos)
            selecionados.append(termos[indice])
            if len(termos) > 1:
                extra = (indice + max(1, len(termos) // 2)) % len(termos)
                selecionados.append(termos[extra])

        adjacentes = [
            (categoria, termos)
            for categoria, termos in cls.TERMOS_POR_CATEGORIA.items()
            if (
                termos
                and categoria not in cls.CATEGORIAS_PRIORITARIAS
                and categoria not in cls.CATEGORIAS_SECUNDARIAS
            )
        ]
        if adjacentes:
            quantidade = min(cls.CATEGORIAS_ADJACENTES_POR_CICLO, len(adjacentes))
            inicio = (janela * quantidade) % len(adjacentes)
            for deslocamento in range(quantidade):
                _, termos = adjacentes[(inicio + deslocamento) % len(adjacentes)]
                selecionados.append(termos[(janela + deslocamento) % len(termos)])

        secundarios = [
            (categoria, cls.TERMOS_POR_CATEGORIA[categoria])
            for categoria in cls.TERMOS_POR_CATEGORIA
            if categoria in cls.CATEGORIAS_SECUNDARIAS and cls.TERMOS_POR_CATEGORIA[categoria]
        ]
        if secundarios:
            _, termos = secundarios[janela % len(secundarios)]
            indice_termo = (janela // len(secundarios)) % len(termos)
            selecionados.append(termos[indice_termo])

        return list(dict.fromkeys(selecionados))

    PRODUTOS_POR_TERMO = 2
    SNAPSHOTS_EXTRA_POR_CICLO = 2
    TENTATIVAS_RATE_LIMIT_PADRAO = 2

    def __init__(
        self,
        termos_busca: list[str] | None = None,
        *,
        cliente_catalogo: ClienteCatalogoMercadoLivre | None = None,
        sleep_fn=None,
        tentativas_rate_limit: int = TENTATIVAS_RATE_LIMIT_PADRAO,
    ) -> None:
        termos_recebidos = (
            termos_busca if termos_busca is not None else self._obter_termos_padrao_rotativos()
        )

        self.termos_busca = [termo.strip() for termo in termos_recebidos if termo and termo.strip()]

        if not self.termos_busca:
            raise ValueError("A lista de termos do Mercado Livre " "não pode estar vazia.")

        self.cliente_catalogo = (
            cliente_catalogo if cliente_catalogo is not None else ClienteCatalogoMercadoLivre()
        )

        self._sleep_fn = sleep_fn if sleep_fn is not None else time.sleep

        if (
            isinstance(
                tentativas_rate_limit,
                bool,
            )
            or not isinstance(
                tentativas_rate_limit,
                int,
            )
            or tentativas_rate_limit < 0
        ):
            raise ValueError("tentativas_rate_limit precisa ser " "inteiro maior ou igual a zero.")

        self.tentativas_rate_limit = tentativas_rate_limit

        self._domain_cache: dict[
            str,
            str | None,
        ] = {}

    @classmethod
    def _categoria_do_termo(
        cls,
        termo: str,
    ) -> str | None:
        normalizado = str(termo or "").strip().casefold()

        if not normalizado:
            return None

        for categoria, termos in cls.TERMOS_POR_CATEGORIA.items():
            for termo_categoria in termos:
                if termo_categoria.strip().casefold() == normalizado:
                    return categoria

        return None

    @staticmethod
    def _consulta_enriquecida(
        termo: str,
        categoria: str | None,
    ) -> str:
        termo = str(termo or "").strip()

        categoria = str(categoria or "").strip()

        if not categoria:
            return termo

        if categoria.casefold() in termo.casefold():
            return termo

        return f"{categoria} {termo}".strip()

    def _executar_api_com_backoff(
        self,
        operacao,
        *,
        descricao: str,
    ):
        tentativa = 0

        while True:
            try:
                return operacao()

            except ErroApiMercadoLivre as erro:
                if erro.status_code != 429 or tentativa >= self.tentativas_rate_limit:
                    raise

                espera = min(
                    2.0 * (2**tentativa),
                    8.0,
                )

                tentativa += 1

                logger.warning(
                    "Mercado Livre API limitou '%s'. " "Nova tentativa %s/%s em %.1fs.",
                    descricao,
                    tentativa,
                    self.tentativas_rate_limit,
                    espera,
                )

                self._sleep_fn(espera)

    def _obter_domain_id(
        self,
        *,
        termo: str,
        categoria: str | None,
        consulta: str,
    ) -> str | None:
        if categoria:
            chave_cache = "categoria:" + categoria.strip().casefold()
        else:
            chave_cache = "termo:" + termo.strip().casefold()

        if chave_cache in self._domain_cache:
            return self._domain_cache[chave_cache]

        dominios = self._executar_api_com_backoff(
            lambda: (
                self.cliente_catalogo.descobrir_dominios(
                    consulta,
                    limite=3,
                )
            ),
            descricao=("domain_discovery:" + termo),
        )

        if not dominios:
            logger.warning(
                "Mercado Livre nao identificou " "dominio para '%s'.",
                termo,
            )

            self._domain_cache[chave_cache] = None

            return None

        domain_id = str(dominios[0].domain_id or "").strip().upper()

        if not domain_id:
            self._domain_cache[chave_cache] = None

            return None

        self._domain_cache[chave_cache] = domain_id

        logger.debug(
            "Dominio ML '%s' resolvido para " "categoria '%s' / termo '%s'.",
            domain_id,
            categoria,
            termo,
        )

        return domain_id

    @staticmethod
    def _oferta_de_snapshot(
        snapshot: SnapshotCatalogoMercadoLivre,
    ) -> Oferta | None:
        permalink = str(snapshot.permalink or "").strip()

        if not permalink:
            logger.warning(
                "Snapshot ML %s sem permalink; " "oferta ignorada.",
                snapshot.product_id,
            )

            return None

        return Oferta(
            nome=snapshot.titulo,
            loja="Mercado Livre",
            preco=float(snapshot.preco),
            preco_antigo=None,
            link=permalink,
            imagem=None,
        )

    def buscar_ofertas(
        self,
        limite: int = 5,
    ) -> list[Oferta]:
        if limite <= 0:
            logger.warning(
                "Limite inválido para o " "Mercado Livre: %s.",
                limite,
            )

            return []

        logger.info(
            "Mercado Livre API-first: " "buscando ate %s oferta(s).",
            limite,
        )

        ofertas: list[Oferta] = []

        product_ids_vistos: set[str] = set()
        item_ids_vistos: set[str] = set()

        snapshots_tentados = 0

        orcamento_snapshots = limite + self.SNAPSHOTS_EXTRA_POR_CICLO

        for indice, termo in enumerate(
            self.termos_busca,
            start=1,
        ):
            if len(ofertas) >= limite:
                break

            if snapshots_tentados >= orcamento_snapshots:
                logger.info("Mercado Livre atingiu o " "orcamento de snapshots do ciclo.")
                break

            categoria = self._categoria_do_termo(termo)

            consulta = self._consulta_enriquecida(
                termo,
                categoria,
            )

            logger.info(
                "Pesquisando Mercado Livre API " "(%s/%s): %s",
                indice,
                len(self.termos_busca),
                consulta,
            )

            domain_id = self._obter_domain_id(
                termo=termo,
                categoria=categoria,
                consulta=consulta,
            )

            if not domain_id:
                continue

            faltantes = limite - len(ofertas)

            restante_orcamento = orcamento_snapshots - snapshots_tentados

            limite_produtos = min(
                self.PRODUTOS_POR_TERMO,
                faltantes,
                restante_orcamento,
            )

            if limite_produtos <= 0:
                break

            produtos = self._executar_api_com_backoff(
                lambda consulta=consulta, domain_id=domain_id, limite_produtos=limite_produtos: (
                    self.cliente_catalogo.buscar_produtos(
                        consulta,
                        domain_id=domain_id,
                        limite=limite_produtos,
                    )
                ),
                descricao=("products_search:" + termo),
            )

            adicionadas_termo = 0

            for produto in produtos:
                if len(ofertas) >= limite:
                    break

                if snapshots_tentados >= orcamento_snapshots:
                    break

                product_id = str(produto.product_id or "").strip().upper()

                if not product_id:
                    continue

                if product_id in product_ids_vistos:
                    continue

                product_ids_vistos.add(product_id)

                status = str(produto.status or "").strip().casefold()

                if status and status != "active":
                    continue

                produto_domain_id = str(produto.domain_id or "").strip().upper()

                if produto_domain_id and produto_domain_id != domain_id:
                    logger.debug(
                        "Produto %s descartado: " "dominio %s != %s.",
                        product_id,
                        produto_domain_id,
                        domain_id,
                    )
                    continue

                snapshots_tentados += 1

                try:
                    snapshot = self._executar_api_com_backoff(
                        lambda product_id=product_id: (
                            self.cliente_catalogo.consultar_snapshot(product_id)
                        ),
                        descricao=("catalog_snapshot:" + product_id),
                    )

                except ErroApiMercadoLivre as erro:
                    if erro.status_code == 404:
                        logger.info(
                            "Produto ML %s deixou " "de existir durante o ciclo.",
                            product_id,
                        )
                        continue

                    raise

                if snapshot is None:
                    continue

                item_id = str(snapshot.item_id or "").strip().upper()

                if not item_id:
                    continue

                if item_id in item_ids_vistos:
                    continue

                oferta = self._oferta_de_snapshot(snapshot)

                if oferta is None:
                    continue

                item_ids_vistos.add(item_id)

                ofertas.append(oferta)

                adicionadas_termo += 1

            logger.info(
                "Termo ML '%s': %s nova(s) " "oferta(s) API.",
                termo,
                adicionadas_termo,
            )

        logger.info(
            "Mercado Livre API-first: %s "
            "oferta(s) unica(s) coletada(s); "
            "%s snapshot(s) tentado(s).",
            len(ofertas),
            snapshots_tentados,
        )

        return ofertas
