from unittest.mock import Mock, patch

import requests

from models.mensagem_social_scout import (
    MensagemSocialScout,
)
from services.scout.social_scout_destino_resolver import (
    ResolvedorDestinoSocialScout,
)


def criar_mensagem(
    *,
    texto: str,
    links: tuple[str, ...],
    message_id: int = 10,
) -> MensagemSocialScout:
    return MensagemSocialScout(
        fonte="telegram",
        chat_id="-100123",
        message_id=message_id,
        chat_titulo="Grupo Teste",
        texto=texto,
        links=links,
    )


def criar_html_social(
    *,
    titulo: str,
    links: tuple[str, ...],
) -> str:
    partes = [
        "<html><head>",
        ('<meta property="og:title" ' f'content="{titulo}">'),
        "</head><body><script>",
    ]

    for link in links:
        escapado = link.replace(
            "/",
            r"\u002F",
        )

        partes.append(f'{{"url":"{escapado}"}}')

    partes.extend(
        [
            "</script></body></html>",
        ]
    )

    return "".join(partes)


def link_featured(
    *,
    item_id: str,
    produto: str = "produto-teste",
    user_product_id: str = "MLBU1234567890",
    c_uid: str = "abc",
) -> str:
    return (
        "https://www.mercadolivre.com.br/"
        f"{produto}/up/{user_product_id}"
        f"?pdp_filters=item_id%3A{item_id}"
        "#polycard_client=recommendations_home_affiliate-profile"
        "&wid="
        f"{item_id}"
        "&source=affiliate-profile"
        "&c_id=/home/card-featured/element"
        "&c_uid="
        f"{c_uid}"
    )


def test_resolve_link_direto_mercado_livre_sem_http():
    link = (
        "https://produto.mercadolivre.com.br/"
        "MLB-5108080657-produto-teste-_JM"
        "?tracking=abc#origem"
    )

    mensagem = criar_mensagem(
        texto=("Produto Teste\n" "Por: R$ 199,90\n" f"{link}"),
        links=(link,),
    )

    with patch("services.scout." "social_scout_destino_resolver." "requests.get") as requisicao:
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    requisicao.assert_not_called()

    assert resultado.status == "resolvido"
    assert resultado.marketplace == "mercado_livre"
    assert resultado.tipo_destino == "produto"

    assert resultado.id_produto == "MLB5108080657"

    assert resultado.url_destino == (
        "https://produto.mercadolivre.com.br/" "MLB-5108080657-produto-teste-_JM"
    )


def test_resolve_meli_la_ate_produto_oficial():
    link_curto = "https://meli.la/abc123"

    mensagem = criar_mensagem(
        texto=("Produto Teste\n" "Por: R$ 149,90\n" f"{link_curto}"),
        links=(link_curto,),
    )

    resposta = Mock()
    resposta.url = (
        "https://www.mercadolivre.com.br/" "produto-teste/p/MLB23343532" "?matt_tool=123#origem"
    )
    resposta.status_code = 200

    with patch(
        "services.scout." "social_scout_destino_resolver." "requests.get",
        return_value=resposta,
    ) as requisicao:
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    requisicao.assert_called_once()

    resposta.close.assert_called_once()

    assert resultado.status == "resolvido"
    assert resultado.id_produto == "MLB23343532"

    assert resultado.url_original == link_curto

    assert resultado.url_destino == (
        "https://www.mercadolivre.com.br/" "produto-teste/p/MLB23343532"
    )


def test_preserva_id_anuncio_do_destino():
    link_curto = "https://meli.la/xyz789"

    mensagem = criar_mensagem(
        texto=("Produto Teste\n" "Por: R$ 349,90\n" f"{link_curto}"),
        links=(link_curto,),
    )

    resposta = Mock()
    resposta.url = (
        "https://www.mercadolivre.com.br/" "produto-teste/p/MLB12345678" "?wid=MLB9876543210"
    )
    resposta.status_code = 200

    with patch(
        "services.scout." "social_scout_destino_resolver." "requests.get",
        return_value=resposta,
    ):
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    assert resultado.status == "resolvido"
    assert resultado.id_produto == "MLB12345678"
    assert resultado.id_anuncio == "MLB9876543210"


