from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco
from services.pontuador_oferta import PontuadorOferta


def oferta_base(preco=900.0, preco_antigo=1000.0, nota_curadoria=90.0):
    oferta = Oferta(
        nome="Placa de Video NVIDIA GeForce RTX 5070 12GB",
        loja="Mercado Livre",
        preco=preco,
        preco_antigo=preco_antigo,
        link="https://mercadolivre.com.br/teste",
        imagem=None,
    )
    oferta.eh_nicho = True
    oferta.relevancia_nicho = 100.0
    oferta.categoria = "Placa de video"
    oferta.nota_curadoria = nota_curadoria
    return oferta


def historico(
    *,
    primeiro=False,
    preco_anterior=1000.0,
    menor_anterior=950.0,
    menor=True,
    variacao=-10.0,
    caiu=True,
    registros=8,
):
    return ResultadoHistoricoPreco(
        primeiro_registro=primeiro,
        preco_anterior=preco_anterior,
        menor_preco_anterior=menor_anterior,
        menor_preco_historico=menor,
        variacao_percentual=variacao,
        preco_caiu=caiu,
        preco_subiu=not caiu and variacao > 0,
        novo_preco_registrado=True,
        quantidade_registros=registros,
    )


def test_promocao_real_com_historico_forte_supera_72():
    p = PontuadorOferta(preco_maximo=10000)
    oferta = oferta_base()
    nota = p.calcular(
        oferta,
        historico(variacao=-10, menor=True, registros=8),
    )

    assert nota >= 72
    assert (
        oferta.componentes_pontuacao["novo_menor_preco"] == PontuadorOferta.PONTOS_NOVO_MENOR_PRECO
    )
    assert oferta.componentes_pontuacao["queda_real_historico"] > 0


def test_desconto_de_loja_sem_historico_nao_basta():
    p = PontuadorOferta(preco_maximo=10000)
    oferta = oferta_base(preco=500, preco_antigo=1000, nota_curadoria=100)
    nota = p.calcular(
        oferta,
        historico(
            primeiro=True,
            menor=True,
            variacao=0,
            caiu=False,
            registros=1,
        ),
    )

    assert nota < 72
    assert oferta.componentes_pontuacao["queda_real_historico"] == 0
    assert oferta.componentes_pontuacao["novo_menor_preco"] == 0
    assert oferta.componentes_pontuacao["maturidade_historico"] == 0


def test_preco_estavel_com_de_por_inflado_fica_abaixo_do_corte():
    p = PontuadorOferta(preco_maximo=10000)
    oferta = oferta_base(preco=500, preco_antigo=1000, nota_curadoria=95)

    nota = p.calcular(
        oferta,
        historico(
            menor=False,
            variacao=0,
            caiu=False,
            registros=10,
        ),
    )

    assert nota < 72


def test_queda_real_maior_recebe_score_maior():
    p = PontuadorOferta(preco_maximo=10000)

    nota_5 = p.calcular(
        oferta_base(),
        historico(variacao=-5, menor=True, registros=8),
    )
    nota_15 = p.calcular(
        oferta_base(),
        historico(variacao=-15, menor=True, registros=8),
    )

    assert nota_15 > nota_5


def test_maturidade_do_historico_importa():
    p = PontuadorOferta(preco_maximo=10000)

    nota_curta = p.calcular(
        oferta_base(),
        historico(variacao=-10, menor=True, registros=2),
    )
    nota_madura = p.calcular(
        oferta_base(),
        historico(variacao=-10, menor=True, registros=10),
    )

    assert nota_madura > nota_curta


def test_nota_comercial_nao_entra_no_score(monkeypatch):
    p = PontuadorOferta(preco_maximo=10000)

    class Resultado:
        def __init__(self, nota):
            self.nota = nota
            self.marca = "Marca"
            self.motivos = ("teste",)

    monkeypatch.setattr(
        p.curadoria_comercial,
        "analisar",
        lambda oferta: Resultado(0),
    )
    oferta_a = oferta_base()
    nota_a = p.calcular(
        oferta_a,
        historico(variacao=-10, menor=True, registros=8),
    )

    monkeypatch.setattr(
        p.curadoria_comercial,
        "analisar",
        lambda oferta: Resultado(100),
    )
    oferta_b = oferta_base()
    nota_b = p.calcular(
        oferta_b,
        historico(variacao=-10, menor=True, registros=8),
    )

    assert nota_a == nota_b
    assert oferta_b.nota_comercial == 100
    assert oferta_b.componentes_pontuacao["potencial_comercial_no_score"] == 0


