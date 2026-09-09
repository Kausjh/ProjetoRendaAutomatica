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


def test_promocao_marketplace_confirmada_confirma_preco_sem_validar_codigo():
    item = oferta()

    item.origem_descoberta = "social_scout"
    item.preco_condicional_observado = 2399.0
    item.codigo_cupom_observado = "GPU300"
    item.cupom_validado_descoberta = False

    item.status_promocao_marketplace = "confirmada"
    item.promocao_marketplace_confirmada = True
    item.preco_promocional_marketplace = 2399.0
    item.preco_grupo_confere_promocao = True

    resultado = InteligenciaSinalPreco().analisar(item)

    assert resultado.status == "confirmado"
    assert resultado.confirmado is True

    # Preco confirmado != codigo confirmado.
    assert resultado.cupom_validado is False

    assert resultado.confianca == 100.0

    assert resultado.economia_percentual == 11.12

    assert "preco_promocional_marketplace_confirmado" in resultado.motivos

    assert "codigo_cupom_ainda_nao_validado" in resultado.motivos


def test_promocao_marketplace_com_preco_divergente_continua_observada():
    item = oferta()

    item.origem_descoberta = "social_scout"
    item.preco_condicional_observado = 2399.0
    item.codigo_cupom_observado = "GPU300"
    item.cupom_validado_descoberta = False

    item.status_promocao_marketplace = "confirmada"
    item.promocao_marketplace_confirmada = True

    item.preco_promocional_marketplace = 2499.0
    item.preco_grupo_confere_promocao = False

    resultado = InteligenciaSinalPreco().analisar(item)

    assert resultado.status == "observado"
    assert resultado.confirmado is False
    assert resultado.cupom_validado is False


def test_metadata_inconsistente_nao_consegue_confirmar_preco():
    item = oferta()

    item.origem_descoberta = "social_scout"
    item.preco_condicional_observado = 2399.0
    item.codigo_cupom_observado = "GPU300"
    item.cupom_validado_descoberta = False

    item.promocao_marketplace_confirmada = True

    # Booleano diz que confere...
    item.preco_grupo_confere_promocao = True

    # ...mas os valores nao.
    item.preco_promocional_marketplace = 2499.0

    resultado = InteligenciaSinalPreco().analisar(item)

    assert resultado.status == "observado"
    assert resultado.confirmado is False


def test_promocao_confirmada_sem_preco_promocional_nao_confirma():
    item = oferta()

    item.origem_descoberta = "social_scout"
    item.preco_condicional_observado = 2399.0
    item.codigo_cupom_observado = "GPU300"
    item.cupom_validado_descoberta = False

    item.promocao_marketplace_confirmada = True
    item.preco_grupo_confere_promocao = True
    item.preco_promocional_marketplace = None

    resultado = InteligenciaSinalPreco().analisar(item)

    assert resultado.status == "observado"
    assert resultado.confirmado is False


def test_aplicar_promocao_marketplace_preserva_preco_e_codigo_nao_validado():
    item = oferta()

    preco_oficial_antes = item.preco

    item.origem_descoberta = "social_scout"
    item.preco_condicional_observado = 2399.0
    item.codigo_cupom_observado = "GPU300"
    item.cupom_validado_descoberta = False

    item.status_promocao_marketplace = "confirmada"
    item.promocao_marketplace_confirmada = True
    item.preco_promocional_marketplace = 2399.0
    item.preco_grupo_confere_promocao = True

    resultado = InteligenciaSinalPreco().aplicar(item)

    assert resultado.confirmado is True
    assert resultado.cupom_validado is False

    assert item.status_sinal_preco == "confirmado"

    # Fonte de verdade nao muda.
    assert item.preco == preco_oficial_antes

    # Sinal social permanece separado.
    assert item.preco_condicional_observado == 2399.0

    # Codigo continua explicitamente nao validado.
    assert item.cupom_validado_descoberta is False
