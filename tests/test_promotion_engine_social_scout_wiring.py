# 63.8738, -149.7525

import inspect
from unittest.mock import Mock

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
from services.inteligencia_sinal_preco import (
    InteligenciaSinalPreco,
)
from services.scout.construtor_oferta_social_scout import (
    ConstrutorOfertaSocialScout,
)
from services.scout.enriquecedor_promocao_social_scout import (
    EnriquecedorPromocaoSocialScout,
)
from services.scout.promotion_engine_ml import (
    PromotionEngineMercadoLivre,
    ResultadoPromocaoMarketplace,
)

URL_FONTE = "https://meli.la/teste"

URL_DESTINO = "https://www.mercadolivre.com.br/" "controle-teste/p/MLB30055107"


def deteccao():
    return ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="Controle Xbox Pulse Red",
        marketplace="mercado_livre",
        preco_original=599.0,
        preco_oferta=358.79,
        preco_final=287.0,
        # 358.79 -> 287.00 equivale a ~20.01%,
        # nao 20.00%.
        desconto_cupom_percentual=20.01,
        codigo_cupom="MELIMAISPOSDD",
        cupons=("MELIMAISPOSDD",),
        links=(URL_FONTE,),
        motivo="teste",
    )


def resolucao():
    return ResultadoResolucaoSocialScout(
        fonte="telegram",
        id_externo="teste:1",
        status="resolvido",
        marketplace="mercado_livre",
        tipo_destino="produto",
        url_original=URL_FONTE,
        url_destino=URL_DESTINO,
        id_produto="MLB30055107",
        motivo="teste",
    )


def validacao(
    *,
    status="validado",
):
    return ResultadoValidacaoPrecoSocialScout(
        status=status,
        marketplace="mercado_livre",
        url=URL_DESTINO,
        titulo_oficial=("Controle Xbox Pulse Red Oficial"),
        preco_oficial=358.79,
        preco_original_oficial=599.0,
        tipo_preco_oficial="pix",
        disponivel=True,
        preco_original_grupo=599.0,
        preco_oferta_grupo=358.79,
        preco_final_grupo=287.0,
        codigo_cupom="MELIMAISPOSDD",
        desconto_cupom_percentual=20.01,
        preco_base_confere=True,
        preco_original_confere=True,
        preco_final_coerente_com_desconto=True,
        cupom_validado=False,
        motivo="teste",
    )


def resultado_promocao(
    *,
    preco,
    confere,
):
    return ResultadoPromocaoMarketplace(
        status="confirmada",
        id_produto="MLB30055107",
        promocao_confirmada=True,
        tipo_promocao=("preco_final_com_cupom"),
        preco_base=358.79,
        preco_promocional=preco,
        valor_desconto=round(
            358.79 - preco,
            2,
        ),
        desconto_percentual=round(
            (358.79 - preco) / 358.79 * 100,
            2,
        ),
        preco_grupo=287.0,
        preco_grupo_confere=confere,
        codigo_cupom_validado=False,
        fonte_url=URL_FONTE,
        motivo=("promocao_oficial_no_" "card_exato_confirmada"),
    )


def criar_enriquecedor(
    promocao,
):
    engine = Mock()

    engine.inspecionar.return_value = promocao

    return (
        EnriquecedorPromocaoSocialScout(promotion_engine=engine),
        engine,
    )


def test_nao_enriquece_status_ainda_rejeitado():
    enriquecedor, engine = criar_enriquecedor(
        resultado_promocao(
            preco=315.73,
            confere=False,
        )
    )

    original = validacao(status="divergente")

    resultado = enriquecedor.aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=original,
    )

    assert resultado == original

    engine.inspecionar.assert_not_called()


def test_transporta_promocao_divergente_do_preco_social():
    enriquecedor, engine = criar_enriquecedor(
        resultado_promocao(
            preco=315.73,
            confere=False,
        )
    )

    resultado = enriquecedor.aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=validacao(),
    )

    assert resultado.status == "validado"

    assert resultado.promocao_marketplace_confirmada is True

    assert resultado.preco_promocional_marketplace == 315.73

    assert resultado.preco_grupo_confere_promocao is False

    # Codigo textual continua nao validado.
    assert resultado.cupom_validado is False

    engine.inspecionar.assert_called_once()


