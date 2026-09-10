import time

import pytest

from models.oferta import Oferta
from services.hunter_v2 import HunterV2


def oferta(
    nome,
    *,
    link,
    marketplace=None,
    id_anuncio=None,
    id_produto=None,
    valida=True,
    eh_nicho=False,
):
    return Oferta(
        nome=nome,
        loja="Loja",
        preco=100.0,
        preco_antigo=None,
        link=link,
        imagem=None,
        marketplace=marketplace,
        id_anuncio=id_anuncio,
        id_produto=id_produto,
        valida=valida,
        eh_nicho=eh_nicho,
    )


class FonteA:
    def __init__(
        self,
        ofertas=None,
    ):
        self.ofertas = list(ofertas or [])
        self.limites = []

    def buscar_ofertas(
        self,
        limite=5,
    ):
        self.limites.append(limite)

        return list(self.ofertas)


class FonteB(FonteA):
    pass


class FonteLenta(FonteA):
    def buscar_ofertas(
        self,
        limite=5,
    ):
        self.limites.append(limite)

        time.sleep(0.05)

        return list(self.ofertas)


class FonteFalha:
    def buscar_ofertas(
        self,
        limite=5,
    ):
        del limite

        raise RuntimeError("falha proposital")


class FonteRetornoInvalido:
    def buscar_ofertas(
        self,
        limite=5,
    ):
        del limite

        return "nao_e_lista"


def test_sem_fontes_retorna_resultado_vazio():
    resultado = HunterV2([]).descobrir(5)

    assert resultado.quantidade_bruta == 0
    assert resultado.quantidade_unica == 0
    assert resultado.duplicadas_confirmadas == 0
    assert resultado.candidatos == ()
    assert resultado.fontes == ()


def test_limite_base_precisa_ser_positivo():
    with pytest.raises(
        ValueError,
        match="Limite base",
    ):
        HunterV2([]).descobrir(0)


def test_aplica_mesmo_limite_base_a_todas_as_fontes():
    a = FonteA()
    b = FonteB()

    resultado = HunterV2(
        [
            a,
            b,
        ]
    ).descobrir(7)

    assert a.limites == [7]
    assert b.limites == [7]

    assert [item.limite_solicitado for item in resultado.fontes] == [
        7,
        7,
    ]


def test_permite_orcamento_especifico_por_fonte():
    a = FonteA()
    b = FonteB()

    resultado = HunterV2(
        [
            a,
            b,
        ]
    ).descobrir(
        5,
        limites_por_fonte={
            "FonteB": 12,
        },
    )

    assert a.limites == [5]
    assert b.limites == [12]

    assert {item.fonte: item.limite_solicitado for item in resultado.fontes} == {
        "FonteA": 5,
        "FonteB": 12,
    }


def test_limite_especifico_invalido_e_rejeitado():
    with pytest.raises(
        ValueError,
        match="FonteA",
    ):
        HunterV2(
            [
                FonteA(),
            ]
        ).descobrir(
            5,
            limites_por_fonte={
                "FonteA": 0,
            },
        )


def test_falha_de_uma_fonte_nao_perde_as_demais():
    boa = FonteA(
        [
            oferta(
                "Produto bom",
                link="https://loja/produto-1",
            )
        ]
    )

    resultado = HunterV2(
        [
            FonteFalha(),
            boa,
        ]
    ).descobrir(5)

    assert resultado.quantidade_bruta == 1
    assert resultado.quantidade_unica == 1

    assert resultado.ofertas[0].nome == "Produto bom"

    assert resultado.fontes_com_erro == ("FonteFalha",)

    falha = resultado.fontes[0]

    assert falha.quantidade_coletada == 0
    assert "RuntimeError" in falha.erro


def test_retorno_invalido_da_fonte_e_isolado():
    resultado = HunterV2(
        [
            FonteRetornoInvalido(),
            FonteA(),
        ]
    ).descobrir(5)

    assert resultado.fontes_com_erro == ("FonteRetornoInvalido",)

    assert "TypeError" in resultado.fontes[0].erro


def test_preserva_ordem_configurada_das_fontes():
    lenta = FonteLenta(
        [
            oferta(
                "Primeiro",
                link="https://loja/primeiro",
            )
        ]
    )

    rapida = FonteB(
        [
            oferta(
                "Segundo",
                link="https://loja/segundo",
            )
        ]
    )

    resultado = HunterV2(
        [
            lenta,
            rapida,
        ]
    ).descobrir(5)

    assert [item.nome for item in resultado.ofertas] == [
        "Primeiro",
        "Segundo",
    ]


def test_link_exatamente_igual_e_deduplicado_e_fontes_sao_preservadas():
    link = "https://loja/produto"

    resultado = HunterV2(
        [
            FonteA(
                [
                    oferta(
                        "Produto A",
                        link=link,
                    )
                ]
            ),
            FonteB(
                [
                    oferta(
                        "Produto B",
                        link=link,
                    )
                ]
            ),
        ]
    ).descobrir(5)

    assert resultado.quantidade_bruta == 2
    assert resultado.quantidade_unica == 1
    assert resultado.duplicadas_confirmadas == 1

    candidato = resultado.candidatos[0]

    assert candidato.oferta.nome == "Produto A"

    assert candidato.fontes == (
        "FonteA",
        "FonteB",
    )


def test_mesmo_id_anuncio_marketplace_e_identidade_segura():
    resultado = HunterV2(
        [
            FonteA(
                [
                    oferta(
                        "Produto A",
                        link="https://origem/a",
                        marketplace="mercado_livre",
                        id_anuncio="MLB123",
                    )
                ]
            ),
            FonteB(
                [
                    oferta(
                        "Produto B",
                        link="https://origem/b",
                        marketplace="mercado_livre",
                        id_anuncio="MLB123",
                    )
                ]
            ),
        ]
    ).descobrir(5)

    assert resultado.quantidade_bruta == 2
    assert resultado.quantidade_unica == 1
    assert resultado.duplicadas_confirmadas == 1


def test_id_produto_sozinho_nao_e_usado_para_deduplicar():
    resultado = HunterV2(
        [
            FonteA(
                [
                    oferta(
                        "Oferta vendedor A",
                        link="https://loja/a",
                        marketplace="marketplace",
                        id_produto="SKU123",
                    )
                ]
            ),
            FonteB(
                [
                    oferta(
                        "Oferta vendedor B",
                        link="https://loja/b",
                        marketplace="marketplace",
                        id_produto="SKU123",
                    )
                ]
            ),
        ]
    ).descobrir(5)

    assert resultado.quantidade_bruta == 2
    assert resultado.quantidade_unica == 2
    assert resultado.duplicadas_confirmadas == 0


def test_hunter_nao_filtra_invalidas_nem_fora_do_nicho():
    invalida = oferta(
        "Invalida",
        link="https://loja/invalida",
        valida=False,
        eh_nicho=False,
    )

    fora_nicho = oferta(
        "Fora do nicho",
        link="https://loja/fora",
        valida=True,
        eh_nicho=False,
    )

    resultado = HunterV2(
        [
            FonteA(
                [
                    invalida,
                    fora_nicho,
                ]
            )
        ]
    ).descobrir(5)

    assert resultado.ofertas == [
        invalida,
        fora_nicho,
    ]

    assert resultado.ofertas[0].valida is False

    assert resultado.ofertas[1].eh_nicho is False
