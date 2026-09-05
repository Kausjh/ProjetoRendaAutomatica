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


def test_nucleo_participa_de_cada_ciclo_e_secundario_rotaciona():
    momento = datetime(
        2026,
        8,
        22,
        9,
        0,
    )

    selecionados = MercadoLivreScraper._obter_termos_padrao_rotativos(momento)

    for categoria in MercadoLivreScraper.CATEGORIAS_PRIORITARIAS:
        termos = MercadoLivreScraper.TERMOS_POR_CATEGORIA[categoria]

        assert any(termo in selecionados for termo in termos)

    termos_secundarios = {
        termo
        for categoria in MercadoLivreScraper.CATEGORIAS_SECUNDARIAS
        for termo in MercadoLivreScraper.TERMOS_POR_CATEGORIA[categoria]
    }

    secundarios_selecionados = [termo for termo in selecionados if termo in termos_secundarios]

    assert len(secundarios_selecionados) == 1


def test_rotacao_muda_consultas_entre_janelas():
    primeira = MercadoLivreScraper._obter_termos_padrao_rotativos(datetime(2026, 8, 22, 9, 0))
    segunda = MercadoLivreScraper._obter_termos_padrao_rotativos(datetime(2026, 8, 22, 9, 30))
    assert primeira != segunda
