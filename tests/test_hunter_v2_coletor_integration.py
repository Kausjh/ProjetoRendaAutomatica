from __future__ import annotations

from types import SimpleNamespace

from models.oferta import Oferta
from services.coletor_ofertas import ColetorOfertas


def criar_oferta(
    nome="Produto",
    *,
    link="https://loja/produto",
    marketplace=None,
    id_anuncio=None,
):
    return Oferta(
        nome=nome,
        loja="Loja Teste",
        preco=100.0,
        preco_antigo=150.0,
        link=link,
        imagem=None,
        marketplace=marketplace,
        id_anuncio=id_anuncio,
    )


class ScraperA:
    def __init__(
        self,
        ofertas=None,
        *,
        falhar=False,
    ):
        self.ofertas = list(ofertas or [])
        self.falhar = falhar
        self.limites = []
        self.confirmacoes = []

    def buscar_ofertas(
        self,
        limite=5,
    ):
        self.limites.append(limite)

        if self.falhar:
            raise RuntimeError("falha controlada")

        return list(self.ofertas)

    def confirmar_handoff(
        self,
        oferta,
        *,
        status,
        motivo,
    ):
        if not any(item is oferta for item in self.ofertas):
            return False

        self.confirmacoes.append(
            (
                oferta,
                status,
                motivo,
            )
        )

        return True


class ScraperB(ScraperA):
    pass


class ValidadorPassa:
    def __init__(
        self,
        eventos=None,
    ):
        self.eventos = eventos

    def validar(
        self,
        oferta,
        estatisticas=None,
    ):
        del estatisticas

        if self.eventos is not None:
            self.eventos.append("validar")

        oferta.valida = True
        oferta.motivos_validacao = []

        return oferta


class ValidadorRejeita:
    def validar(
        self,
        oferta,
        estatisticas=None,
    ):
        del estatisticas

        oferta.valida = False
        oferta.motivos_validacao = [
            "invalida_teste",
        ]

        return oferta


class ClassificadorNicho:
    def __init__(
        self,
        eventos=None,
    ):
        self.eventos = eventos

    def aplicar_classificacao(
        self,
        oferta,
    ):
        if self.eventos is not None:
            self.eventos.append("classificar")

        oferta.eh_nicho = True
        oferta.categoria = "perifericos"

        return SimpleNamespace(
            eh_nicho=True,
            categoria="perifericos",
            relevancia=90.0,
            motivo="nicho_teste",
        )


class ClassificadorFora:
    def aplicar_classificacao(
        self,
        oferta,
    ):
        return SimpleNamespace(
            eh_nicho=False,
            categoria="fora",
            relevancia=0.0,
            motivo="fora_do_nicho",
        )


class PipelineFake:
    def __init__(
        self,
        eventos,
    ):
        self.eventos = eventos

    def executar(
        self,
        oferta,
    ):
        self.eventos.append("pipeline")

        return oferta


def test_coletor_usa_hunter_v2_como_descoberta():
    produto = criar_oferta()

    scraper = ScraperA(
        [
            produto,
        ]
    )

    coletor = ColetorOfertas(
        scrapers=[
            scraper,
        ],
        classificador=(ClassificadorNicho()),
        validador=(ValidadorPassa()),
    )

    resultado = coletor.buscar_ofertas(limite_por_scraper=7)

    assert resultado == [
        produto,
    ]

    assert scraper.limites == [
        7,
    ]

    assert coletor.ultimo_resultado_hunter is not None

    assert coletor.ultimo_resultado_hunter.quantidade_bruta == 1


def test_duplicata_link_hunter_preserva_ack_legado():
    link = "https://loja/mesmo"

    primeira = criar_oferta(
        "Primeira",
        link=link,
    )

    segunda = criar_oferta(
        "Segunda",
        link=link,
    )

    scraper = ScraperA(
        [
            primeira,
            segunda,
        ]
    )

    coletor = ColetorOfertas(
        scrapers=[
            scraper,
        ],
        classificador=(ClassificadorNicho()),
        validador=(ValidadorPassa()),
    )

    resultado = coletor.buscar_ofertas(limite_por_scraper=5)

    assert resultado == [
        primeira,
    ]

    assert scraper.confirmacoes == [
        (
            segunda,
            "coletor_duplicada",
            "link_duplicado_no_coletor",
        ),
    ]


