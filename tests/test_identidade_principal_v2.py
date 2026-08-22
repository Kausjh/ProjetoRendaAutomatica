from models.oferta import Oferta
from services.classificador_produto import ClassificadorProduto
from services.normalizador_produto import NormalizadorProduto


def criar(nome: str, preco: float = 1000.0) -> Oferta:
    return Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=preco,
        preco_antigo=None,
        link="https://www.mercadolivre.com.br/item",
        imagem=None,
    )


def classificar(nome: str) -> Oferta:
    oferta = criar(nome)
    ClassificadorProduto().aplicar_classificacao(oferta)
    return oferta


def test_notebook_com_ryzen_e_rtx_continua_notebook():
    oferta = classificar("Notebook Gamer Acer Nitro V15 Ryzen 7 7735HS RTX 4050 16GB 512GB SSD")
    assert oferta.categoria == "Notebook"


def test_pc_completo_com_ryzen_e_rtx_continua_computador():
    oferta = classificar("PC Gamer Ryzen 5 5500 16GB SSD 1TB RTX 4060")
    assert oferta.categoria == "Computador e Mini PC"


def test_kit_upgrade_nao_vira_processador():
    oferta = classificar("Kit Upgrade Ryzen 7 5700X + B550M Aorus Elite + 32GB RAM")
    assert oferta.categoria == "Kit upgrade"


def test_gpu_avulsa_continua_gpu():
    oferta = classificar("Placa de Vídeo Asus GeForce RTX 4060 8GB")
    assert oferta.categoria == "Placa de vídeo"


def test_notebook_nao_e_deduplicado_pela_gpu_interna():
    oferta = classificar("Notebook Gamer Acer Nitro V15 Ryzen 7 7735HS RTX 4050 16GB 512GB SSD")
    resultado = NormalizadorProduto().normalizar(oferta)
    assert resultado.nome_canonico != "RTX 4050"
    assert resultado.confianca < 90


def test_gpu_avulsa_recebe_normalizacao_de_alta_confianca():
    oferta = classificar("Placa de Vídeo Asus GeForce RTX 4060 8GB")
    resultado = NormalizadorProduto().normalizar(oferta)
    assert resultado.nome_canonico == "RTX 4060"
    assert resultado.confianca >= 90


def test_acessorio_de_headset_e_bloqueado():
    oferta = classificar("Headband Almofada Headset HyperX Cloud 2")
    assert oferta.eh_nicho is False
