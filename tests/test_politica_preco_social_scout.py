# 63.8738, -149.7525

import inspect

from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)
from scrapers.social_scout_scraper import (
    SocialScoutScraper,
)
from services.scout.politica_preco_social_scout import (
    PoliticaPrecoSocialScout,
)


def deteccao(
    marketplace="mercado_livre",
):
    return ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="Produto Gamer Teste",
        marketplace=marketplace,
        preco_oferta=500.0,
        preco_final=450.0,
        codigo_cupom="TESTE10",
    )


def resolucao(
    marketplace="mercado_livre",
):
    return ResultadoResolucaoSocialScout(
        fonte="telegram",
        id_externo="teste:1",
        status="resolvido",
        marketplace=marketplace,
        tipo_destino="produto",
        url_destino=("https://exemplo.invalid/produto"),
        id_produto="123",
    )


def validacao(
    motivo,
    *,
    marketplace="mercado_livre",
    preco_oficial=599.0,
    status="rejeitado",
    disponivel=True,
):
    return ResultadoValidacaoPrecoSocialScout(
        status=status,
        marketplace=marketplace,
        url=("https://exemplo.invalid/produto"),
        titulo_oficial=("Produto Gamer Teste Oficial"),
        preco_oficial=preco_oficial,
        disponivel=disponivel,
        preco_base_confere=False,
        motivo=motivo,
    )


def aplicar(
    motivo,
    *,
    marketplace="mercado_livre",
    preco_oficial=599.0,
    status="rejeitado",
):
    return PoliticaPrecoSocialScout().aplicar(
        deteccao=deteccao(marketplace),
        resolucao=resolucao(marketplace),
        validacao=validacao(
            motivo,
            marketplace=marketplace,
            preco_oficial=preco_oficial,
            status=status,
        ),
    )


def test_v12_recupera_ml_sem_preco_base():
    resultado = aplicar(
        "mensagem_social_sem_preco_base",
        status="nao_verificavel",
    )

    assert resultado.status == "validado"
    assert resultado.preco_oficial == 599.0
    assert resultado.preco_base_confere is False

    assert "preco_social_apenas_sinal" in resultado.motivo


def test_v12_recupera_ml_com_divergencia_social():
    resultado = aplicar("precos_da_fonte_divergem_dos_dados_oficiais")

    assert resultado.status == "validado"
    assert resultado.preco_oficial == 599.0
    assert resultado.preco_base_confere is False


def test_v12_recupera_shopee_com_divergencia_social():
    resultado = aplicar(
        "preco_base_shopee_divergente",
        marketplace="shopee",
    )

    assert resultado.status == "validado"
    assert resultado.preco_oficial == 599.0
    assert resultado.preco_base_confere is False


def test_v12_recupera_shopee_sem_preco_base():
    resultado = aplicar(
        "mensagem_shopee_sem_preco_base",
        marketplace="shopee",
        status="nao_verificavel",
    )

    assert resultado.status == "validado"


def test_v12_nao_recupera_variante_shopee():
    original = validacao(
        "produto_shopee_com_variantes_de_preco",
        marketplace="shopee",
        status="nao_verificavel",
    )

    resultado = PoliticaPrecoSocialScout().aplicar(
        deteccao=deteccao("shopee"),
        resolucao=resolucao("shopee"),
        validacao=original,
    )

    assert resultado == original


def test_v12_nao_recupera_titulo_divergente():
    original = validacao(
        "pagina_social_titulo_divergente",
        status="nao_suportado",
    )

    resultado = PoliticaPrecoSocialScout().aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=original,
    )

    assert resultado == original


def test_v12_nao_recupera_sem_preco_oficial():
    original = validacao(
        "mensagem_social_sem_preco_base",
        preco_oficial=None,
        status="nao_verificavel",
    )

    resultado = PoliticaPrecoSocialScout().aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=original,
    )

    assert resultado == original


def test_v12_nao_recupera_marketplace_divergente():
    original = validacao(
        "preco_base_shopee_divergente",
        marketplace="shopee",
    )

    resultado = PoliticaPrecoSocialScout().aplicar(
        deteccao=deteccao("mercado_livre"),
        resolucao=resolucao("shopee"),
        validacao=original,
    )

    assert resultado == original


def test_v12_nao_recupera_indisponivel():
    original = validacao(
        "mensagem_social_sem_preco_base",
        disponivel=False,
        status="nao_verificavel",
    )

    resultado = PoliticaPrecoSocialScout().aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=original,
    )

    assert resultado == original


def test_v12_preserva_validacao_ja_aprovada():
    original = validacao(
        "preco_social_confirmado",
        status="validado",
    )

    resultado = PoliticaPrecoSocialScout().aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=original,
    )

    assert resultado == original


def test_v12_wiring_acontece_antes_do_status():
    fonte = inspect.getsource(SocialScoutScraper.buscar_ofertas)

    chamada_politica = "self.politica_preco_social"

    verificacao_status = 'validacao.status == "erro"'

    assert chamada_politica in fonte
    assert verificacao_status in fonte

    assert fonte.index(chamada_politica) < fonte.index(verificacao_status)


def test_v12_versao_processador():
    assert SocialScoutScraper.VERSAO_PROCESSADOR == "12"
