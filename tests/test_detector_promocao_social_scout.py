# 63.8738, -149.7525

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
        chat_id="-100123",
        message_id=10,
        chat_titulo="Grupo Teste",
        texto=texto,
        links=links,
    )


def test_detecta_oferta_produto_com_cupom():
    mensagem = criar_mensagem(
        texto=(
            "Mouse Gamer Modelo X\n"
            "De: R$ 399,99\n"
            "Por: R$ 251,74 (37% OFF)\n"
            "R$ 206,43 - Aplique o cupom TESTE18 de 18% OFF"
        ),
        links=("https://meli.la/teste123",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "oferta_produto"
    assert resultado.utilizavel is True
    assert resultado.titulo == "Mouse Gamer Modelo X"

    assert resultado.marketplace == "mercado_livre"

    assert resultado.preco_original == 399.99
    assert resultado.preco_oferta == 251.74
    assert resultado.preco_final == 206.43

    assert resultado.desconto_anunciado_percentual == 37.0
    assert resultado.desconto_cupom_percentual == 18.0

    assert resultado.codigo_cupom == "TESTE18"
    assert resultado.cupons == ("TESTE18",)


def test_detecta_campanha_de_cupons_gerais():
    mensagem = criar_mensagem(
        texto=(
            "Cupons no APP Magalu\n"
            "R$ 150 OFF em R$ 1000: TESTE150\n"
            "R$ 30 OFF em R$ 250: TESTE30"
        ),
        links=("https://divulgadormagalu.com/teste123",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "cupom_geral"
    assert resultado.utilizavel is True

    assert resultado.marketplace == "magalu"

    assert resultado.cupons == (
        "TESTE150",
        "TESTE30",
    )


def test_ignora_mensagem_vazia():
    resultado = DetectorPromocaoSocialScout.detectar(criar_mensagem(""))

    assert resultado.classificacao == "ignorar"
    assert resultado.utilizavel is False


def test_ignora_preco_sem_link():
    resultado = DetectorPromocaoSocialScout.detectar(
        criar_mensagem("Teclado Gamer\n" "Por: R$ 199,90")
    )

    assert resultado.classificacao == "ignorar"


def test_ignora_link_sem_preco():
    resultado = DetectorPromocaoSocialScout.detectar(
        criar_mensagem(
            "Teclado Gamer em promocao",
            links=("https://meli.la/teste456",),
        )
    )

    assert resultado.classificacao == "ignorar"
    assert resultado.marketplace == "mercado_livre"


def test_preco_final_sem_cupom_e_o_preco_da_oferta():
    resultado = DetectorPromocaoSocialScout.detectar(
        criar_mensagem(
            "SSD NVMe Modelo Y\n" "Por: R$ 349,90",
            links=("https://www.amazon.com.br/" "produto-teste",),
        )
    )

    assert resultado.classificacao == "oferta_produto"
    assert resultado.marketplace == "amazon"

    assert resultado.preco_oferta == 349.90
    assert resultado.preco_final == 349.90

    assert resultado.codigo_cupom is None


def test_detecta_marketplace_pelo_dominio():
    resultado = DetectorPromocaoSocialScout.detectar(
        criar_mensagem(
            "Headset Gamer Modelo Z\n" "Por: R$ 129,90",
            links=("https://www.kabum.com.br/" "produto/123/teste",),
        )
    )

    assert resultado.classificacao == "oferta_produto"
    assert resultado.marketplace == "kabum"


def test_remove_cupom_geral_duplicado():
    resultado = DetectorPromocaoSocialScout.detectar(
        criar_mensagem(
            "Cupons no APP\n" "R$ 50 OFF em R$ 500: TESTE50\n" "R$ 50 OFF em R$ 500: TESTE50",
            links=("https://divulgadormagalu.com/" "teste456",),
        )
    )

    assert resultado.classificacao == "cupom_geral"
    assert resultado.cupons == ("TESTE50",)


def test_detecta_preco_generico_inteiro_com_cupom():
    mensagem = criar_mensagem(
        texto="""Fonte Gamer Teste 750W
R$ 258 Cupom: TESTE10
""",
        links=("https://meli.la/teste-generico",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "oferta_produto"
    assert resultado.utilizavel is True
    assert resultado.preco_oferta == 258.0
    assert resultado.preco_final == 258.0
    assert resultado.codigo_cupom == "TESTE10"


def test_detecta_preco_generico_com_milhar_sem_centavos():
    mensagem = criar_mensagem(
        texto="""Eletronico Teste
R$ 3.911 em ate 12x
""",
        links=("https://meli.la/teste-milhar",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "oferta_produto"
    assert resultado.preco_final == 3911.0


def test_detecta_preco_generico_decimal():
    mensagem = criar_mensagem(
        texto="""Cooler Gamer Teste
R$ 133,32
""",
        links=("https://meli.la/teste-decimal",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "oferta_produto"
    assert resultado.preco_final == 133.32


def test_campanha_com_emoji_e_novos_cupons_nao_vira_produto():
    mensagem = criar_mensagem(
        texto="""?? NOVOS CUPONS MERCADO LIVRE ??
20% OFF: Compra minima de R$ 89
""",
        links=("https://meli.la/teste-cupom",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "cupom_geral"


def test_campanha_com_emoji_e_cupom_no_titulo():
    mensagem = criar_mensagem(
        texto="""?? CUPOM SHOPEE LIBERADO ??
R$ 50 OFF em R$ 249
""",
        links=("https://shopee.com.br/teste",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "cupom_geral"


def test_produto_com_rodape_resgate_cupons_continua_produto():
    mensagem = criar_mensagem(
        texto="""Mouse Gamer Teste
De: R$ 299,90
Por: R$ 199,90
Resgate seus cupons aqui:
https://meli.la/teste-cupons
""",
        links=(
            "https://meli.la/teste-produto",
            "https://meli.la/teste-cupons",
        ),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "oferta_produto"
    assert resultado.preco_final == 199.90


def test_apenas_de_sem_preco_de_oferta_continua_ignorado():
    mensagem = criar_mensagem(
        texto="""Produto Teste
De: R$ 499,90
""",
        links=("https://meli.la/teste-apenas-de",),
    )

    resultado = DetectorPromocaoSocialScout.detectar(mensagem)

    assert resultado.classificacao == "ignorar"