def test_promocao_com_preco_igual_grupo_nao_valida_codigo():
    enriquecedor, _ = criar_enriquecedor(
        resultado_promocao(
            preco=287.0,
            confere=True,
        )
    )

    resultado = enriquecedor.aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=validacao(),
    )

    assert resultado.promocao_marketplace_confirmada is True

    assert resultado.preco_grupo_confere_promocao is True

    # Continua False nesta fase.
    assert resultado.cupom_validado is False


def test_construtor_transporta_promocao_sem_trocar_preco():
    enriquecedor, _ = criar_enriquecedor(
        resultado_promocao(
            preco=315.73,
            confere=False,
        )
    )

    validada = enriquecedor.aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=validacao(),
    )

    construcao = ConstrutorOfertaSocialScout().construir(
        deteccao(),
        resolucao(),
        validada,
    )

    assert construcao.oferta is not None

    oferta = construcao.oferta

    # Fonte de verdade continua marketplace.
    assert oferta.preco == 358.79

    assert oferta.promocao_marketplace_confirmada is True

    assert oferta.preco_promocional_marketplace == 315.73

    assert oferta.preco_grupo_confere_promocao is False

    assert oferta.cupom_validado_descoberta is False


def test_promotion_intelligence_confirma_preco_sem_validar_codigo():
    enriquecedor, _ = criar_enriquecedor(
        resultado_promocao(
            preco=287.0,
            confere=True,
        )
    )

    validada = enriquecedor.aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=validacao(),
    )

    construcao = ConstrutorOfertaSocialScout().construir(
        deteccao(),
        resolucao(),
        validada,
    )

    assert construcao.oferta is not None

    oferta = construcao.oferta

    assert oferta.promocao_marketplace_confirmada is True

    assert oferta.preco_promocional_marketplace == 287.0

    assert oferta.preco_grupo_confere_promocao is True

    # O Promotion Engine nao provou o codigo.
    assert oferta.cupom_validado_descoberta is False

    sinal = InteligenciaSinalPreco().analisar(oferta)

    # Agora o PRECO possui evidencia oficial.
    assert sinal.status == "confirmado"
    assert sinal.confirmado is True

    # Mas o codigo continua independente.
    assert sinal.cupom_validado is False

    assert "preco_promocional_marketplace_confirmado" in sinal.motivos

    assert oferta.preco == validada.preco_oficial


def test_wiring_fica_depois_politica_v12_e_antes_status():
    fonte = inspect.getsource(SocialScoutScraper.buscar_ofertas)

    politica = fonte.index("self.politica_preco_social")

    promocao = fonte.index("self.enriquecedor_promocao")

    verificacao_status = fonte.index('validacao.status == "erro"')

    assert politica < promocao
    assert promocao < verificacao_status


def test_social_scout_default_possui_enriquecedor():
    scraper = SocialScoutScraper(
        repository=object(),
        processamentos_repository=object(),
        detector=object(),
        resolvedor=object(),
        validador_preco=object(),
        processador_shopee=object(),
        processador_aliexpress=object(),
        processador_kabum=object(),
        construtor=object(),
    )

    assert isinstance(
        scraper.enriquecedor_promocao,
        EnriquecedorPromocaoSocialScout,
    )

    assert isinstance(
        scraper.enriquecedor_promocao.promotion_engine,
        PromotionEngineMercadoLivre,
    )


def test_fecha_engine_depois_de_inspecao_bem_sucedida():
    enriquecedor, engine = criar_enriquecedor(
        resultado_promocao(
            preco=315.73,
            confere=False,
        )
    )

    resultado = enriquecedor.aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=validacao(),
    )

    assert resultado.status == "validado"

    engine.inspecionar.assert_called_once()

    engine.fechar.assert_called_once_with()


def test_fecha_engine_mesmo_quando_inspecao_falha():
    engine = Mock()

    engine.inspecionar.side_effect = RuntimeError("falha_teste")

    enriquecedor = EnriquecedorPromocaoSocialScout(promotion_engine=engine)

    resultado = enriquecedor.aplicar(
        deteccao=deteccao(),
        resolucao=resolucao(),
        validacao=validacao(),
    )

    # Promotion Intelligence continua sendo
    # enriquecimento fail-open.
    assert resultado.status == "validado"

    assert resultado.status_promocao_marketplace == "erro"

    assert resultado.promocao_marketplace_confirmada is False

    assert resultado.cupom_validado is False

    engine.inspecionar.assert_called_once()

    # A regressao que causava o conflito CDP.
    engine.fechar.assert_called_once_with()
