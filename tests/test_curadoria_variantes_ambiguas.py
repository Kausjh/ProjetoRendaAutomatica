from models.oferta import Oferta
from services.curadoria_publicacao import (
    CuradoriaPublicacao,
)


def criar_oferta(
    nome: str,
    categoria: str = "Placa de v\u00eddeo",
) -> Oferta:
    oferta = Oferta(
        nome=nome,
        loja="Shopee",
        preco=739.99,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace="shopee",
    )

    oferta.eh_nicho = True
    oferta.categoria = categoria
    oferta.relevancia_nicho = 90.0
    oferta.confianca_normalizacao = 95.0

    return oferta


def test_bloqueia_anuncio_real_com_muitos_modelos():
    oferta = criar_oferta(
        "Placa De Video Rx 580 8gb, 560 4gb, "
        "Rtx 4060 3060 2060, Gtx 960, "
        "Rx 5500 6600 Gamer Diversos Modelos"
    )

    resultado = CuradoriaPublicacao().analisar(oferta)

    assert resultado.publicavel is False

    assert any("variacoes ambiguas" in bloqueio for bloqueio in resultado.bloqueios)


def test_bloqueia_duas_gpus_no_mesmo_anuncio():
    oferta = criar_oferta("Placa de Video RTX 3060 ou RTX 4060 8GB")

    resultado = CuradoriaPublicacao().analisar(oferta)

    assert resultado.publicavel is False


def test_bloqueia_diversos_modelos_sem_enumeracao():
    oferta = criar_oferta("Placa de Video Gamer Original " "Diversos Modelos Com Nota Fiscal")

    resultado = CuradoriaPublicacao().analisar(oferta)

    assert resultado.publicavel is False


def test_uma_rtx_4060_legitima_continua_publicavel():
    oferta = criar_oferta("Placa de Video RTX 4060 8GB GDDR6")

    resultado = CuradoriaPublicacao().analisar(oferta)

    assert resultado.publicavel is True


def test_uma_rx_580_legitima_continua_publicavel():
    oferta = criar_oferta("Placa de Video Radeon RX 580 8GB GDDR5")

    resultado = CuradoriaPublicacao().analisar(oferta)

    assert resultado.publicavel is True


def test_rtx_4070_ti_super_continua_publicavel():
    oferta = criar_oferta("Placa de Video RTX 4070 Ti Super 16GB")

    resultado = CuradoriaPublicacao().analisar(oferta)

    assert resultado.publicavel is True


def test_regra_nao_afeta_notebook():
    oferta = criar_oferta(
        ("Notebook Gamer compativel com " "RTX 3060 e RTX 4060"),
        categoria="Notebook",
    )

    resultado = CuradoriaPublicacao().analisar(oferta)

    assert not any("variacoes ambiguas" in bloqueio for bloqueio in resultado.bloqueios)
