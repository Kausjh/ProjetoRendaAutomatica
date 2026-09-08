# 63.8738, -149.7525

import pytest

from models.oferta import Oferta
from scrapers.social_scout_scraper import (
    SocialScoutScraper,
)
from services.classificador_produto import (
    ClassificadorProduto,
)


def _oferta(
    nome: str,
) -> Oferta:
    return Oferta(
        nome=nome,
        loja="Teste",
        preco=100.0,
        preco_antigo=None,
        link="https://example.invalid/produto",
        imagem=None,
        marketplace="shopee",
    )


@pytest.mark.parametrize(
    "nome",
    (
        "Mini Processador Triturador Sem Fio Eletrico 250ML",
        "Mini Processador de Alimentos 3 Laminas",
        "Processador de Alimentos 1000W",
        "Triturador Processador de Alho Eletrico",
        "Processador Triturador para Cozinha",
    ),
)
def test_social_scout_bloqueia_processador_sem_evidencia_de_cpu(
    nome: str,
):
    oferta = _oferta(nome)

    classificacao = ClassificadorProduto().classificar(oferta)

    assert classificacao.eh_nicho is True
    assert classificacao.categoria == "Processador"

    assert (
        SocialScoutScraper._oferta_fora_escopo_social(
            oferta,
            classificacao,
        )
        is True
    )


@pytest.mark.parametrize(
    "nome",
    (
        "Processador AMD Ryzen 7 5700X",
        "AMD Ryzen 5 5600GT AM4",
        "Processador Intel Core i5-12400F",
        "Intel Core i7 14700K",
        "CPU AMD Ryzen 7 7800X3D",
        "Processador Intel Xeon E5-2670 V3",
    ),
)
def test_social_scout_aceita_processador_com_evidencia_de_cpu(
    nome: str,
):
    oferta = _oferta(nome)

    classificacao = ClassificadorProduto().classificar(oferta)

    assert classificacao.eh_nicho is True
    assert classificacao.categoria == "Processador"

    assert (
        SocialScoutScraper._oferta_fora_escopo_social(
            oferta,
            classificacao,
        )
        is False
    )


def test_social_scout_v7():
    assert SocialScoutScraper.VERSAO_PROCESSADOR == "10"
