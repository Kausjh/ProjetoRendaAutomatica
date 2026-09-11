import pytest

from models.alvo_discovery_comercial_hunter import (
    AlvoDiscoveryComercialHunter,
)
from scrapers.kabum_scraper import KabumScraper
from scrapers.registro_scrapers import criar_scrapers


@pytest.fixture(autouse=True)
def _configurar_awin_para_testes(
    monkeypatch,
):
    monkeypatch.setenv(
        "AWIN_PRODUCT_FEED_API_KEY",
        "chave-ficticia-apenas-para-teste",
    )


def _alvo_kabum(
    termo: str,
) -> AlvoDiscoveryComercialHunter:
    return AlvoDiscoveryComercialHunter(
        fonte_hunter="KabumScraper",
        marketplace="kabum",
        estrategia="buscar_termos_kabum",
        termo_busca=termo,
        direcao="alta",
        sinais_distintos=4,
        motivo="rota_comercial_temporalmente_madura",
        evidencias=(
            "qualidade_temporal:aprovada",
            "ambas_metades_tem_sinais",
        ),
    )


def test_kabum_prioriza_termo_sem_aumentar_quantidade_total():
    scraper = KabumScraper()

    quantidade_original = len(scraper.termos_busca)

    aplicados = scraper.priorizar_termos_discovery(
        [
            "Threadripper 9980X",
            "threadripper 9980x",
        ]
    )

    assert aplicados == ("Threadripper 9980X",)
    assert scraper.termos_busca[0] == "Threadripper 9980X"
    assert len(scraper.termos_busca) == quantidade_original

    normalizados = [termo.casefold() for termo in scraper.termos_busca]

    assert len(normalizados) == len(set(normalizados))


def test_registro_entrega_kabum_ja_orientado_pelo_alvo():
    termo = "Threadripper 9980X"

    scrapers = criar_scrapers(alvos_discovery_comercial=(_alvo_kabum(termo),))

    kabum = next(scraper for scraper in scrapers if isinstance(scraper, KabumScraper))

    assert kabum.termos_busca[0] == termo
    assert len(kabum.termos_busca) == len(KabumScraper.TERMOS_PADRAO)


def test_registro_sem_alvo_preserva_ordem_padrao_kabum():
    scrapers = criar_scrapers()

    kabum = next(scraper for scraper in scrapers if isinstance(scraper, KabumScraper))

    assert kabum.termos_busca == KabumScraper.TERMOS_PADRAO
