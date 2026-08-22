from datetime import datetime

from scrapers.mercado_livre_scraper import MercadoLivreScraper


def test_todas_as_categorias_tem_cobertura_ampla():
    assert len(MercadoLivreScraper.TERMOS_POR_CATEGORIA) >= 35
    assert all(len(termos) >= 5 for termos in MercadoLivreScraper.TERMOS_POR_CATEGORIA.values())


def test_teclado_nao_fica_preso_a_redragon():
    termos = MercadoLivreScraper.TERMOS_POR_CATEGORIA["Teclados"]
    assert "Teclado Redragon" in termos
    assert "Teclado mecânico" in termos
    assert "Teclado Logitech" in termos
    assert "Teclado Keychron" in termos
    assert len(termos) >= 10


def test_toda_categoria_participa_de_cada_ciclo():
    momento = datetime(2026, 8, 22, 9, 0)
    selecionados = MercadoLivreScraper._obter_termos_padrao_rotativos(momento)
    quantidade_minima = len(MercadoLivreScraper.TERMOS_POR_CATEGORIA)
    assert len(selecionados) >= quantidade_minima


def test_rotacao_muda_consultas_entre_janelas():
    primeira = MercadoLivreScraper._obter_termos_padrao_rotativos(datetime(2026, 8, 22, 9, 0))
    segunda = MercadoLivreScraper._obter_termos_padrao_rotativos(datetime(2026, 8, 22, 9, 30))
    assert primeira != segunda
