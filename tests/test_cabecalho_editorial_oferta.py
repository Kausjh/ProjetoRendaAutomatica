import pytest

from formatters.oferta_formatter import OfertaFormatter
from models.oferta import Oferta


def criar_oferta(
    nota_tecnica: float,
    nota_historica: float = 0.0,
) -> Oferta:
    oferta = Oferta(
        nome="Produto de teste",
        loja="Shopee",
        preco=100.0,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace="shopee",
    )

    oferta.nota_tecnica = nota_tecnica
    oferta.nota_historica = nota_historica

    return oferta


@pytest.mark.parametrize(
    ("nota", "esperado"),
    [
        (80.0, "\U0001f525 OFERTA IMPERD\u00cdVEL"),
        (70.0, "\U0001f525 OFERTA IMPERD\u00cdVEL"),
        (69.9, "\U0001f7e2 MUITO BOA OFERTA"),
        (60.0, "\U0001f7e2 MUITO BOA OFERTA"),
        (59.9, "\U0001f7e2 BOA OFERTA"),
        (50.0, "\U0001f7e2 BOA OFERTA"),
        (49.9, "\U0001f7e1 OFERTA INTERESSANTE"),
        (45.0, "\U0001f7e1 OFERTA INTERESSANTE"),
        (44.9, "\u26aa OFERTA COMUM"),
        (31.0, "\u26aa OFERTA COMUM"),
    ],
)
def test_cabecalho_reflete_nota_do_comprador(
    nota: float,
    esperado: str,
) -> None:
    oferta = criar_oferta(nota)

    assert (
        OfertaFormatter._formatar_cabecalho(
            oferta,
            None,
        )
        == esperado
    )


def test_nota_31_nao_pode_ser_chamada_de_imperdivel():
    oferta = criar_oferta(31.0)

    mensagem = OfertaFormatter.formatar(
        oferta=oferta,
        resultado_historico=None,
    )

    assert "\u26aa OFERTA COMUM" in mensagem
    assert "\U0001f525 OFERTA IMPERD\u00cdVEL" not in mensagem
    assert "31/80" in mensagem
    assert "Oferta comum" in mensagem


def test_nota_48_tem_cabecalho_e_descricao_coerentes():
    oferta = criar_oferta(48.0)

    mensagem = OfertaFormatter.formatar(
        oferta=oferta,
        resultado_historico=None,
    )

    assert "\U0001f7e1 OFERTA INTERESSANTE" in mensagem
    assert "48/80" in mensagem
    assert "Oferta interessante" in mensagem


def test_anomalia_continua_tendo_prioridade():
    oferta = criar_oferta(75.0)
    oferta.tipo_oportunidade = "possivel_preco_bugado"

    assert (
        OfertaFormatter._formatar_cabecalho(
            oferta,
            None,
        )
        == "\U0001f6a8 POSS\u00cdVEL PRE\u00c7O BUGADO"
    )