def test_ignora_cupom_geral_sem_abrir_link():
    link = "https://meli.la/cupom"

    mensagem = criar_mensagem(
        texto=("Cupons no APP\n\n" "R$ 50 OFF em R$ 500: TESTE50\n" f"{link}"),
        links=(link,),
    )

    with patch("services.scout." "social_scout_destino_resolver." "requests.get") as requisicao:
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    requisicao.assert_not_called()

    assert resultado.status == "ignorado"


def test_marketplace_diferente_ainda_nao_e_resolvido():
    link = "https://www.kabum.com.br/produto/123/teste"

    mensagem = criar_mensagem(
        texto=("Mouse Gamer\n" "Por: R$ 99,90\n" f"{link}"),
        links=(link,),
    )

    resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    assert resultado.status == "nao_suportado"
    assert resultado.marketplace == "kabum"

    assert resultado.motivo == "marketplace_social_ainda_nao_suportado"


def test_falha_http_do_meli_la_vira_erro():
    link = "https://meli.la/falha"

    mensagem = criar_mensagem(
        texto=("Produto Teste\n" "Por: R$ 199,90\n" f"{link}"),
        links=(link,),
    )

    with patch(
        "services.scout." "social_scout_destino_resolver." "requests.get",
        side_effect=requests.RequestException("falha simulada"),
    ):
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    assert resultado.status == "erro"

    assert resultado.motivo == "falha_ao_resolver_link_curto"


def test_meli_la_para_dominio_externo_nao_e_aceito():
    link = "https://meli.la/externo"

    mensagem = criar_mensagem(
        texto=("Produto Teste\n" "Por: R$ 199,90\n" f"{link}"),
        links=(link,),
    )

    resposta = Mock()
    resposta.url = "https://loja-exemplo.com/produto"
    resposta.status_code = 200

    with patch(
        "services.scout." "social_scout_destino_resolver." "requests.get",
        return_value=resposta,
    ):
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    assert resultado.status == "nao_suportado"

    assert resultado.motivo == ("link_curto_nao_levou_ao_" "mercado_livre_oficial")


def test_id_externo_combina_chat_e_mensagem():
    link = "https://produto.mercadolivre.com.br/" "MLB-1234567890-produto-_JM"

    mensagem = criar_mensagem(
        texto=("Produto Teste\n" "Por: R$ 100,00\n" f"{link}"),
        links=(link,),
        message_id=987,
    )

    resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    assert resultado.id_externo == "-100123:987"


def test_resolve_card_destacado_de_pagina_social():
    link_curto = "https://meli.la/social123"

    mensagem = criar_mensagem(
        texto=("Mouse Gamer Modelo X\n" "Por: R$ 251,74\n" f"{link_curto}"),
        links=(link_curto,),
    )

    featured = link_featured(
        item_id="MLB8765432109",
        produto="mouse-gamer-modelo-x",
        user_product_id="MLBU2468135790",
    )

    resposta = Mock()
    resposta.url = "https://www.mercadolivre.com.br/" "social/perfilteste?tracking=abc"
    resposta.status_code = 200
    resposta.text = criar_html_social(
        titulo=("Mouse Gamer Modelo X " "Preto RGB USB"),
        links=(featured,),
    )

    with patch(
        "services.scout." "social_scout_destino_resolver." "requests.get",
        return_value=resposta,
    ):
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    assert resultado.status == "resolvido"
    assert resultado.id_produto is None
    assert resultado.id_anuncio == "MLB8765432109"

    assert resultado.url_destino == (
        "https://www.mercadolivre.com.br/"
        "mouse-gamer-modelo-x/"
        "up/MLBU2468135790"
        "?pdp_filters=item_id%3AMLB8765432109"
    )

    assert resultado.motivo == "produto_social_mercado_livre_identificado"


