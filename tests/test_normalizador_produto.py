from models.oferta import Oferta
from services.normalizador_produto import NormalizadorProduto


def oferta(nome: str, categoria: str = "Processador") -> Oferta:
    item = Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=1000.0,
        preco_antigo=None,
        link="https://www.mercadolivre.com.br/item",
        imagem=None,
    )
    item.categoria = categoria
    return item


def test_normaliza_ryzen_5700x_com_alta_confianca():
    item = oferta("Processador AMD Ryzen 7 5700X 8 Core AM4")

    resultado = NormalizadorProduto().normalizar(item)

    assert resultado.nome_canonico == "Ryzen 7 5700X"
    assert resultado.chave_canonica == "ryzen_7_5700x"
    assert resultado.confianca >= 90


def test_5700x_e_5700x3d_nao_recebem_mesma_chave():
    normalizador = NormalizadorProduto()

    comum = normalizador.normalizar(oferta("AMD Ryzen 7 5700X"))
    x3d = normalizador.normalizar(oferta("AMD Ryzen 7 5700X3D"))

    assert comum.chave_canonica != x3d.chave_canonica


def test_normaliza_rtx_4060_independente_da_marca_da_placa():
    normalizador = NormalizadorProduto()

    zotac = normalizador.normalizar(
        oferta("Zotac GeForce RTX 4060 Twin Edge 8GB", "Placa de vídeo")
    )
    asus = normalizador.normalizar(oferta("Asus Dual NVIDIA RTX 4060 OC 8GB", "Placa de vídeo"))

    assert zotac.chave_canonica == "rtx_4060"
    assert asus.chave_canonica == "rtx_4060"
