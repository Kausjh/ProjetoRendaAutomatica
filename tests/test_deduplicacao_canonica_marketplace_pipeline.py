from models.oferta import Oferta
from services.executor_pipeline import ExecutorPipeline


def criar_oferta(
    indice: int,
    loja: str,
    marketplace: str,
    preco: float,
) -> Oferta:
    oferta = Oferta(
        nome=f"Mouse Logitech G305 {indice}",
        loja=loja,
        preco=preco,
        preco_antigo=None,
        link=(f"https://example.com/" f"{marketplace}/{indice}"),
        imagem=None,
        marketplace=marketplace,
    )

    oferta.produto_canonico = "Mouse Logitech G305"
    oferta.chave_produto_canonica = "mouse-logitech-g305"
    oferta.confianca_normalizacao = 95.0
    oferta.anomalia_publicavel = False

    return oferta


def criar_executor() -> ExecutorPipeline:
    executor = object.__new__(ExecutorPipeline)
    executor.confianca_minima_deduplicacao = 90.0
    return executor


def item(
    oferta: Oferta,
    score: float,
):
    return (
        oferta,
        score,
        None,
        False,
        False,
    )


def test_mesmo_produto_de_marketplaces_diferentes_coexiste():
    executor = criar_executor()

    mercado_livre = criar_oferta(
        indice=1,
        loja="Mercado Livre",
        marketplace="mercado_livre",
        preco=200.0,
    )

    shopee = criar_oferta(
        indice=2,
        loja="Shopee",
        marketplace="shopee",
        preco=180.0,
    )

    resultado, removidas = executor._deduplicar_ofertas_canonicas(
        [
            item(mercado_livre, 80.0),
            item(shopee, 60.0),
        ]
    )

    assert len(resultado) == 2
    assert removidas == 0

    marketplaces = {oferta.marketplace for oferta, *_ in resultado}

    assert marketplaces == {
        "mercado_livre",
        "shopee",
    }


def test_mesmo_produto_no_mesmo_marketplace_continua_deduplicado():
    executor = criar_executor()

    oferta_a = criar_oferta(
        indice=1,
        loja="Mercado Livre",
        marketplace="mercado_livre",
        preco=200.0,
    )

    oferta_b = criar_oferta(
        indice=2,
        loja="Mercado Livre",
        marketplace="mercado_livre",
        preco=180.0,
    )

    resultado, removidas = executor._deduplicar_ofertas_canonicas(
        [
            item(oferta_a, 80.0),
            item(oferta_b, 75.0),
        ]
    )

    assert len(resultado) == 1
    assert removidas == 1
    assert resultado[0][0].preco == 180.0
