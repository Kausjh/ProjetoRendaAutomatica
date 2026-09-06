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

URL = "https://www.mercadolivre.com.br/" "mouse-gamer-modelo-x/p/MLB12345678"


def criar_deteccao():
    return ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="Mouse Gamer Modelo X",
        marketplace="mercado_livre",
        preco_original=500.00,
        preco_oferta=300.00,
        preco_final=270.00,
        desconto_cupom_percentual=10.0,
        codigo_cupom="TESTE10",
        links=("https://meli.la/teste",),
        motivo="teste",
    )


def criar_resolucao(
    *,
    status: str = "resolvido",
    marketplace: str = "mercado_livre",
):
    return ResultadoResolucaoSocialScout(
        fonte="telegram",
        id_externo="-100123:1",
        status=status,
        marketplace=marketplace,
        tipo_destino="produto",
        url_original="https://meli.la/teste",
        url_destino=URL,
        id_produto="MLB12345678",
        id_anuncio=None,
        http_status=200,
        motivo="teste",
    )


def criar_validacao(
    *,
    status: str = "validado",
    marketplace: str = "mercado_livre",
    titulo: str = "Mouse Gamer Modelo X Oficial",
    preco: float | None = 300.00,
    preco_antigo: float | None = 500.00,
    disponivel: bool | None = True,
):
    return ResultadoValidacaoPrecoSocialScout(
        status=status,
        marketplace=marketplace,
        url=URL,
        titulo_oficial=titulo,
        preco_oficial=preco,
        preco_original_oficial=preco_antigo,
        tipo_preco_oficial="pix",
        preco_parcelado_oficial=320.00,
        parcelas=8,
        valor_parcela=40.00,
        disponivel=disponivel,
        preco_original_grupo=500.00,
        preco_oferta_grupo=300.00,
        preco_final_grupo=270.00,
        codigo_cupom="TESTE10",
        desconto_cupom_percentual=10.0,
        preco_base_confere=True,
        preco_original_confere=True,
        preco_final_coerente_com_desconto=True,
        cupom_validado=False,
        motivo="teste",
    )


def test_cria_oferta_com_dados_oficiais():
    resultado = ConstrutorOfertaSocialScout().construir(
        criar_deteccao(),
        criar_resolucao(),
        criar_validacao(),
    )

    assert resultado.status == "criada"
    assert resultado.oferta is not None

    oferta = resultado.oferta

    assert oferta.nome == "Mouse Gamer Modelo X Oficial"
    assert oferta.loja == "Mercado Livre"
    assert oferta.preco == 300.00
    assert oferta.preco_antigo == 500.00
    assert oferta.link == URL
    assert oferta.marketplace == "mercado_livre"
    assert oferta.id_produto == "MLB12345678"


def test_preco_da_oferta_nao_usa_cupom_nao_validado():
    resultado = ConstrutorOfertaSocialScout().construir(
        criar_deteccao(),
        criar_resolucao(),
        criar_validacao(),
    )

    assert resultado.oferta is not None

    assert resultado.oferta.preco == 300.00
    assert resultado.oferta.preco != 270.00


def test_preserva_cupom_apenas_como_metadado():
    resultado = ConstrutorOfertaSocialScout().construir(
        criar_deteccao(),
        criar_resolucao(),
        criar_validacao(),
    )

    assert resultado.codigo_cupom == "TESTE10"

    assert resultado.preco_condicional_grupo == 270.00

    assert resultado.cupom_validado is False


def test_prefere_titulo_oficial():
    resultado = ConstrutorOfertaSocialScout().construir(
        criar_deteccao(),
        criar_resolucao(),
        criar_validacao(titulo="Mouse Gamer Oficial"),
    )

    assert resultado.oferta is not None

    assert resultado.oferta.nome == "Mouse Gamer Oficial"


def test_usa_titulo_do_grupo_como_fallback():
    resultado = ConstrutorOfertaSocialScout().construir(
        criar_deteccao(),
        criar_resolucao(),
        criar_validacao(titulo=""),
    )

    assert resultado.oferta is not None

    assert resultado.oferta.nome == "Mouse Gamer Modelo X"


def test_rejeita_validacao_divergente():
    resultado = ConstrutorOfertaSocialScout().construir(
        criar_deteccao(),
        criar_resolucao(),
        criar_validacao(status="divergente"),
    )

    assert resultado.status == "rejeitada"
    assert resultado.oferta is None

    assert resultado.motivo == "preco_social_nao_validado"


def test_rejeita_produto_indisponivel():
    resultado = ConstrutorOfertaSocialScout().construir(
        criar_deteccao(),
        criar_resolucao(),
        criar_validacao(disponivel=False),
    )

    assert resultado.status == "rejeitada"
    assert resultado.oferta is None


def test_rejeita_outro_marketplace():
    resultado = ConstrutorOfertaSocialScout().construir(
        criar_deteccao(),
        criar_resolucao(marketplace="kabum"),
        criar_validacao(),
    )

    assert resultado.status == "rejeitada"
    assert resultado.oferta is None


def test_preco_antigo_invalido_nao_contamina_oferta():
    resultado = ConstrutorOfertaSocialScout().construir(
        criar_deteccao(),
        criar_resolucao(),
        criar_validacao(
            preco=300.00,
            preco_antigo=250.00,
        ),
    )

    assert resultado.oferta is not None
    assert resultado.oferta.preco == 300.00
    assert resultado.oferta.preco_antigo is None
