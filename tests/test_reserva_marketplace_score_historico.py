from models.oferta import Oferta
from services.executor_pipeline import ExecutorPipeline


def criar_oferta(
    nome: str,
    loja: str,
    marketplace: str,
    score: float,
):
    oferta = Oferta(
        nome=nome,
        loja=loja,
        preco=100.0,
        preco_antigo=None,
        link=("https://example.com/" + marketplace + "/" + nome.replace(" ", "-")),
        imagem=None,
        marketplace=marketplace,
    )

    oferta.categoria = "Mouse"
    oferta.tipo_oportunidade = "normal"

    return (
        oferta,
        score,
        None,
        False,
        False,
    )


def test_marketplace_novo_respeita_piso_editorial():
    mercado_livre = criar_oferta(
        nome="Produto Mercado Livre",
        loja="Mercado Livre",
        marketplace="mercado_livre",
        score=82.0,
    )

    shopee_fraca = criar_oferta(
        nome="Produto Shopee Fraco",
        loja="Shopee",
        marketplace="shopee",
        score=31.0,
    )

    resultado, reservas = ExecutorPipeline._garantir_diversidade_marketplace(
        selecionados=[mercado_livre],
        candidatos_disponiveis=[
            mercado_livre,
            shopee_fraca,
        ],
        pontuacao_minima=45.0,
    )

    marketplaces = {ExecutorPipeline._chave_marketplace(item[0]) for item in resultado}

    assert reservas == 0
    assert marketplaces == {"mercado_livre"}


def test_marketplace_novo_pode_entrar_acima_do_piso():
    mercado_livre = criar_oferta(
        nome="Produto Mercado Livre",
        loja="Mercado Livre",
        marketplace="mercado_livre",
        score=82.0,
    )

    shopee = criar_oferta(
        nome="Produto Shopee",
        loja="Shopee",
        marketplace="shopee",
        score=48.0,
    )

    resultado, reservas = ExecutorPipeline._garantir_diversidade_marketplace(
        selecionados=[mercado_livre],
        candidatos_disponiveis=[
            mercado_livre,
            shopee,
        ],
        pontuacao_minima=45.0,
    )

    marketplaces = {ExecutorPipeline._chave_marketplace(item[0]) for item in resultado}

    assert reservas == 1
    assert marketplaces == {
        "mercado_livre",
        "shopee",
    }


def test_reserva_escolhe_melhor_shopee_acima_do_piso():
    mercado_livre = criar_oferta(
        nome="Produto Mercado Livre",
        loja="Mercado Livre",
        marketplace="mercado_livre",
        score=90.0,
    )

    shopee_fraca = criar_oferta(
        nome="Shopee A",
        loja="Shopee",
        marketplace="shopee",
        score=30.0,
    )

    shopee_boa = criar_oferta(
        nome="Shopee B",
        loja="Shopee",
        marketplace="shopee",
        score=47.0,
    )

    shopee_melhor = criar_oferta(
        nome="Shopee C",
        loja="Shopee",
        marketplace="shopee",
        score=53.0,
    )

    resultado, reservas = ExecutorPipeline._garantir_diversidade_marketplace(
        selecionados=[mercado_livre],
        candidatos_disponiveis=[
            mercado_livre,
            shopee_fraca,
            shopee_boa,
            shopee_melhor,
        ],
        pontuacao_minima=45.0,
    )

    reservadas_shopee = [
        item for item in resultado if ExecutorPipeline._chave_marketplace(item[0]) == "shopee"
    ]

    assert reservas == 1
    assert len(reservadas_shopee) == 1
    assert reservadas_shopee[0][0].nome == "Shopee C"
