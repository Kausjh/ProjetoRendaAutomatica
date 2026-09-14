from types import SimpleNamespace

import pytest

from services.classificador_produto import ClassificadorProduto


def classificar(nome: str):
    return ClassificadorProduto().classificar(SimpleNamespace(nome=nome))


@pytest.mark.parametrize(
    "nome",
    [
        (
            "Novo Ventilador GPU 87MM 4PIN PLD09210S12HH RTX4060 4060TI "
            "Para Placa Grafica MSI GEFORCE RTX 4060 TI VENTUS 3X"
        ),
        "Capa para Gigabyte RTX 4060 - 4060 Ti 2 Fans Cover Decorativa GPU Gamer",
        (
            "Capa para MSI RTX 4060/4060Ti 5060 / 5060 Ti Ventus 2X "
            "Cover Decorativa GPU Gamer Personalizacao PC"
        ),
        "Capa para MSI RTX 5060 - 5060 Ti Ventus 2X Cover Decorativa GPU Gamer",
        "Kit 3 Fans para RTX 4060 Ti placa de video",
        "Backplate para GeForce RTX 4070 GPU",
    ],
)
def test_acessorio_que_cita_gpu_nao_e_classificado_como_gpu(nome):
    resultado = classificar(nome)

    assert resultado.eh_nicho is False
    assert resultado.categoria is None
    assert resultado.relevancia == 0
    assert "acessorio de placa de video" in resultado.motivo.lower()


@pytest.mark.parametrize(
    "nome",
    [
        "Placa de Video MSI GeForce RTX 4060 Ventus 2X 8GB GDDR6",
        "Placa de Video Gigabyte RTX 5060 Gaming OC 8GB GDDR7",
        "GeForce RTX 4060 Dual Fan 8GB GDDR6",
        "GPU Radeon RX 7600 Dual Fan 8GB GDDR6",
    ],
)
def test_gpu_real_continua_classificada_como_gpu(nome):
    resultado = classificar(nome)

    assert resultado.eh_nicho is True
    assert resultado.categoria == "Placa de vídeo"
