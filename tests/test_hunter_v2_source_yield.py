from models.oferta import Oferta
from services.hunter_v2 import HunterV2


def oferta(
    nome,
    *,
    link,
    marketplace=None,
    id_anuncio=None,
):
    return Oferta(
        nome=nome,
        loja="Teste",
        preco=100.0,
        preco_antigo=None,
        link=link,
        imagem=None,
        marketplace=marketplace,
        id_anuncio=id_anuncio,
    )


class FonteA:
    def __init__(
        self,
        ofertas=None,
    ):
        self.ofertas = list(ofertas or [])

    def buscar_ofertas(
        self,
        limite=5,
    ):
        del limite

        return list(self.ofertas)


class FonteB(FonteA):
    pass


class FonteVazia(FonteA):
    pass


class FonteFalha:
    def buscar_ofertas(
        self,
        limite=5,
    ):
        del limite

        raise RuntimeError("falha controlada")


def mapa_fontes(
    resultado,
):
    return {fonte.fonte: fonte for fonte in resultado.fontes}


def test_fonte_totalmente_nova_tem_100_porcento_novidade():
    resultado = HunterV2(
        [
            FonteA(
                [
                    oferta(
                        "A",
                        link="https://loja/a",
                    ),
                    oferta(
                        "B",
                        link="https://loja/b",
                    ),
                ]
            )
        ]
    ).descobrir(5)

    fonte = resultado.fontes[0]

    assert fonte.quantidade_coletada == 2
    assert fonte.quantidade_novas == 2
    assert fonte.quantidade_duplicadas == 0
    assert fonte.taxa_novidade_percentual == 100.0


def test_segunda_fonte_mede_nova_e_duplicada():
    resultado = HunterV2(
        [
            FonteA(
                [
                    oferta(
                        "A",
                        link="https://loja/a",
                    )
                ]
            ),
            FonteB(
                [
                    oferta(
                        "A duplicada",
                        link="https://loja/a",
                    ),
                    oferta(
                        "B",
                        link="https://loja/b",
                    ),
                ]
            ),
        ]
    ).descobrir(5)

    fontes = mapa_fontes(resultado)

    assert fontes["FonteA"].quantidade_novas == 1

    assert fontes["FonteA"].quantidade_duplicadas == 0

    assert fontes["FonteB"].quantidade_coletada == 2

    assert fontes["FonteB"].quantidade_novas == 1

    assert fontes["FonteB"].quantidade_duplicadas == 1

    assert fontes["FonteB"].taxa_novidade_percentual == 50.0


def test_duplicata_na_mesma_fonte_entra_na_metrica():
    resultado = HunterV2(
        [
            FonteA(
                [
                    oferta(
                        "A",
                        link="https://loja/a",
                    ),
                    oferta(
                        "A novamente",
                        link="https://loja/a",
                    ),
                ]
            )
        ]
    ).descobrir(5)

    fonte = resultado.fontes[0]

    assert fonte.quantidade_coletada == 2
    assert fonte.quantidade_novas == 1
    assert fonte.quantidade_duplicadas == 1
    assert fonte.taxa_novidade_percentual == 50.0


def test_fonte_vazia_tem_taxa_zero():
    resultado = HunterV2(
        [
            FonteVazia(),
        ]
    ).descobrir(5)

    fonte = resultado.fontes[0]

    assert fonte.quantidade_coletada == 0
    assert fonte.quantidade_novas == 0
    assert fonte.quantidade_duplicadas == 0
    assert fonte.taxa_novidade_percentual == 0.0


def test_fonte_com_erro_tem_yield_zero():
    resultado = HunterV2(
        [
            FonteFalha(),
        ]
    ).descobrir(5)

    fonte = resultado.fontes[0]

    assert fonte.sucesso is False
    assert fonte.quantidade_coletada == 0
    assert fonte.quantidade_novas == 0
    assert fonte.quantidade_duplicadas == 0
    assert fonte.taxa_novidade_percentual == 0.0


def test_candidato_encontrado_por_duas_fontes_e_multifonte():
    resultado = HunterV2(
        [
            FonteA(
                [
                    oferta(
                        "A",
                        link="https://loja/a",
                    )
                ]
            ),
            FonteB(
                [
                    oferta(
                        "A novamente",
                        link="https://loja/a",
                    )
                ]
            ),
        ]
    ).descobrir(5)

    assert resultado.quantidade_candidatos_multifonte == 1

    assert resultado.candidatos[0].fontes == (
        "FonteA",
        "FonteB",
    )


def test_identidade_por_anuncio_entra_no_yield():
    resultado = HunterV2(
        [
            FonteA(
                [
                    oferta(
                        "A",
                        link="https://origem/a",
                        marketplace="mercado_livre",
                        id_anuncio="MLB123",
                    )
                ]
            ),
            FonteB(
                [
                    oferta(
                        "A outra URL",
                        link="https://origem/b",
                        marketplace="mercado_livre",
                        id_anuncio="MLB123",
                    )
                ]
            ),
        ]
    ).descobrir(5)

    fontes = mapa_fontes(resultado)

    assert fontes["FonteB"].quantidade_novas == 0

    assert fontes["FonteB"].quantidade_duplicadas == 1

    assert fontes["FonteB"].taxa_novidade_percentual == 0.0


def test_coletadas_sao_conservadas_entre_novas_e_duplicadas():
    resultado = HunterV2(
        [
            FonteA(
                [
                    oferta(
                        "A",
                        link="https://loja/a",
                    ),
                    oferta(
                        "B",
                        link="https://loja/b",
                    ),
                ]
            ),
            FonteB(
                [
                    oferta(
                        "A duplicada",
                        link="https://loja/a",
                    ),
                    oferta(
                        "C",
                        link="https://loja/c",
                    ),
                ]
            ),
        ]
    ).descobrir(5)

    for fonte in resultado.fontes:
        assert fonte.quantidade_novas + fonte.quantidade_duplicadas == fonte.quantidade_coletada
