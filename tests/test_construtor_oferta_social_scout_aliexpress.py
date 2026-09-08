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


def test_construtor_cria_aliexpress():
    url = "https://pt.aliexpress.com/" "item/1005001234567890.html"

    d = ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="SSD NVMe 1TB",
        marketplace="aliexpress",
        preco_oferta=299.90,
    )

    r = ResultadoResolucaoSocialScout(
        fonte="telegram",
        id_externo="teste:1",
        status="resolvido",
        marketplace="aliexpress",
        tipo_destino="produto",
        url_original=url,
        url_destino=url,
        id_produto="1005001234567890",
        id_anuncio="1005001234567890",
    )

    v = ResultadoValidacaoPrecoSocialScout(
        status="validado",
        marketplace="aliexpress",
        url=url,
        preco_oficial=299.90,
        preco_original_oficial=349.90,
        disponivel=True,
        preco_oferta_grupo=299.90,
        preco_base_confere=True,
    )

    resultado = ConstrutorOfertaSocialScout().construir(
        d,
        r,
        v,
    )

    assert resultado.status == "criada"
    assert resultado.oferta is not None
    assert resultado.oferta.loja == "AliExpress"
    assert resultado.oferta.marketplace == "aliexpress"
    assert resultado.oferta.preco == 299.90
