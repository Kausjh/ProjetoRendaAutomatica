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

URL = "https://www.kabum.com.br/" "produto/699153/monitor-teste"


def test_construtor_cria_oferta_kabum():
    deteccao = ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="Monitor Gamer",
        marketplace="kabum",
        preco_oferta=649.99,
    )

    resolucao = ResultadoResolucaoSocialScout(
        fonte="telegram",
        id_externo="teste:1",
        status="resolvido",
        marketplace="kabum",
        tipo_destino="produto",
        url_original=URL,
        url_destino=URL,
        id_produto="699153",
    )

    validacao = ResultadoValidacaoPrecoSocialScout(
        status="validado",
        marketplace="kabum",
        url=URL,
        titulo_oficial="Monitor Gamer Oficial",
        preco_oficial=649.99,
        disponivel=None,
        preco_oferta_grupo=649.99,
        preco_base_confere=True,
        cupom_validado=False,
    )

    resultado = ConstrutorOfertaSocialScout().construir(
        deteccao,
        resolucao,
        validacao,
    )

    assert resultado.status == "criada"
    assert resultado.oferta is not None
    assert resultado.oferta.loja == "KaBuM!"
    assert resultado.oferta.marketplace == "kabum"
    assert resultado.oferta.preco == 649.99

    assert resultado.oferta.nome == "Monitor Gamer Oficial"
