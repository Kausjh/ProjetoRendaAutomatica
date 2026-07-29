"""
Configurações compartilhadas dos testes.

Este arquivo contém fixtures reutilizáveis por toda a suíte de testes.

Sempre que um teste precisar criar uma Oferta de exemplo, utilizar
a fixture "oferta_exemplo" em vez de criar objetos manualmente.
"""

import pytest

from models.oferta import Oferta


@pytest.fixture
def oferta_exemplo():
    """
    Retorna uma Oferta válida para utilização nos testes.
    """

    return Oferta(
        titulo="Ryzen 7 5700X",
        preco=799.90,
        preco_original=1199.90,
        desconto=33,
        loja="Kabum",
        link="https://exemplo.com/produto",
        imagem="https://exemplo.com/imagem.jpg",
    )
