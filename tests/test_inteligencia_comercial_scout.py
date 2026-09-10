import pytest

from models.plano_discovery_scout import (
    PlanoDiscoveryScout,
)
from models.resolucao_scout import ResolucaoScout
from models.sinal_scout import SinalScout
from services.scout.inteligencia_comercial_scout import (
    InteligenciaComercialScout,
)


def criar_sinal(
    **alteracoes,
):
    dados = {
        "fonte": "awin",
        "id_externo": "promo-1",
        "tipo": "promotion",
        "titulo": "Campanha Gamer",
        "url": "https://exemplo.com/campanha",
        "advertiser_id": "123",
        "advertiser_nome": "Parceiro Teste",
        "descricao": "Promocao de hardware",
        "termos": "Linha Ryzen",
        "url_tracking": None,
        "codigo_voucher": "GAMER10",
        "inicio": "2026-09-10",
        "fim": "2026-09-12",
        "regioes": (
            "br",
            "BR",
        ),
    }

    dados.update(alteracoes)

    return SinalScout(**dados)


def criar_resolucao(
    **alteracoes,
):
    dados = {
        "fonte": "awin",
        "id_externo": "promo-1",
        "status": "landing_page",
        "marketplace": "kabum",
        "tipo_destino": "campanha",
        "url_destino": "https://www.kabum.com.br/",
        "id_produto": None,
        "http_status": 200,
        "motivo": "teste",
    }

    dados.update(alteracoes)

    return ResolucaoScout(**dados)


def criar_plano(
    **alteracoes,
):
    dados = {
        "fonte": "awin",
        "id_externo": "promo-1",
        "marketplace": "kabum",
        "estrategia": "buscar_termos_kabum",
        "termos_busca": (
            "Ryzen",
            "ryzen",
            "SSD NVMe",
        ),
        "utilizavel": True,
        "motivo": "teste",
    }

    dados.update(alteracoes)

    return PlanoDiscoveryScout(**dados)


def analisar(
    sinal=None,
    resolucao=None,
    plano=None,
):
    return InteligenciaComercialScout().analisar(
        sinal=(sinal or criar_sinal()),
        resolucao=(criar_resolucao() if resolucao is None else resolucao),
        plano=(criar_plano() if plano is None else plano),
    )


def test_perfil_comercial_estrutura_sinal_rico():
    perfil = analisar()

    assert perfil.marketplace == "kabum"
    assert perfil.tipo_destino == "campanha"

    assert perfil.parceiro_id == "123"
    assert perfil.parceiro_nome == "Parceiro Teste"

    assert perfil.codigo_voucher == "GAMER10"

    assert perfil.regioes == ("BR",)

    assert perfil.termos_descoberta == (
        "Ryzen",
        "SSD NVMe",
    )

    assert perfil.landing_page is True

    assert perfil.utilizavel_discovery is True

    assert perfil.dimensoes == (
        "campanha",
        "cupom",
        "parceiro",
        "termos_discovery",
        "janela_temporal",
        "regional",
        "landing_page",
    )


def test_tipo_voucher_sem_codigo_nao_inventa_cupom():
    perfil = analisar(
        sinal=criar_sinal(
            tipo="voucher",
            codigo_voucher=None,
        )
    )

    assert "campanha" in perfil.dimensoes
    assert "cupom" not in perfil.dimensoes
    assert perfil.codigo_voucher is None


def test_codigo_voucher_preserva_valor_original():
    perfil = analisar(
        sinal=criar_sinal(
            codigo_voucher="GaMeR-15",
        )
    )

    assert perfil.codigo_voucher == "GaMeR-15"


def test_termos_discovery_sao_deduplicados_sem_perder_ordem():
    perfil = analisar(
        plano=criar_plano(
            termos_busca=(
                "Ryzen",
                "  RYZEN ",
                "SSD",
                "",
                "ssd",
            )
        )
    )

    assert perfil.termos_descoberta == (
        "Ryzen",
        "SSD",
    )


def test_regioes_sao_normalizadas_e_deduplicadas():
    perfil = analisar(
        sinal=criar_sinal(
            regioes=(
                "br",
                " BR ",
                "us",
                "",
                "US",
            )
        )
    )

    assert perfil.regioes == (
        "BR",
        "US",
    )


def test_produto_resolvido_sem_plano_continua_sendo_perfil_comercial():
    perfil = InteligenciaComercialScout().analisar(
        sinal=criar_sinal(),
        resolucao=criar_resolucao(
            status="resolvido",
            tipo_destino="produto",
        ),
        plano=None,
    )

    assert perfil.marketplace == "kabum"
    assert perfil.tipo_destino == "produto"

    assert perfil.landing_page is False

    assert perfil.utilizavel_discovery is False

    assert perfil.estrategia_discovery is None


def test_rejeita_resolucao_de_outro_sinal():
    with pytest.raises(
        ValueError,
        match="Identidade inconsistente",
    ):
        InteligenciaComercialScout().analisar(
            sinal=criar_sinal(),
            resolucao=criar_resolucao(
                id_externo="outra-promocao",
            ),
            plano=None,
        )


def test_rejeita_plano_de_outro_sinal():
    with pytest.raises(
        ValueError,
        match="Identidade inconsistente",
    ):
        InteligenciaComercialScout().analisar(
            sinal=criar_sinal(),
            resolucao=criar_resolucao(),
            plano=criar_plano(
                fonte="outra_fonte",
            ),
        )


def test_v1_nao_inventa_seller_nem_tendencia():
    perfil = analisar()

    assert "seller" not in perfil.dimensoes
    assert "tendencia" not in perfil.dimensoes

    assert not hasattr(
        perfil,
        "preco",
    )

    assert not hasattr(
        perfil,
        "preco_efetivo",
    )
