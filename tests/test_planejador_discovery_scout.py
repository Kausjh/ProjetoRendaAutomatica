from models.resolucao_scout import (
    ResolucaoScout,
)
from models.sinal_scout import SinalScout
from services.scout.planejador_discovery_scout import (
    PlanejadorDiscoveryScout,
)


def criar_sinal(
    titulo: str,
    *,
    id_externo: str = "1",
) -> SinalScout:
    return SinalScout(
        fonte="awin",
        id_externo=id_externo,
        tipo="voucher",
        titulo=titulo,
        url="https://exemplo.com/",
        descricao=titulo,
        termos="..",
        advertiser_id="1",
        advertiser_nome="Teste",
        codigo_voucher="TESTE",
        regioes=("BR",),
    )


def criar_resolucao(
    marketplace: str,
    *,
    status: str = "landing_page",
) -> ResolucaoScout:
    return ResolucaoScout(
        fonte="awin",
        id_externo="1",
        status=status,
        marketplace=marketplace,
        tipo_destino="campanha",
        motivo="teste",
    )


def test_aliexpress_cupom_br_vira_feed_curado():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("R$ 25 OFF em compras " "a partir de R$ 180 " "usando cupom BRFS2"),
        criar_resolucao("aliexpress"),
    )

    assert plano.utilizavel is True

    assert plano.estrategia == "feed_curado_aliexpress"

    assert plano.termos_busca == ()


def test_aliexpress_chile_e_ignorado():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("Cupons Chile"),
        criar_resolucao("aliexpress"),
    )

    assert plano.utilizavel is False
    assert plano.estrategia == "ignorar"

    assert plano.motivo == "campanha_regional_fora_br"


def test_kabum_extrai_playninja():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("10% de desconto em " "itens da linha PlayNinja."),
        criar_resolucao("kabum"),
    )

    assert plano.estrategia == "buscar_termos_kabum"

    assert plano.termos_busca == ("PlayNinja",)


def test_kabum_extrai_vga():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("8% de desconto exclusivo " "em produtos de VGA."),
        criar_resolucao("kabum"),
    )

    assert plano.termos_busca == ("VGA",)


def test_kabum_extrai_asrock():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("R$100 de desconto " "em produtos ASRock."),
        criar_resolucao("kabum"),
    )

    assert plano.termos_busca == ("ASRock",)


def test_kabum_extrai_jbl():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("25% OFF em produtos " "JBL selecionados"),
        criar_resolucao("kabum"),
    )

    assert plano.termos_busca == ("JBL",)


def test_kabum_extrai_shark():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("20% OFF em produtos " "Shark selecionados"),
        criar_resolucao("kabum"),
    )

    assert plano.termos_busca == ("Shark",)


def test_kabum_extrai_mesa_digitalizadora():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("10% OFF em mesas " "digitalizadoras e " "itens selecionados"),
        criar_resolucao("kabum"),
    )

    assert plano.estrategia == "buscar_termos_kabum"

    assert plano.termos_busca == ("mesas digitalizadoras",)


def test_kabum_generico_explora_landing():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("10% OFF em itens " "selecionados"),
        criar_resolucao("kabum"),
    )

    assert plano.estrategia == "explorar_landing_kabum"

    assert plano.termos_busca == ()


def test_kabum_titulo_truncado_explora_landing():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("R$50,00 OFF em"),
        criar_resolucao("kabum"),
    )

    assert plano.estrategia == "explorar_landing_kabum"


def test_resolucao_que_ja_e_produto_nao_entra_no_discovery():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("Produto qualquer"),
        criar_resolucao(
            "kabum",
            status="resolvido",
        ),
    )

    assert plano.utilizavel is False
    assert plano.estrategia == "ignorar"

    assert plano.motivo == "resolucao_nao_e_landing_page"


def test_marketplace_desconhecido_e_ignorado():
    plano = PlanejadorDiscoveryScout().planejar(
        criar_sinal("Campanha qualquer"),
        criar_resolucao("outro"),
    )

    assert plano.utilizavel is False
    assert plano.estrategia == "ignorar"
