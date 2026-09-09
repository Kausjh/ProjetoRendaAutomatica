# 63.8738, -149.7525

import pytest

from models.oferta import Oferta
from services.classificador_produto import (
    ClassificadorProduto,
)
from services.historico_precos_service import (
    ResultadoHistoricoPreco,
)
from services.inteligencia_sinal_preco import (
    InteligenciaSinalPreco,
)
from services.pontuador_oferta import (
    PontuadorOferta,
)

PRECO_OFICIAL = 6323.07
PRECO_SOCIAL = 5951.00
PRECO_PROMOCIONAL_OFICIAL = 5951.07


def criar_oferta() -> Oferta:
    oferta = Oferta(
        nome=("Notebook Gamer Acer Nitro V15 " "Intel Core i5 16GB SSD RTX 4060"),
        loja="Mercado Livre",
        preco=PRECO_OFICIAL,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace="mercado_livre",
    )

    oferta.origem_descoberta = "social_scout"

    oferta.preco_condicional_observado = PRECO_SOCIAL

    oferta.codigo_cupom_observado = "CUPOM_SOCIAL_OBSERVADO"

    # O codigo textual nunca foi validado.
    oferta.cupom_validado_descoberta = False

    # O marketplace, entretanto, confirmou
    # oficialmente um preco promocional que
    # coincide com o preco observado no grupo.
    oferta.status_promocao_marketplace = "confirmada"

    oferta.promocao_marketplace_confirmada = True

    oferta.tipo_promocao_marketplace = "valor_off_com_cupom"

    oferta.preco_promocional_marketplace = PRECO_PROMOCIONAL_OFICIAL

    oferta.valor_desconto_promocional_marketplace = PRECO_OFICIAL - PRECO_PROMOCIONAL_OFICIAL

    oferta.desconto_promocional_marketplace_percentual = (
        (PRECO_OFICIAL - PRECO_PROMOCIONAL_OFICIAL) / PRECO_OFICIAL * 100.0
    )

    oferta.preco_grupo_confere_promocao = True

    oferta.fonte_promocao_marketplace = "marketplace_oficial"

    oferta.motivo_promocao_marketplace = "preco_promocional_oficial_confere_com_grupo"

    ClassificadorProduto().aplicar_classificacao(oferta)

    oferta.nota_curadoria = 86.0

    return oferta


def historico_neutro(
    preco: float,
) -> ResultadoHistoricoPreco:
    return ResultadoHistoricoPreco(
        primeiro_registro=False,
        preco_anterior=preco,
        menor_preco_anterior=preco,
        menor_preco_historico=False,
        variacao_percentual=0.0,
        preco_caiu=False,
        preco_subiu=False,
        novo_preco_registrado=True,
        quantidade_registros=3,
    )


def test_canario_real_confirma_preco_sem_validar_codigo():
    oferta = criar_oferta()

    sinal = InteligenciaSinalPreco().analisar(oferta)

    assert sinal.status == "confirmado"
    assert sinal.confirmado is True
    assert sinal.confianca == 100.0

    assert sinal.cupom_validado is False

    assert oferta.cupom_validado_descoberta is False

    assert sinal.economia_percentual == pytest.approx(
        5.88,
        abs=0.01,
    )

    # Invariante principal:
    # confirmar preco promocional nao altera
    # o preco oficial/base da Oferta.
    assert oferta.preco == PRECO_OFICIAL


def test_canario_real_preco_efetivo_entra_no_deal_score():
    oferta = criar_oferta()

    pontuador = PontuadorOferta(preco_maximo=10000)

    score = pontuador.calcular(
        oferta,
        historico_neutro(PRECO_OFICIAL),
    )

    componentes = oferta.componentes_pontuacao

    assert score > 0.0

    assert componentes["desconto_efetivo_confirmado"] == pytest.approx(
        1.47,
        abs=0.01,
    )

    assert componentes["desconto_pontuado"] >= componentes["desconto_efetivo_confirmado"]

    # A serie oficial continua neutra.
    assert componentes["queda_real_historico"] == 0.0

    assert componentes["novo_menor_preco"] == 0.0

    assert oferta.preco == PRECO_OFICIAL


def test_canario_real_preserva_separacao_preco_e_cupom():
    oferta = criar_oferta()

    sinal = InteligenciaSinalPreco().analisar(oferta)

    assert oferta.promocao_marketplace_confirmada is True

    assert oferta.preco_grupo_confere_promocao is True

    assert sinal.confirmado is True

    # Preco confirmado != codigo confirmado.
    assert oferta.codigo_cupom_observado == "CUPOM_SOCIAL_OBSERVADO"

    assert sinal.cupom_validado is False
    assert oferta.cupom_validado_descoberta is False
