# 63.8738, -149.7525

from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)
from services.scout.construtor_oferta_social_scout import (
    ConstrutorOfertaSocialScout,
)


def test_construtor_cria_oferta_shopee():
    deteccao = ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="SSD NVMe Kingston 1TB",
        marketplace="shopee",
        preco_oferta=299.90,
    )

    resolucao = ResultadoResolucaoSocialScout(
        fonte="telegram",
        id_externo="teste:1",
        status="resolvido",
        marketplace="shopee",
        tipo_destino="produto",
        url_original=("https://s.shopee.com.br/teste"),
        url_destino=("https://shopee.com.br/" "product/10/123"),
        id_produto="123",
        id_anuncio="123",
    )

    validacao = ResultadoValidacaoPrecoSocialScout(
        status="validado",
        marketplace="shopee",
        url=resolucao.url_destino,
        titulo_oficial="SSD NVMe Kingston 1TB",
        preco_oficial=299.90,
        preco_oferta_grupo=299.90,
        preco_base_confere=True,
        motivo="teste",
    )

    resultado = ConstrutorOfertaSocialScout().construir(
        deteccao,
        resolucao,
        validacao,
    )

    assert resultado.status == "criada"
    assert resultado.oferta is not None

    assert resultado.oferta.loja == "Shopee"
    assert resultado.oferta.marketplace == "shopee"
    assert resultado.oferta.preco == 299.90
    assert resultado.oferta.id_produto == "123"
