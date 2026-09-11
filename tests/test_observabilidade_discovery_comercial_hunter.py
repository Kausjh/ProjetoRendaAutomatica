from models.alvo_discovery_comercial_hunter import (
    AlvoDiscoveryComercialHunter,
    ResultadoAlvosDiscoveryComercialHunter,
)
from scrapers.kabum_scraper import KabumScraper
from services.scout.observabilidade_discovery_comercial_hunter import (
    criar_observabilidade_discovery_comercial_hunter,
)


def _alvo(
    *,
    fonte: str = "KabumScraper",
    marketplace: str = "kabum",
    estrategia: str = "buscar_termos_kabum",
    termo: str | None = "Ryzen 9 9950X3D",
    sinais: int = 4,
):
    return AlvoDiscoveryComercialHunter(
        fonte_hunter=fonte,
        marketplace=marketplace,
        estrategia=estrategia,
        termo_busca=termo,
        direcao="alta",
        sinais_distintos=sinais,
        motivo="rota_comercial_temporalmente_madura",
        evidencias=(
            "qualidade_temporal:aprovada",
            "ambas_metades_tem_sinais",
        ),
    )


def test_sem_alvos_expoe_estado_neutro():
    resultado = ResultadoAlvosDiscoveryComercialHunter(
        alvos=(),
    )

    observabilidade = criar_observabilidade_discovery_comercial_hunter(
        resultado=resultado,
        scrapers=(),
    )

    assert observabilidade == {
        "schema_version": 1,
        "status": "sem_alvos_maduros",
        "motivo_status": "nenhum_alvo_comercial_maduro",
        "alvos_total": 0,
        "alvos_aplicados": 0,
        "fontes_hunter": [],
        "alvos": [],
    }


def test_kabum_confirma_termo_priorizado_no_runtime():
    termo = "Ryzen 9 9950X3D"
    alvo = _alvo(termo=termo)

    kabum = KabumScraper()
    kabum.priorizar_termos_discovery(
        [termo],
        maximo=5,
    )

    observabilidade = criar_observabilidade_discovery_comercial_hunter(
        resultado=ResultadoAlvosDiscoveryComercialHunter(
            alvos=(alvo,),
        ),
        scrapers=(kabum,),
    )

    item = observabilidade["alvos"][0]

    assert observabilidade["status"] == "aplicado"
    assert observabilidade["alvos_total"] == 1
    assert observabilidade["alvos_aplicados"] == 1
    assert item["termo_busca"] == termo
    assert item["aplicado"] is True
    assert item["motivo_aplicacao"] == "termo_priorizado_kabum"
    assert item["posicao_runtime"] == 1
    assert item["sinais_distintos"] == 4


def test_kabum_expoe_alvo_fora_do_limite_de_cinco_prioridades():
    alvos = tuple(
        _alvo(
            termo=f"Termo Comercial {indice}",
            sinais=10 - indice,
        )
        for indice in range(1, 7)
    )

    kabum = KabumScraper()
    kabum.priorizar_termos_discovery(
        [alvo.termo_busca for alvo in alvos if alvo.termo_busca],
        maximo=5,
    )

    observabilidade = criar_observabilidade_discovery_comercial_hunter(
        resultado=ResultadoAlvosDiscoveryComercialHunter(
            alvos=alvos,
        ),
        scrapers=(kabum,),
    )

    assert observabilidade["status"] == "aplicado_parcialmente"
    assert observabilidade["alvos_aplicados"] == 5
    assert observabilidade["alvos"][5]["aplicado"] is False
    assert observabilidade["alvos"][5]["motivo_aplicacao"] == "fora_limite_priorizacao_kabum"


def test_aliexpress_confirma_rota_nativa_sem_termo():
    AliExpressFake = type(
        "AliExpressScraper",
        (),
        {},
    )

    alvo = _alvo(
        fonte="AliExpressScraper",
        marketplace="aliexpress",
        estrategia="feed_curado_aliexpress",
        termo=None,
    )

    observabilidade = criar_observabilidade_discovery_comercial_hunter(
        resultado=ResultadoAlvosDiscoveryComercialHunter(
            alvos=(alvo,),
        ),
        scrapers=(AliExpressFake(),),
    )

    item = observabilidade["alvos"][0]

    assert item["aplicado"] is True
    assert item["motivo_aplicacao"] == "rota_feed_curado_nativa_ativa"
    assert item["posicao_runtime"] is None


def test_fonte_ausente_fica_visivel_no_relatorio():
    alvo = _alvo()

    observabilidade = criar_observabilidade_discovery_comercial_hunter(
        resultado=ResultadoAlvosDiscoveryComercialHunter(
            alvos=(alvo,),
        ),
        scrapers=(),
    )

    item = observabilidade["alvos"][0]

    assert observabilidade["status"] == "nao_aplicado"
    assert observabilidade["alvos_aplicados"] == 0
    assert item["aplicado"] is False
    assert item["motivo_aplicacao"] == "fonte_hunter_nao_configurada"