def test_duplicata_id_anuncio_recebe_ack_seguro():
    primeira = criar_oferta(
        "Primeira",
        link="https://loja/a",
        marketplace="mercado_livre",
        id_anuncio="MLB123",
    )

    segunda = criar_oferta(
        "Segunda",
        link="https://loja/b",
        marketplace="mercado_livre",
        id_anuncio="MLB123",
    )

    scraper = ScraperA(
        [
            primeira,
            segunda,
        ]
    )

    coletor = ColetorOfertas(
        scrapers=[
            scraper,
        ],
        classificador=(ClassificadorNicho()),
        validador=(ValidadorPassa()),
    )

    resultado = coletor.buscar_ofertas(limite_por_scraper=5)

    assert resultado == [
        primeira,
    ]

    assert scraper.confirmacoes == [
        (
            segunda,
            "coletor_duplicada",
            ("identidade_segura_" "duplicada_no_hunter"),
        ),
    ]


def test_invalida_continua_com_ack():
    produto = criar_oferta()

    scraper = ScraperA(
        [
            produto,
        ]
    )

    coletor = ColetorOfertas(
        scrapers=[
            scraper,
        ],
        classificador=(ClassificadorNicho()),
        validador=(ValidadorRejeita()),
    )

    assert coletor.buscar_ofertas(limite_por_scraper=5) == []

    assert scraper.confirmacoes == [
        (
            produto,
            "coletor_rejeitada_validacao",
            "invalida_teste",
        ),
    ]


def test_fora_nicho_continua_com_ack():
    produto = criar_oferta()

    scraper = ScraperA(
        [
            produto,
        ]
    )

    coletor = ColetorOfertas(
        scrapers=[
            scraper,
        ],
        classificador=(ClassificadorFora()),
        validador=(ValidadorPassa()),
    )

    assert coletor.buscar_ofertas(limite_por_scraper=5) == []

    assert scraper.confirmacoes == [
        (
            produto,
            "coletor_fora_nicho",
            "fora_do_nicho",
        ),
    ]


def test_ordem_validacao_classificacao_pipeline_preservada():
    eventos = []

    produto = criar_oferta()

    coletor = ColetorOfertas(
        scrapers=[
            ScraperA(
                [
                    produto,
                ]
            ),
        ],
        classificador=(ClassificadorNicho(eventos)),
        validador=(ValidadorPassa(eventos)),
        pipeline=PipelineFake(eventos),
    )

    resultado = coletor.buscar_ofertas(limite_por_scraper=5)

    assert resultado == [
        produto,
    ]

    assert eventos == [
        "validar",
        "classificar",
        "pipeline",
    ]


def test_orcamento_por_fonte_chega_ao_hunter():
    a = ScraperA()
    b = ScraperB()

    coletor = ColetorOfertas(
        scrapers=[
            a,
            b,
        ],
        classificador=(ClassificadorNicho()),
        validador=(ValidadorPassa()),
        limites_hunter_por_fonte={
            "ScraperB": 11,
        },
    )

    coletor.buscar_ofertas(limite_por_scraper=4)

    assert a.limites == [
        4,
    ]

    assert b.limites == [
        11,
    ]


def test_falha_de_fonte_nao_impede_demais():
    bom = criar_oferta("Produto bom")

    fonte_falha = ScraperA(falhar=True)

    fonte_boa = ScraperB(
        [
            bom,
        ]
    )

    coletor = ColetorOfertas(
        scrapers=[
            fonte_falha,
            fonte_boa,
        ],
        classificador=(ClassificadorNicho()),
        validador=(ValidadorPassa()),
    )

    resultado = coletor.buscar_ofertas(limite_por_scraper=5)

    assert resultado == [
        bom,
    ]

    assert coletor.ultimo_resultado_hunter.fontes_com_erro == ("ScraperA",)
