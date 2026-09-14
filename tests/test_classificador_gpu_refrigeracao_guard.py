from types import SimpleNamespace

import pytest

from services.classificador_produto import ClassificadorProduto

TITULO_REAL_SHOPEE = (
    "90MM CF9015U12D FD9015U12D PLA09215B12H DC12V "
    "Ventilador De Placa Gráfica Para ProArt GeForce RTX 4070 "
    "4060 Ti 4060"
)


def classificar(titulo: str):
    return ClassificadorProduto().classificar(SimpleNamespace(nome=titulo))


def test_titulo_real_shopee_ventilador_gpu_e_bloqueado():
    resultado = classificar(TITULO_REAL_SHOPEE)

    assert resultado.eh_nicho is False
    assert resultado.categoria is None
    assert resultado.relevancia == 0
    assert "refrigeracao_placa_gpu" in resultado.termos_encontrados


@pytest.mark.parametrize(
    "titulo",
    [
        "Ventoinha da placa de vídeo compativel com GeForce RTX 4060 Ti",
        "Cooler de placa grafica para Radeon RX 7600",
        "Fan de placa gráfica para RTX 5070",
    ],
)
def test_variantes_de_refrigeracao_gpu_sao_bloqueadas(titulo):
    resultado = classificar(titulo)

    assert resultado.eh_nicho is False
    assert resultado.categoria is None
    assert resultado.relevancia == 0
    assert resultado.termos_encontrados


@pytest.mark.parametrize(
    "titulo",
    [
        "Placa de Video ASUS ProArt GeForce RTX 4070 12GB GDDR6X",
        "Placa Grafica MSI Gaming GeForce RTX 4070 Ti 12GB GDDR6X",
        "Placa de Video RTX 4060 Dual Fan 8GB GDDR6",
    ],
)
def test_gpus_legitimas_continuam_aceitas(titulo):
    resultado = classificar(titulo)

    assert resultado.eh_nicho is True
    assert resultado.categoria == "Placa de vídeo"
