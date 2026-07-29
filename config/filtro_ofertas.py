from __future__ import annotations

MARCAS_PRIORITARIAS: dict[str, int] = {
    "logitech": 40,
    "redragon": 40,
    "hyperx": 40,
    "corsair": 40,
    "kingston": 40,
    "sandisk": 35,
    "western digital": 40,
    "wd": 30,
    "crucial": 40,
    "samsung": 40,
    "lg": 40,
    "aoc": 40,
    "acer": 35,
    "asus": 40,
    "msi": 40,
    "gigabyte": 40,
    "dell": 35,
    "lenovo": 35,
    "intel": 35,
    "amd": 40,
    "nvidia": 40,
    "tp-link": 35,
    "tplink": 35,
    "baseus": 35,
    "anker": 40,
    "soundcore": 40,
    "ugreen": 35,
    "xiaomi": 35,
    "jbl": 40,
    "edifier": 40,
    "8bitdo": 40,
    "seagate": 35,
    "razer": 40,
    "steelseries": 40,
    "cooler master": 35,
    "deepcool": 35,
    "pcyes": 30,
    "elgato": 40,
    "motorola": 35,
    "apple": 40,
    "haylou": 30,
    "qcy": 30,
}


PALAVRAS_PROIBIDAS: set[str] = {
    "usado",
    "usada",
    "seminovo",
    "seminova",
    "recondicionado",
    "recondicionada",
    "refurbished",
    "gift card",
    "giftcard",
    "cartão presente",
    "cartao presente",
    "ebook",
    "e-book",
    "curso online",
    "camiseta",
    "calça",
    "calca",
    "vestido",
    "perfume",
    "shampoo",
    "maquiagem",
    "fralda",
    "ração",
    "racao",
}


PALAVRAS_TECNOLOGIA: dict[str, int] = {
    "memória ram": 22,
    "memoria ram": 22,
    "placa de vídeo": 22,
    "placa de video": 22,
    "placa mãe": 20,
    "placa mae": 20,
    "power bank": 15,
    "carregador portátil": 15,
    "carregador portatil": 15,
    "caixa de som": 15,
    "fone de ouvido": 16,
    "processador": 22,
    "notebook": 20,
    "smartphone": 18,
    "smartwatch": 15,
    "computador": 15,
    "controle": 18,
    "joystick": 18,
    "headset": 18,
    "teclado": 18,
    "monitor": 20,
    "microfone": 18,
    "roteador": 15,
    "webcam": 15,
    "console": 18,
    "playstation": 20,
    "nintendo": 20,
    "carregador": 10,
    "gabinete": 15,
    "cooler": 15,
    "tablet": 18,
    "celular": 18,
    "mouse": 18,
    "ssd": 22,
    "nvme": 22,
    "fonte": 15,
    "fone": 12,
    "xbox": 20,
    "adaptador": 8,
    "cabo": 8,
    "película": 5,
    "pelicula": 5,
    "capinha": 5,
}


CATEGORIAS_PRIORITARIAS: dict[str, int] = {
    "informática": 20,
    "informatica": 20,
    "games": 20,
    "eletrônicos, áudio e vídeo": 15,
    "eletronicos, audio e video": 15,
    "celulares e telefones": 15,
}


TIPOS_ACESSORIOS_COMPATIVEIS: set[str] = {
    "carregador",
    "fonte",
    "cabo",
    "adaptador",
    "película",
    "pelicula",
    "capinha",
}


PREFIXOS_COMPATIBILIDADE_MARCA: tuple[str, ...] = (
    "para",
    "compatível com",
    "compativel com",
    "compatível para",
    "compativel para",
    "serve em",
    "serve para",
    "feito para",
    "ideal para",
    "carregador para",
    "fonte para",
    "cabo para",
    "adaptador para",
    "película para",
    "pelicula para",
    "capinha para",
    "carregador de",
    "fonte de",
)


MARCADORES_COMPATIBILIDADE: tuple[str, ...] = (
    "compatível com",
    "compativel com",
    "compatível para",
    "compativel para",
    "universal para",
    "serve para",
    "serve em",
    "feito para",
    "ideal para",
    "para iphone",
    "para samsung",
    "para xiaomi",
    "para motorola",
    "para lg",
    "para lenovo",
    "para asus",
    "para acer",
    "para dell",
    "para celular",
    "para smartphone",
    "para notebook",
    "suporte para celular",
    "suporte para smartphone",
)


PALAVRAS_ANUNCIO_GENERICO: tuple[str, ...] = (
    "compatível",
    "compativel",
    "universal",
    "premium",
    "turbo",
    "super rápido",
    "super rapido",
    "original importado",
    "similar",
    "tipo",
    "para ps4",
    "p4",
)


HARDWARE_ULTRAPASSADO: tuple[str, ...] = (
    "i5 2400",
    "i5-2400",
    "i5 2500",
    "i5-2500",
    "i5 3470",
    "i5-3470",
    "i5 3570",
    "i5-3570",
    "i7 2600",
    "i7-2600",
    "i7 3770",
    "i7-3770",
    "core 2 duo",
    "core2duo",
    "ddr3",
    "gt 710",
    "gt710",
    "gt 730",
    "gt730",
    "gt 1030",
    "gt1030",
    "rx 550",
    "rx550",
    "ssd 120gb",
    "ssd 120 gb",
)


LIMITES_POR_TIPO: dict[str, int] = {
    "monitor": 4,
    "fone de ouvido": 4,
    "fone": 3,
    "headset": 3,
    "smartphone": 3,
    "celular": 3,
    "smartwatch": 3,
    "placa mãe": 3,
    "placa mae": 3,
    "processador": 3,
    "ssd": 3,
    "nvme": 3,
    "memória ram": 3,
    "memoria ram": 3,
    "caixa de som": 3,
    "roteador": 2,
    "teclado": 3,
    "mouse": 3,
    "controle": 3,
    "joystick": 3,
    "webcam": 2,
    "microfone": 2,
    "carregador": 1,
    "fonte": 1,
    "cabo": 1,
    "adaptador": 1,
    "película": 1,
    "pelicula": 1,
    "capinha": 1,
}


PRECO_MINIMO = 30.0
PRECO_MAXIMO = 2000.0

FAIXA_PRECO_IDEAL_MINIMA = 50.0
FAIXA_PRECO_IDEAL_MAXIMA = 800.0

PONTOS_PRECO_IDEAL = 20
PONTOS_PRECO_ACEITAVEL = 10

PONTOS_DESCONTO_20 = 10
PONTOS_DESCONTO_30 = 20
PONTOS_DESCONTO_40 = 30
PONTOS_DESCONTO_50 = 40

PENALIDADE_PALAVRA_PROIBIDA = -200
PENALIDADE_PRECO_FORA_DA_FAIXA = -80
PENALIDADE_SEM_PRECO = -100
PENALIDADE_SEM_LINK = -100
PENALIDADE_SEM_IMAGEM = -10

PENALIDADE_ANUNCIO_GENERICO = -15
PENALIDADE_TITULO_LONGO = -20
PENALIDADE_TITULO_MUITO_LONGO = -40
PENALIDADE_HARDWARE_ULTRAPASSADO = -150
PENALIDADE_ALEGACAO_SUSPEITA = -150
PENALIDADE_ACESSORIO_SEM_MARCA = -35

LIMITE_PALAVRAS_TITULO_LONGO = 28
LIMITE_PALAVRAS_TITULO_MUITO_LONGO = 45

NOTA_MINIMA_PUBLICACAO = 60
LIMITE_OFERTAS_APROVADAS = 30

LIMITE_PRODUTOS_MESMO_MODELO = 1
