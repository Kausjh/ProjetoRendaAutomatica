from models.oferta import Oferta
from services.inteligencia_sinal_preco import (
    InteligenciaSinalPreco,
)


def oferta() -> Oferta:
    return Oferta(
        nome="NVIDIA RTX 5060",
        loja="Shopee",
        preco=2699.0,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace="shopee",
    )


def test_sem_origem_social_nao_cria_evidencia():
    item = oferta()

    item.preco_condicional_observado = 2399.0
    item.cupom_validado_descoberta = True

    resultado = InteligenciaSinalPreco().analisar(item)

    assert resultado.status == "sem_sinal"
    assert resultado.confirmado is False


def test_nao_validado_e_somente_observado():
    item = oferta()

    item.origem_descoberta = "social_scout"
    item.preco_condicional_observado = 2399.0
    item.codigo_cupom_observado = "GPU300"
    item.cupom_validado_descoberta = False

    resultado = InteligenciaSinalPreco().analisar(item)

    assert resultado.status == "observado"
    assert resultado.confirmado is False
    assert resultado.economia_percentual == 11.12


def test_validado_vira_confirmado():
    item = oferta()

    item.origem_descoberta = "social_scout"
    item.preco_condicional_observado = 2399.0
    item.codigo_cupom_observado = "GPU300"
    item.cupom_validado_descoberta = True

    resultado = InteligenciaSinalPreco().analisar(item)

    assert resultado.status == "confirmado"
    assert resultado.confirmado is True
    assert resultado.confianca == 100.0
    assert resultado.economia_percentual == 11.12


def test_preco_condicional_pior_nao_confirma():
    item = oferta()

    item.origem_descoberta = "social_scout"
    item.preco_condicional_observado = 2899.0
    item.cupom_validado_descoberta = True

    resultado = InteligenciaSinalPreco().analisar(item)

    assert resultado.confirmado is False
    assert resultado.economia_percentual == 0.0


def test_aplicar_nao_substitui_preco_oficial():
    item = oferta()

    item.origem_descoberta = "social_scout"
    item.preco_condicional_observado = 2399.0
    item.cupom_validado_descoberta = True

    InteligenciaSinalPreco().aplicar(item)

    assert item.preco == 2699.0
    assert item.status_sinal_preco == "confirmado"
    assert item.economia_condicional_percentual == 11.12
