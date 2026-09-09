from services.scout.promotion_engine_ml import (
    PromotionEngineMercadoLivre,
)


def engine():
    return PromotionEngineMercadoLivre()


def test_sem_cupom_nao_confirma_promocao():
    resultado = engine().analisar_texto_card(
        texto_card=("Produto Gamer " "R$ 400 R$ 350 12% OFF"),
        id_produto="MLB1",
        preco_oficial=350.0,
        preco_final_grupo=300.0,
    )

    assert resultado.status == "sem_evidencia"
    assert resultado.promocao_confirmada is False
    assert resultado.preco_grupo_confere is None


def test_preco_final_com_cupom_confirma_promocao():
    resultado = engine().analisar_texto_card(
        texto_card=("Produto Gamer " "R$ 400 R$ 350 " "R$ 300 com Cupom"),
        id_produto="MLB1",
        preco_oficial=350.0,
        preco_final_grupo=300.0,
    )

    assert resultado.status == "confirmada"
    assert resultado.promocao_confirmada is True

    assert resultado.tipo_promocao == "preco_final_com_cupom"

    assert resultado.preco_promocional == 300.0
    assert resultado.preco_grupo_confere is True

    # Promotion Engine V1 nao prova codigo.
    assert resultado.codigo_cupom_validado is False


def test_preco_marketplace_diferente_do_grupo_nao_confere():
    resultado = engine().analisar_texto_card(
        texto_card=("RX 9060 XT " "R$ 4.003 R$ 3.670 " "R$ 3.470 com Cupom"),
        id_produto="MLB51865733",
        preco_oficial=3670.0,
        preco_final_grupo=3096.0,
    )

    assert resultado.promocao_confirmada is True
    assert resultado.preco_promocional == 3470.0

    assert resultado.preco_grupo_confere is False

    assert resultado.codigo_cupom_validado is False


def test_valor_off_com_cupom():
    resultado = engine().analisar_texto_card(
        texto_card=("Xbox Pulse Red " "R$ 358,79 " "R$ 60 OFF com Cupom"),
        id_produto="MLB30055107",
        preco_oficial=358.79,
        preco_final_grupo=298.79,
    )

    assert resultado.promocao_confirmada is True

    assert resultado.tipo_promocao == "valor_off_com_cupom"

    assert resultado.valor_desconto == 60.0
    assert resultado.preco_promocional == 298.79
    assert resultado.preco_grupo_confere is True


def test_percentual_off_com_cupom():
    resultado = engine().analisar_texto_card(
        texto_card=("Monitor Gamer " "R$ 1.000 " "20% OFF com Cupom"),
        id_produto="MLB2",
        preco_oficial=1000.0,
        preco_final_grupo=800.0,
    )

    assert resultado.promocao_confirmada is True

    assert resultado.tipo_promocao == "percentual_off_com_cupom"

    assert resultado.desconto_percentual == 20.0
    assert resultado.preco_promocional == 800.0
    assert resultado.preco_grupo_confere is True


def test_cupom_sem_valor_ainda_e_evidencia_de_promocao():
    resultado = engine().analisar_texto_card(
        texto_card=("Produto Gamer " "Cupom disponivel"),
        id_produto="MLB3",
        preco_oficial=500.0,
        preco_final_grupo=None,
    )

    assert resultado.promocao_confirmada is True

    assert resultado.tipo_promocao == "cupom_sem_valor_extraivel"

    assert resultado.preco_promocional is None
    assert resultado.preco_grupo_confere is None


def test_tolerancia_aceita_arredondamento_pequeno():
    resultado = engine().analisar_texto_card(
        texto_card=("Produto " "R$ 299,90 com Cupom"),
        id_produto="MLB4",
        preco_oficial=350.0,
        preco_final_grupo=300.0,
    )

    assert resultado.preco_promocional == 299.90
    assert resultado.preco_grupo_confere is True
