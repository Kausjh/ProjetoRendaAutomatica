from models.mensagem_social_scout import MensagemSocialScout
from services.scout.detector_promocao_social_scout import (
    DetectorPromocaoSocialScout,
)


def criar_mensagem(
    texto: str,
    links: tuple[str, ...] = (),
) -> MensagemSocialScout:
    return MensagemSocialScout(
        fonte="telegram",
        chat_id="-1001",
        message_id=1,
        chat_titulo="Grupo Teste",
        texto=texto,
        links=links,
    )


def test_detecta_oferta_real_canario_promos():
    mensagem = criar_mensagem(
        texto="""T?nis Masculino Streettalk Adidas

?? De: R$ 399,99
? Por: R$ 251,74 (37% OFF)

?? R$ 206,43 - Aplique o cupom OFERTASEMPRE de 18% OFF

?? https://meli.la/1mKjw4r
""",
        links=("https://meli.la/1mKjw4r",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "oferta_produto"
    assert resultado.utilizavel is True

    assert resultado.titulo == "T?nis Masculino Streettalk Adidas"

    assert resultado.marketplace == "mercado_livre"

    assert resultado.preco_original == 399.99
    assert resultado.preco_oferta == 251.74
    assert resultado.preco_final == 206.43

    assert resultado.desconto_anunciado_percentual == 37.0

    assert resultado.desconto_cupom_percentual == 18.0

    assert resultado.codigo_cupom == "OFERTASEMPRE"


def test_detecta_campanha_real_magalu():
    mensagem = criar_mensagem(
        texto="""Cupons no APP Magalu

R$ 150 OFF em R$ 1000: ESQUENTA150
R$ 30 OFF em R$ 250: TOMA30

Resgate aqui:
https://divulgadormagalu.com/4jy67l3

(AN?NCIO)
""",
        links=("https://divulgadormagalu.com/4jy67l3",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "cupom_geral"
    assert resultado.utilizavel is True
    assert resultado.marketplace == "magalu"

    assert resultado.cupons == (
        "ESQUENTA150",
        "TOMA30",
    )


def test_ignora_conversa_comum():
    mensagem = criar_mensagem("Algu?m sabe se esse teclado ? bom?")

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "ignorar"
    assert resultado.utilizavel is False


def test_link_sem_preco_nao_vira_oferta():
    mensagem = criar_mensagem(
        "Olha esse produto aqui",
        links=("https://www.kabum.com.br/produto/123",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "ignorar"


def test_detecta_kabum_pelo_link():
    mensagem = criar_mensagem(
        texto="""Mouse Gamer
Por: R$ 129,90
""",
        links=("https://www.kabum.com.br/produto/123",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.marketplace == "kabum"
    assert resultado.preco_final == 129.90


def test_preco_final_sem_cupom_usa_preco_oferta():
    mensagem = criar_mensagem(
        texto="""SSD 1TB
De: R$ 499,90
Por: R$ 299,90 (40% OFF)
""",
        links=("https://www.kabum.com.br/produto/456",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.preco_original == 499.90
    assert resultado.preco_oferta == 299.90
    assert resultado.preco_final == 299.90


def test_cupons_gerais_sao_deduplicados():
    mensagem = criar_mensagem(texto="""Cupons no APP

R$ 50 OFF em R$ 500: CUPOM50
R$ 50 OFF em R$ 500: CUPOM50
""")

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "cupom_geral"

    assert resultado.cupons == ("CUPOM50",)
