import json

from services.validador_preco_aliexpress import (
    ValidadorPrecoAliExpress,
)

PRODUTO_ID = "1005012134809286"

URL = "https://pt.aliexpress.com/" f"item/{PRODUTO_ID}.html"


def html_produto(
    preco="38.04",
    moeda="BRL",
):
    dados = {
        "@context": "https://schema.org",
        "@type": "Product",
        "offers": {
            "@type": "Offer",
            "url": URL,
            "priceCurrency": moeda,
            "price": preco,
        },
    }

    return '<script type="application/ld+json">' + json.dumps(dados) + "</script>"


def pdp(
    *,
    sale="38.04",
    normal="40.04",
    atmosfera=None,
    supplementary=None,
    new_user=True,
):
    banner = {}

    if atmosfera is not None:
        banner["atmosphereCode"] = atmosfera

    target_banner = {}

    if supplementary is not None:
        target_banner["supplementaryText"] = supplementary

    if target_banner:
        banner["targetSkuBanner"] = target_banner

    dados = {
        "data": {
            "result": {
                "PRICE": {
                    "productId": int(PRODUTO_ID),
                    "selectedSkuId": (12000057594601401),
                    "targetSkuPriceInfo": {
                        "originalPrice": {
                            "currency": "BRL",
                            "value": normal,
                        },
                        "salePriceString": (
                            "R$"
                            + sale.replace(
                                ".",
                                ",",
                            )
                        ),
                    },
                },
                "PRICE_BANNER": banner,
                ("PERSONAL_INFORMATION_" "SECURITY"): {"features": {"newUser": (new_user)}},
            }
        }
    }

    return json.dumps(dados)


def test_json_ld_continua_funcionando_sem_pdp():
    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=URL,
        html=html_produto(),
    )

    assert resultado.valido is True
    assert resultado.preco == 38.04
    assert resultado.moeda == "BRL"


def test_exigir_pdp_rejeita_quando_nao_capturada():
    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=URL,
        html=html_produto(),
        exigir_pdp=True,
    )

    assert resultado.valido is False


def test_promocao_comum_usa_preco_promocional():
    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=URL,
        html=html_produto(preco="9.51"),
        pdp_texto=pdp(
            sale="9.51",
            normal="10.01",
            atmosfera=("girdle_aplus_big_sale"),
            new_user=True,
        ),
        exigir_pdp=True,
    )

    assert resultado.valido is True

    assert resultado.preco == 9.51

    assert resultado.preco_normal == 10.01

    assert resultado.preco_promocional == 9.51

    assert resultado.promocao_novo_usuario is False

    assert resultado.preco_novo_usuario is None


def test_novo_usuario_preserva_dois_precos():
    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=URL,
        html=html_produto(preco="25.04"),
        pdp_texto=pdp(
            sale="25.04",
            normal="40.04",
            atmosfera=("new_user_" "platform_allowance_atm"),
            new_user=True,
        ),
        exigir_pdp=True,
    )

    assert resultado.valido is True

    assert resultado.preco == 40.04

    assert resultado.preco_normal == 40.04

    assert resultado.preco_promocional == 25.04

    assert resultado.preco_novo_usuario == 25.04

    assert resultado.promocao_novo_usuario is True

    assert resultado.moeda_normal == "BRL"

    assert resultado.moeda_promocional == "BRL"

    assert resultado.moeda_novo_usuario == "BRL"


def test_flag_new_user_sozinha_nao_define_promocao():
    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=URL,
        html=html_produto(preco="1074.99"),
        pdp_texto=pdp(
            sale="1074.99",
            normal="2443.16",
            atmosfera=None,
            new_user=True,
        ),
        exigir_pdp=True,
    )

    assert resultado.valido is True

    assert resultado.promocao_novo_usuario is False

    assert resultado.preco == 1074.99

    assert resultado.preco_normal == 2443.16


def test_texto_explicito_novo_usuario_define_promocao():
    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=URL,
        html=html_produto(preco="25.04"),
        pdp_texto=pdp(
            sale="25.04",
            normal="40.04",
            supplementary=("Novo usu?rio - " "R$15,00 OFF"),
        ),
        exigir_pdp=True,
    )

    assert resultado.valido is True

    assert resultado.promocao_novo_usuario is True


def test_rejeita_divergencia_entre_jsonld_e_sku():
    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=URL,
        html=html_produto(preco="25.04"),
        pdp_texto=pdp(
            sale="30.00",
            normal="40.04",
        ),
        exigir_pdp=True,
    )

    assert resultado.valido is False

    assert "diverge" in resultado.motivo


def test_rejeita_moeda_jsonld_estrangeira():
    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=URL,
        html=html_produto(
            preco="8.96",
            moeda="CNY",
        ),
    )

    assert resultado.valido is False


def test_pdp_com_prefixo_anti_json_e_aceita():
    bruto = ")]}',\n" + pdp(
        sale="25.04",
        normal="40.04",
        atmosfera=("new_user_" "platform_allowance_atm"),
    )

    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=URL,
        html=html_produto(preco="25.04"),
        pdp_texto=bruto,
        exigir_pdp=True,
    )

    assert resultado.valido is True
    assert resultado.preco == 40.04


def test_rejeita_url_de_outro_produto():
    resultado = ValidadorPrecoAliExpress().validar_html(
        produto_id=PRODUTO_ID,
        url_final=("https://pt.aliexpress.com/" "item/999999999999.html"),
        html=html_produto(),
    )

    assert resultado.valido is False
