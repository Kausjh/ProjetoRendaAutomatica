# 63.8738, -149.7525

from __future__ import annotations

from types import SimpleNamespace

import pytest

from models.community_discovery import DescobertaComunitaria
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)
from services.community_discovery_marketplace_adapter import (
    CommunityDiscoveryMarketplaceAdapter,
)
from services.scout.mercado_livre_catalog_api import (
    ErroApiMercadoLivre,
    SnapshotCatalogoMercadoLivre,
)


def descoberta(
    marketplace: str | None,
    *,
    status: str = "processing",
) -> DescobertaComunitaria:
    return DescobertaComunitaria(
        id=f"dsc_{marketplace or 'unknown'}",
        conta_id="usr_teste",
        url="https://example.com/oferta",
        url_normalizada="https://example.com/oferta",
        marketplace=marketplace,
        status=status,
        tentativas=1,
        disponivel_em="2026-09-15T20:00:00+00:00",
        processando_desde="2026-09-15T20:00:00+00:00",
        motivo_status=None,
        canonical_key=None,
        criado_em="2026-09-15T19:00:00+00:00",
        atualizado_em="2026-09-15T20:00:00+00:00",
    )


def resolucao(
    marketplace: str,
    *,
    status: str = "resolvido",
    motivo: str = "produto_identificado",
    id_produto: str | None = "123",
    id_anuncio: str | None = "123",
) -> ResultadoResolucaoSocialScout:
    return ResultadoResolucaoSocialScout(
        fonte="community_discovery",
        id_externo="usr_teste:1",
        status=status,
        marketplace=marketplace,
        tipo_destino="produto",
        url_original="https://example.com/oferta",
        url_destino="https://example.com/produto",
        id_produto=id_produto,
        id_anuncio=id_anuncio,
        motivo=motivo,
    )


def validacao(
    marketplace: str,
    *,
    status: str = "validado",
    motivo: str = "preco_confirmado",
    titulo: str = "Produto oficial",
    preco: float | None = 100.0,
    disponivel: bool | None = True,
) -> ResultadoValidacaoPrecoSocialScout:
    return ResultadoValidacaoPrecoSocialScout(
        status=status,
        marketplace=marketplace,
        url="https://example.com/produto",
        titulo_oficial=titulo,
        preco_oficial=preco,
        tipo_preco_oficial="teste",
        disponivel=disponivel,
        motivo=motivo,
    )


class ProcessadorFake:
    def __init__(
        self,
        *,
        resultado_resolucao,
        resultado_validacao,
    ):
        self.resultado_resolucao = resultado_resolucao
        self.resultado_validacao = resultado_validacao
        self.resolver_chamadas = 0
        self.validar_chamadas = 0

    def resolver(self, mensagem, deteccao):
        self.resolver_chamadas += 1
        assert mensagem.fonte == "community_discovery"
        assert deteccao.classificacao == "oferta_produto"
        return self.resultado_resolucao

    def validar(self, deteccao, resultado_resolucao):
        self.validar_chamadas += 1
        assert resultado_resolucao is self.resultado_resolucao
        assert deteccao.preco_oferta is None
        return self.resultado_validacao


class ConstrutorFake:
    def __init__(self):
        self.chamadas = 0
        self.ultima_validacao = None

    def construir(self, deteccao, resolucao, resultado_validacao):
        self.chamadas += 1
        self.ultima_validacao = resultado_validacao

        oferta = SimpleNamespace(
            origem_descoberta="social_scout",
        )

        return SimpleNamespace(
            status="criada",
            oferta=oferta,
            motivo="oferta_criada_com_preco_oficial",
        )


def test_shopee_link_only_promove_preco_oficial_e_cria_oferta():
    processador = ProcessadorFake(
        resultado_resolucao=resolucao("shopee"),
        resultado_validacao=validacao(
            "shopee",
            status="nao_verificavel",
            motivo="mensagem_shopee_sem_preco_base",
        ),
    )
    construtor = ConstrutorFake()

    adapter = CommunityDiscoveryMarketplaceAdapter(
        processador_shopee=processador,
        construtor=construtor,
    )

    resultado = adapter.processar(descoberta("shopee"))

    assert resultado.status == "oferta_criada"
    assert resultado.transitorio is False
    assert resultado.oferta is not None
    assert resultado.oferta.origem_descoberta == "community_discovery"
    assert construtor.chamadas == 1
    assert construtor.ultima_validacao.status == "validado"
    assert construtor.ultima_validacao.preco_base_confere is True


def test_kabum_link_only_usa_mesma_regra_de_preco_oficial():
    processador = ProcessadorFake(
        resultado_resolucao=resolucao("kabum"),
        resultado_validacao=validacao(
            "kabum",
            status="nao_verificavel",
            motivo="mensagem_kabum_sem_preco_base",
            titulo="Produto KaBuM!",
        ),
    )
    construtor = ConstrutorFake()

    adapter = CommunityDiscoveryMarketplaceAdapter(
        processador_kabum=processador,
        construtor=construtor,
    )

    resultado = adapter.processar(descoberta("kabum"))

    assert resultado.status == "oferta_criada"
    assert processador.resolver_chamadas == 1
    assert processador.validar_chamadas == 1
    assert construtor.chamadas == 1


