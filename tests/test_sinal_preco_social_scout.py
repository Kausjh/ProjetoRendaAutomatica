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


def test_transporta_sinal_sem_trocar_preco_oficial():
    deteccao = ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="INNO3D RTX 5060",
        marketplace="shopee",
        preco_original=2999.0,
        preco_oferta=2699.0,
        preco_final=2399.0,
        desconto_anunciado_percentual=10.0,
        desconto_cupom_percentual=11.12,
        codigo_cupom="GPU300",
        cupons=("GPU300",),
        links=("https://shopee.com.br/produto",),
        motivo="teste",
    )

    resolucao = ResultadoResolucaoSocialScout(
        fonte="telegram",
        id_externo="teste:1",
        status="resolvido",
        marketplace="shopee",
        tipo_destino="produto",
        url_original="https://shopee.com.br/produto",
        url_destino="https://shopee.com.br/produto",
        id_produto="43880126119",
        id_anuncio="43880126119",
        http_status=200,
        motivo="teste",
    )

    validacao = ResultadoValidacaoPrecoSocialScout(
        status="validado",
        marketplace="shopee",
        url="https://shopee.com.br/produto",
        titulo_oficial="INNO3D NVIDIA RTX 5060 8GB",
        preco_oficial=2699.0,
        preco_original_oficial=None,
        tipo_preco_oficial="oficial",
        preco_parcelado_oficial=None,
        parcelas=None,
        valor_parcela=None,
        disponivel=True,
        preco_valido_ate=None,
        preco_original_grupo=2999.0,
        preco_oferta_grupo=2699.0,
        preco_final_grupo=2399.0,
        codigo_cupom="GPU300",
        desconto_cupom_percentual=11.12,
        preco_base_confere=True,
        preco_original_confere=None,
        preco_final_coerente_com_desconto=True,
        cupom_validado=True,
        motivo="teste",
    )

    resultado = ConstrutorOfertaSocialScout().construir(
        deteccao,
        resolucao,
        validacao,
    )

    assert resultado.oferta is not None

    oferta = resultado.oferta

    assert oferta.preco == 2699.0
    assert oferta.origem_descoberta == "social_scout"

    assert oferta.preco_condicional_observado == 2399.0

    assert oferta.codigo_cupom_observado == "GPU300"

    assert oferta.cupom_validado_descoberta is True