def test_faixa_de_preco_nao_da_bonus_por_comissao():
    p = PontuadorOferta(preco_maximo=10000)

    barato = oferta_base(preco=200, preco_antigo=220)
    caro = oferta_base(preco=2000, preco_antigo=2200)
    h = historico(variacao=-10, menor=True, registros=8)

    assert p.calcular(barato, h) == p.calcular(caro, h)


def test_product_intelligence_entra_no_score():
    p = PontuadorOferta(preco_maximo=10000)

    oferta = oferta_base(
        preco=900,
        preco_antigo=1000,
    )

    nota = p.calcular(
        oferta,
        historico(
            primeiro=True,
            menor=False,
            variacao=0,
            caiu=False,
            registros=1,
        ),
    )

    assert nota < 72
    assert oferta.nota_produto >= 90

    assert oferta.componentes_pontuacao["inteligencia_produto"] > 0

    assert oferta.componentes_pontuacao["inteligencia_produto_nota"] == oferta.nota_produto


def test_produto_desejavel_sem_sinal_preco_nao_vira_oferta():
    p = PontuadorOferta(preco_maximo=10000)

    oferta = oferta_base(
        preco=900,
        preco_antigo=None,
        nota_curadoria=100,
    )

    nota = p.calcular(
        oferta,
        historico(
            primeiro=False,
            menor=False,
            variacao=0,
            caiu=False,
            registros=10,
        ),
    )

    assert oferta.nota_produto >= 90

    assert oferta.componentes_pontuacao["inteligencia_produto"] == 0

    assert nota < 72


def test_pesos_product_intelligence_totalizam_100():
    total = (
        PontuadorOferta.PONTOS_MAXIMOS_NICHO
        + PontuadorOferta.PONTOS_MAXIMOS_DESCONTO_ANUNCIADO
        + PontuadorOferta.PONTOS_MAXIMOS_PRODUTO
        + PontuadorOferta.PONTOS_MAXIMOS_QUEDA_REAL
        + PontuadorOferta.PONTOS_NOVO_MENOR_PRECO
        + PontuadorOferta.PONTOS_MAXIMOS_MATURIDADE_HISTORICO
        + PontuadorOferta.PONTOS_MAXIMOS_CURADORIA
    )

    assert total == 100.0


def test_score_forte_fica_limitado_a_100():
    p = PontuadorOferta(preco_maximo=10000)

    oferta = oferta_base(
        preco=100,
        preco_antigo=1000,
        nota_curadoria=100,
    )

    nota = p.calcular(
        oferta,
        historico(
            variacao=-90,
            menor=True,
            caiu=True,
            registros=100,
        ),
    )

    assert 99.0 <= nota <= 100.0


def test_sinal_social_nao_validado_nao_habilita_product_intelligence():
    p = PontuadorOferta(preco_maximo=10000)

    oferta = oferta_base(
        preco=2699,
        preco_antigo=None,
    )

    oferta.origem_descoberta = "social_scout"
    oferta.preco_condicional_observado = 2399.0
    oferta.codigo_cupom_observado = "GPU300"
    oferta.cupom_validado_descoberta = False

    nota = p.calcular(
        oferta,
        historico(
            primeiro=False,
            menor=False,
            variacao=0,
            caiu=False,
            registros=3,
        ),
    )

    assert oferta.status_sinal_preco == "observado"

    assert oferta.componentes_pontuacao["sinal_preco_descoberta_confirmado"] == 0.0

    assert oferta.componentes_pontuacao["inteligencia_produto"] == 0.0

    assert nota < 72


def test_sinal_social_confirmado_habilita_product_intelligence():
    p = PontuadorOferta(preco_maximo=10000)

    oferta = oferta_base(
        preco=2699,
        preco_antigo=None,
    )

    oferta.origem_descoberta = "social_scout"
    oferta.preco_condicional_observado = 2399.0
    oferta.codigo_cupom_observado = "GPU300"
    oferta.cupom_validado_descoberta = True

    nota = p.calcular(
        oferta,
        historico(
            primeiro=False,
            menor=False,
            variacao=0,
            caiu=False,
            registros=3,
        ),
    )

    assert oferta.status_sinal_preco == "confirmado"

    assert oferta.componentes_pontuacao["sinal_preco_descoberta_confirmado"] == 1.0

    assert oferta.componentes_pontuacao["inteligencia_produto"] > 0.0

    assert oferta.componentes_pontuacao["economia_condicional_observada"] > 0.0

    # Ainda nao significa publicar automaticamente.
    assert nota < 72