def test_aliexpress_sem_titulo_oficial_nao_fabrica_nome():
    processador = ProcessadorFake(
        resultado_resolucao=resolucao("aliexpress"),
        resultado_validacao=validacao(
            "aliexpress",
            status="nao_verificavel",
            motivo="mensagem_aliexpress_sem_preco_base",
            titulo="",
        ),
    )
    construtor = ConstrutorFake()

    adapter = CommunityDiscoveryMarketplaceAdapter(
        processador_aliexpress=processador,
        construtor=construtor,
    )

    resultado = adapter.processar(descoberta("aliexpress"))

    assert resultado.status == "nao_suportada"
    assert resultado.motivo == "titulo_oficial_ausente_para_" "community_discovery_link_only"
    assert construtor.chamadas == 0


def test_amazon_fica_explicitamente_fora_do_adapter():
    adapter = CommunityDiscoveryMarketplaceAdapter()

    resultado = adapter.processar(descoberta("amazon"))

    assert resultado.status == "nao_suportada"
    assert resultado.motivo == "amazon_sem_processador_de_produto"


def test_erro_de_resolucao_vira_retry():
    processador = ProcessadorFake(
        resultado_resolucao=resolucao(
            "shopee",
            status="erro",
            motivo="falha_api_shopee_resolucao",
        ),
        resultado_validacao=validacao("shopee"),
    )

    adapter = CommunityDiscoveryMarketplaceAdapter(
        processador_shopee=processador,
    )

    resultado = adapter.processar(descoberta("shopee"))

    assert resultado.status == "retry"
    assert resultado.transitorio is True
    assert resultado.motivo == "falha_api_shopee_resolucao"
    assert processador.validar_chamadas == 0


class ResolvedorMlFake:
    def resolver(self, mensagem, deteccao):
        assert mensagem.fonte == "community_discovery"
        assert deteccao.marketplace == "mercado_livre"
        return resolucao(
            "mercado_livre",
            id_produto="MLB75627492",
            id_anuncio=None,
        )


class ClienteCatalogoMlFake:
    def __init__(self):
        self.product_ids = []

    def consultar_snapshot(self, product_id):
        self.product_ids.append(product_id)

        return SnapshotCatalogoMercadoLivre(
            product_id=product_id,
            item_id="MLB4936660307",
            titulo="Produto Mercado Livre",
            preco=149.90,
            currency_id="BRL",
            seller_id=123,
        )


class ClienteCatalogoMlErroFake:
    def consultar_snapshot(self, product_id):
        assert product_id == "MLB75627492"

        raise ErroApiMercadoLivre(
            "api_mercado_livre_rate_limit",
            status_code=429,
            transitorio=True,
        )


class ValidadorMlFake:
    def __init__(self):
        self.preco_recebido = None
        self.snapshot_recebido = None

    def _avaliar_snapshot(
        self,
        *,
        deteccao,
        resolucao,
        snapshot,
    ):
        self.preco_recebido = deteccao.preco_oferta
        self.snapshot_recebido = snapshot

        assert snapshot["preco_oficial"] == 149.90
        assert snapshot["titulo"] == "Produto Mercado Livre"
        assert snapshot["mercado_livre_item_id"] == "MLB4936660307"
        assert resolucao.marketplace == "mercado_livre"

        return validacao(
            "mercado_livre",
            titulo=snapshot["titulo"],
            preco=snapshot["preco_oficial"],
        )


def test_mercado_livre_usa_api_catalogo_sem_capturar_browser():
    cliente_catalogo = ClienteCatalogoMlFake()
    validador_ml = ValidadorMlFake()
    construtor = ConstrutorFake()

    adapter = CommunityDiscoveryMarketplaceAdapter(
        resolvedor_ml=ResolvedorMlFake(),
        validador_ml=validador_ml,
        cliente_catalogo_ml=cliente_catalogo,
        construtor=construtor,
    )

    resultado = adapter.processar(descoberta("mercado_livre"))

    assert resultado.status == "oferta_criada"
    assert cliente_catalogo.product_ids == ["MLB75627492"]
    assert validador_ml.preco_recebido == 149.90
    assert validador_ml.snapshot_recebido["tipo_preco"] == "catalog_api_listing"
    assert resultado.oferta.origem_descoberta == "community_discovery"


def test_mercado_livre_rate_limit_da_api_vira_retry_transitorio():
    adapter = CommunityDiscoveryMarketplaceAdapter(
        resolvedor_ml=ResolvedorMlFake(),
        cliente_catalogo_ml=ClienteCatalogoMlErroFake(),
    )

    resultado = adapter.processar(descoberta("mercado_livre"))

    assert resultado.status == "retry"
    assert resultado.transitorio is True
    assert resultado.motivo == ("erro_api_catalogo_mercado_livre:" "api_mercado_livre_rate_limit")


def test_adapter_exige_item_previamente_reservado():
    adapter = CommunityDiscoveryMarketplaceAdapter()

    with pytest.raises(ValueError):
        adapter.processar(
            descoberta(
                "shopee",
                status="received",
            )
        )


def test_aliexpress_com_titulo_oficial_cria_oferta_link_only():
    processador = ProcessadorFake(
        resultado_resolucao=resolucao("aliexpress"),
        resultado_validacao=validacao(
            "aliexpress",
            status="nao_verificavel",
            motivo="mensagem_aliexpress_sem_preco_base",
            titulo="SSD NVMe AliExpress Oficial",
            preco=299.90,
        ),
    )
    construtor = ConstrutorFake()

    adapter = CommunityDiscoveryMarketplaceAdapter(
        processador_aliexpress=processador,
        construtor=construtor,
    )

    resultado = adapter.processar(
        descoberta("aliexpress"),
    )

    assert resultado.status == "oferta_criada"
    assert resultado.motivo == ("oferta_comunitaria_criada_com_preco_oficial")
    assert processador.resolver_chamadas == 1
    assert processador.validar_chamadas == 1
    assert construtor.chamadas == 1
