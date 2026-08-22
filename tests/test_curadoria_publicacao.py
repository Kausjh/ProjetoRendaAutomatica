from models.oferta import Oferta
from services.curadoria_publicacao import CuradoriaPublicacao


def criar_oferta(
    nome: str,
    categoria: str,
    preco: float,
    relevancia: float = 90.0,
    confianca: float = 95.0,
) -> Oferta:
    item = Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=preco,
        preco_antigo=None,
        link="https://www.mercadolivre.com.br/item",
        imagem=None,
    )
    item.eh_nicho = True
    item.categoria = categoria
    item.relevancia_nicho = relevancia
    item.confianca_normalizacao = confianca
    return item


def test_rejeita_produto_usado():
    item = criar_oferta(
        "Placa de Video RTX 4060 Usada",
        "Placa de vídeo",
        1800.0,
    )

    resultado = CuradoriaPublicacao().analisar(item)

    assert not resultado.publicavel
    assert any("Condição" in motivo for motivo in resultado.bloqueios)


def test_rejeita_preco_incompativel_com_categoria():
    item = criar_oferta(
        "Placa de Video RTX 4060 8GB",
        "Placa de vídeo",
        79.90,
    )

    resultado = CuradoriaPublicacao().analisar(item)

    assert not resultado.publicavel
    assert any("incompatível" in motivo for motivo in resultado.bloqueios)


def test_produto_normal_passa():
    item = criar_oferta(
        "Placa de Video RTX 4060 8GB",
        "Placa de vídeo",
        1999.0,
    )

    resultado = CuradoriaPublicacao().analisar(item)

    assert resultado.publicavel
    assert resultado.nota >= 55


def test_combo_perde_nota_sem_ser_bloqueado_por_palavra_sozinha():
    item = criar_oferta(
        "Combo RTX 4060 + Fonte 600W",
        "Placa de vídeo",
        2400.0,
        relevancia=70.0,
        confianca=45.0,
    )

    resultado = CuradoriaPublicacao(nota_minima=70).analisar(item)

    assert not resultado.publicavel
    assert any("Kit/combo" in motivo for motivo in resultado.motivos)
