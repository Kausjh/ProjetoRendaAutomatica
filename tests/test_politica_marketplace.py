from datetime import datetime
from types import SimpleNamespace

from models.oferta import Oferta
from scrapers.aliexpress_scraper import AliExpressScraper
from scrapers.mercado_livre_scraper import MercadoLivreScraper
from scrapers.shopee_scraper import ShopeeScraper
from services.classificador_produto import ClassificadorProduto
from services.politica_marketplace import PoliticaMarketplace


def _oferta(
    nome: str,
    *,
    marketplace: str = "aliexpress",
    loja: str = "AliExpress",
    categoria: str | None = None,
    relevancia: float = 90.0,
) -> Oferta:
    oferta = Oferta(
        nome=nome,
        loja=loja,
        preco=100.0,
        preco_antigo=None,
        link="https://example.com/item",
        imagem=None,
        marketplace=marketplace,
    )
    oferta.eh_nicho = True
    oferta.categoria = categoria
    oferta.relevancia_nicho = relevancia
    return oferta


def test_mesh_strainer_nao_vira_rede() -> None:
    resultado = ClassificadorProduto().classificar(
        _oferta(
            "Cocktail Fine Strainer Stainless Steel Conical Mesh Strainer Professional Bar Tool",
            marketplace="teste",
            loja="Teste",
        )
    )
    assert resultado.categoria != "Rede"


def test_wifi_mesh_continua_rede() -> None:
    resultado = ClassificadorProduto().classificar(
        _oferta(
            "Roteador WiFi Mesh WiFi 6 AX3000",
            marketplace="teste",
            loja="Teste",
        )
    )
    assert resultado.eh_nicho is True
    assert resultado.categoria == "Rede"


def test_aliexpress_bloqueia_mini_pc_generico() -> None:
    resultado = PoliticaMarketplace.analisar(
        _oferta(
            "Ultra Fast Mini PC Intel Core i9 10980HK 16GB DDR4 NVMe SSD Triple 4K Office Home",
            categoria="Computador e Mini PC",
            relevancia=100.0,
        )
    )
    assert resultado.permitido is False


def test_aliexpress_aceita_mouse_com_sinal_de_qualidade() -> None:
    resultado = PoliticaMarketplace.analisar(
        _oferta(
            "Attack Shark X11 Wireless Gaming Mouse PixArt PAW3395",
            categoria="Mouse e mousepad",
        )
    )
    assert resultado.permitido is True


def test_aliexpress_rejeita_mouse_generico() -> None:
    resultado = PoliticaMarketplace.analisar(
        _oferta(
            "Generic Wireless RGB Gaming Mouse",
            categoria="Mouse e mousepad",
        )
    )
    assert resultado.permitido is False


def test_aliexpress_usa_somente_feeds_tech_padrao() -> None:
    assert AliExpressScraper.FEEDS_PADRAO == ("47213", "47215", "47217", "47247")


def test_secundario_primeiro_registro_nao_publica() -> None:
    historico = SimpleNamespace(
        primeiro_registro=True,
        quantidade_registros=1,
        preco_caiu=False,
        variacao_percentual=0.0,
        menor_preco_historico=True,
    )
    assert PoliticaMarketplace.secundaria_tem_promocao_forte(95.0, historico) is False


def test_secundario_exige_promocao_forte_real() -> None:
    historico = SimpleNamespace(
        primeiro_registro=False,
        quantidade_registros=4,
        preco_caiu=True,
        variacao_percentual=-18.0,
        menor_preco_historico=True,
    )
    assert PoliticaMarketplace.secundaria_tem_promocao_forte(82.0, historico) is True


def test_secundario_com_queda_fraca_nao_publica() -> None:
    historico = SimpleNamespace(
        primeiro_registro=False,
        quantidade_registros=5,
        preco_caiu=True,
        variacao_percentual=-8.0,
        menor_preco_historico=True,
    )
    assert PoliticaMarketplace.secundaria_tem_promocao_forte(90.0, historico) is False


def test_mercado_livre_busca_um_secundario_por_ciclo() -> None:
    termos = MercadoLivreScraper._obter_termos_padrao_rotativos(datetime(2026, 9, 5, 18, 0))
    termos_secundarios = {
        termo
        for categoria in MercadoLivreScraper.CATEGORIAS_SECUNDARIAS
        for termo in MercadoLivreScraper.TERMOS_POR_CATEGORIA[categoria]
    }
    encontrados = [termo for termo in termos if termo in termos_secundarios]
    assert len(encontrados) == 1


def test_shopee_busca_um_secundario_por_ciclo() -> None:
    termos = ShopeeScraper._obter_termos_padrao_rotativos(datetime(2026, 9, 5, 18, 0))
    encontrados = [termo for termo in termos if termo in ShopeeScraper.TERMOS_SECUNDARIOS]
    assert len(encontrados) == 1
