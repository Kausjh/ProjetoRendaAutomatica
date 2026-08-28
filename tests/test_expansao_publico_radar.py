from models.oferta import Oferta
from scrapers.kabum_scraper import KabumScraper
from scrapers.mercado_livre_scraper import MercadoLivreScraper
from scrapers.shopee_scraper import ShopeeScraper
from services.classificador_produto import ClassificadorProduto
from services.curadoria_publicacao import CuradoriaPublicacao


def criar_oferta(
    nome: str,
    preco: float = 49.90,
) -> Oferta:
    return Oferta(
        nome=nome,
        loja="Loja Teste",
        preco=preco,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
    )


def classificar(nome: str, preco: float = 49.90):
    oferta = criar_oferta(
        nome=nome,
        preco=preco,
    )

    resultado = ClassificadorProduto().aplicar_classificacao(oferta)

    return oferta, resultado


def test_classifica_creatina_como_suplemento() -> None:
    _, resultado = classificar("Creatina Monohidratada 300g")

    assert resultado.eh_nicho is True
    assert resultado.categoria == "Suplementos"


def test_whey_sabor_chocolate_continua_sendo_suplemento() -> None:
    _, resultado = classificar("Whey Protein Concentrado 900g Sabor Chocolate")

    assert resultado.eh_nicho is True
    assert resultado.categoria == "Suplementos"


def test_classifica_energetico() -> None:
    _, resultado = classificar("Monster Energy 473ml Original")

    assert resultado.eh_nicho is True
    assert resultado.categoria == "Energ\u00e9ticos"


def test_classifica_cafe() -> None:
    _, resultado = classificar("Cafe em Graos Especial 500g")

    assert resultado.eh_nicho is True
    assert resultado.categoria == "Caf\u00e9"


def test_classifica_chocolate() -> None:
    _, resultado = classificar("Chocolate Lacta Ao Leite 90g")

    assert resultado.eh_nicho is True
    assert resultado.categoria == "Chocolate e snacks"


def test_curadoria_bloqueia_coqueteleira_disfarcada() -> None:
    oferta, resultado = classificar(
        "Coqueteleira Shaker Para Creatina 600ml",
        preco=19.90,
    )

    assert resultado.categoria == "Suplementos"

    curadoria = CuradoriaPublicacao().analisar(oferta)

    assert curadoria.publicavel is False


def test_curadoria_bloqueia_porta_capsulas() -> None:
    oferta, resultado = classificar(
        "Porta Capsulas Nespresso Para Cafe",
        preco=39.90,
    )

    assert resultado.categoria == "Caf\u00e9"

    curadoria = CuradoriaPublicacao().analisar(oferta)

    assert curadoria.publicavel is False


def test_curadoria_bloqueia_validade_curta() -> None:
    oferta, resultado = classificar(
        "Creatina 300g Validade Curta",
        preco=29.90,
    )

    assert resultado.categoria == "Suplementos"

    curadoria = CuradoriaPublicacao().analisar(oferta)

    assert curadoria.publicavel is False


def test_kit_de_energetico_e_normal() -> None:
    oferta, resultado = classificar(
        "Kit 12 Monster Energy 473ml",
        preco=89.90,
    )

    assert resultado.categoria == "Energ\u00e9ticos"

    curadoria = CuradoriaPublicacao().analisar(oferta)

    assert curadoria.publicavel is True
    assert not any("Kit/combo/lote" in motivo for motivo in curadoria.motivos)


def test_fontes_possuem_cobertura_expandida() -> None:
    assert "Suplementos" in (MercadoLivreScraper.TERMOS_POR_CATEGORIA)

    assert "Creatina monohidratada 300g" in (ShopeeScraper.TERMOS_PADRAO)

    assert "Power bank" in (KabumScraper.TERMOS_PADRAO)


def test_reconhece_caixa_lacta_sem_palavra_chocolate() -> None:
    _, resultado = classificar(
        "Caixa de Variedades Lacta Favoritos 250g",
        preco=18.00,
    )

    assert resultado.eh_nicho is True
    assert resultado.categoria == "Chocolate e snacks"


def test_bloqueia_porta_lata_monster() -> None:
    oferta, resultado = classificar(
        "Porta Lata Monster Energy 473ml Garra Monstro Decorativa Geek",
        preco=41.87,
    )

    assert resultado.eh_nicho is True
    assert resultado.categoria == "Energ\u00e9ticos"

    curadoria = CuradoriaPublicacao().analisar(oferta)

    assert curadoria.publicavel is False
    assert any(
        "acessorio" in bloqueio.lower() or "acess\u00f3rio" in bloqueio.lower()
        for bloqueio in curadoria.bloqueios
    )
