from unittest.mock import Mock, patch

import pytest

from affiliates.afiliador_amazon import AfiliadorAmazon
from affiliates.configuracao_afiliador import (
    ConfiguracaoAfiliador,
)
from bots.telegram_bot import TelegramBot
from formatters.oferta_formatter import OfertaFormatter
from models.oferta import Oferta
from repositories.links_afiliados_amazon_repository import (
    LinksAfiliadosAmazonRepository,
)


def criar_repository(
    tmp_path,
) -> LinksAfiliadosAmazonRepository:
    return LinksAfiliadosAmazonRepository(tmp_path / "amazon.sqlite3")


def test_repository_reutiliza_link_por_asin(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    original = "https://www.amazon.com.br/" "produto/dp/B0ABCDEF12"

    with patch.object(
        LinksAfiliadosAmazonRepository,
        "_validar_redirecionamento",
        return_value=True,
    ):
        repository.registrar(
            original,
            "https://amzn.to/abc123",
        )

    outra_url_mesmo_produto = "https://www.amazon.com.br/" "gp/product/B0ABCDEF12" "?ref_=qualquer"

    assert repository.obter_link_afiliado(outra_url_mesmo_produto) == "https://amzn.to/abc123"


def test_repository_aceita_link_longo_com_tag(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    original = "https://www.amazon.com.br/" "dp/B0ABCDEF12"

    afiliado = "https://www.amazon.com.br/" "dp/B0ABCDEF12" "?tag=exemplo-20"

    repository.registrar(
        original,
        afiliado,
    )

    assert repository.obter_link_afiliado(original) == afiliado


def test_repository_rejeita_link_nao_amazon(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    with pytest.raises(ValueError):
        repository.registrar(
            ("https://www.amazon.com.br/" "dp/B0ABCDEF12"),
            ("https://exemplo.com/" "nao-afiliado"),
        )


def test_repository_aceita_link_amazon_validado(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    original = "https://www.amazon.com.br/" "dp/B0ABCDEF12"

    with patch.object(
        LinksAfiliadosAmazonRepository,
        "_validar_redirecionamento",
        return_value=True,
    ) as validar:
        repository.registrar(
            original,
            "https://link.amazon/abc123",
        )

    validar.assert_called_once_with("https://link.amazon/abc123")

    assert repository.obter_link_afiliado(original) == "https://link.amazon/abc123"


def test_repository_rejeita_link_amazon_sem_afiliacao_validada(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    with patch.object(
        LinksAfiliadosAmazonRepository,
        "_validar_redirecionamento",
        return_value=False,
    ):
        with pytest.raises(ValueError):
            repository.registrar(
                ("https://www.amazon.com.br/" "dp/B0ABCDEF12"),
                "https://link.amazon/abc123",
            )


def test_validacao_real_do_redirecionamento_exige_tag():
    resposta = Mock()

    resposta.url = (
        "https://www.amazon.com.br/" "dp/B0ABCDEF12" "?tag=exemplo-20" "&linkCode=ll1" "&linkId=abc"
    )

    resposta.close = Mock()

    with patch(
        "repositories." "links_afiliados_amazon_repository." "requests.get",
        return_value=resposta,
    ):
        assert LinksAfiliadosAmazonRepository._validar_redirecionamento(
            "https://link.amazon/abc123"
        )


def test_validacao_real_do_redirecionamento_rejeita_sem_tag():
    resposta = Mock()

    resposta.url = "https://www.amazon.com.br/" "dp/B0ABCDEF12" "?ref_=teste"

    resposta.close = Mock()

    with patch(
        "repositories." "links_afiliados_amazon_repository." "requests.get",
        return_value=resposta,
    ):
        assert not (
            LinksAfiliadosAmazonRepository._validar_redirecionamento("https://link.amazon/abc123")
        )


def test_afiliador_usa_sitestripe_cadastrado(
    tmp_path,
):
    repository = criar_repository(tmp_path)

    original = "https://www.amazon.com.br/" "dp/B0ABCDEF12"

    with patch.object(
        LinksAfiliadosAmazonRepository,
        "_validar_redirecionamento",
        return_value=True,
    ):
        repository.registrar(
            original,
            "https://link.amazon/abc123",
        )

    afiliador = AfiliadorAmazon(
        nome="Amazon",
        dominios=[
            "amazon.com.br",
        ],
        repository=repository,
    )

    assert afiliador.gerar_link(original) == "https://link.amazon/abc123"


def test_afiliador_sem_sitestripe_nao_transforma(
    tmp_path,
):
    afiliador = AfiliadorAmazon(
        nome="Amazon",
        dominios=[
            "amazon.com.br",
        ],
        repository=criar_repository(tmp_path),
    )

    original = "https://www.amazon.com.br/" "dp/B0ABCDEF12"

    assert afiliador.gerar_link(original) == original


def test_configuracao_aceita_tipo_amazon():
    configuracao = ConfiguracaoAfiliador.criar_de_dict(
        dados={
            "nome": "Amazon",
            "tipo": "amazon",
            "ativo": True,
            "prioridade": 750,
            "dominios": [
                "amazon.com.br",
            ],
        },
        indice=1,
    )

    assert configuracao.tipo == "amazon"


def test_telegram_exige_afiliacao_amazon():
    assert TelegramBot._exige_link_afiliado("https://www.amazon.com.br/" "dp/B0ABCDEF12")

    assert TelegramBot._exige_link_afiliado("https://amzn.to/abc123")

    assert TelegramBot._exige_link_afiliado("https://link.amazon/abc123")


def test_formatter_amazon_oculta_precos():
    oferta = Oferta(
        nome="Mouse gamer de teste",
        loja="Amazon",
        preco=999.99,
        preco_antigo=1299.99,
        link="https://link.amazon/abc123",
        imagem=None,
        marketplace="amazon",
    )

    mensagem = OfertaFormatter.formatar(oferta)

    assert "ACHADO AMAZON" in mensagem
    assert "999" not in mensagem
    assert "1299" not in mensagem
    assert "R$" not in mensagem
    assert "Desconto" not in mensagem
    assert "Menor pre" not in mensagem
    assert "Vale a pena?" not in mensagem

    assert "#pub" in mensagem

    assert "Como associado da Amazon, " "eu ganho com compras qualificadas." in mensagem