def test_pagina_social_nao_escolhe_recomendacao():
    link_curto = "https://meli.la/social456"

    mensagem = criar_mensagem(
        texto=("Mouse Gamer Modelo X\n" "Por: R$ 251,74\n" f"{link_curto}"),
        links=(link_curto,),
    )

    recomendacao = (
        "https://www.mercadolivre.com.br/"
        "outro-produto/p/MLB38713288"
        "?wid=MLB5303396266"
        "#c_id=/home/"
        "affiliate-profile-recommendations/element"
    )

    featured = link_featured(
        item_id="MLB8765432109",
        produto="mouse-gamer-modelo-x",
        user_product_id="MLBU2468135790",
    )

    resposta = Mock()
    resposta.url = "https://www.mercadolivre.com.br/" "social/perfilteste"
    resposta.status_code = 200
    resposta.text = criar_html_social(
        titulo=("Mouse Gamer Modelo X " "Preto RGB USB"),
        links=(
            recomendacao,
            featured,
        ),
    )

    with patch(
        "services.scout." "social_scout_destino_resolver." "requests.get",
        return_value=resposta,
    ):
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    assert resultado.status == "resolvido"
    assert resultado.id_anuncio == "MLB8765432109"

    assert "MLB5303396266" not in resultado.url_destino


def test_pagina_social_recusa_titulo_divergente():
    link_curto = "https://meli.la/social789"

    mensagem = criar_mensagem(
        texto=("Notebook Gamer Lenovo Legion\n" "Por: R$ 5000,00\n" f"{link_curto}"),
        links=(link_curto,),
    )

    featured = link_featured(
        item_id="MLB8765432109",
        produto="mouse-gamer-modelo-x",
        user_product_id="MLBU2468135790",
    )

    resposta = Mock()
    resposta.url = "https://www.mercadolivre.com.br/" "social/perfilteste"
    resposta.status_code = 200
    resposta.text = criar_html_social(
        titulo=("Mouse Gamer Modelo X " "Preto RGB USB"),
        links=(featured,),
    )

    with patch(
        "services.scout." "social_scout_destino_resolver." "requests.get",
        return_value=resposta,
    ):
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    assert resultado.status == "nao_suportado"

    assert resultado.motivo == "pagina_social_titulo_divergente"


def test_pagina_social_aceita_links_duplicados_do_mesmo_featured():
    link_curto = "https://meli.la/socialduplicado"

    mensagem = criar_mensagem(
        texto=("Mouse Gamer Modelo X\n" "Por: R$ 251,74\n" f"{link_curto}"),
        links=(link_curto,),
    )

    featured_1 = link_featured(
        item_id="MLB8765432109",
        produto="mouse-gamer-modelo-x",
        user_product_id="MLBU2468135790",
        c_uid="aaa",
    )

    featured_2 = link_featured(
        item_id="MLB8765432109",
        produto="mouse-gamer-modelo-x",
        user_product_id="MLBU2468135790",
        c_uid="bbb",
    )

    resposta = Mock()
    resposta.url = "https://www.mercadolivre.com.br/" "social/perfilteste"
    resposta.status_code = 200
    resposta.text = criar_html_social(
        titulo=("Mouse Gamer Modelo X " "Preto RGB USB"),
        links=(
            featured_1,
            featured_2,
        ),
    )

    with patch(
        "services.scout." "social_scout_destino_resolver." "requests.get",
        return_value=resposta,
    ):
        resultado = ResolvedorDestinoSocialScout().resolver(mensagem)

    assert resultado.status == "resolvido"
    assert resultado.id_anuncio == "MLB8765432109"
