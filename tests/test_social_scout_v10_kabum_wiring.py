# 63.8738, -149.7525

import inspect

from scrapers.social_scout_scraper import (
    SocialScoutScraper,
)
from services.scout.detector_promocao_social_scout import (
    DetectorPromocaoSocialScout,
)


def test_v10_registra_processador_kabum():
    fake = object()

    scraper = SocialScoutScraper(
        repository=object(),
        processamentos_repository=object(),
        detector=object(),
        resolvedor=object(),
        validador_preco=object(),
        processador_shopee=object(),
        processador_aliexpress=object(),
        processador_kabum=fake,
        construtor=object(),
    )

    assert scraper.VERSAO_PROCESSADOR == "10"

    assert scraper.processador_kabum is fake


def test_v10_bootstrap_tiddly_antes_do_gate():
    fonte = inspect.getsource(SocialScoutScraper.buscar_ofertas)

    assert "resolucao_previa = None" in fonte

    assert "tem_link_tiddly" in fonte

    assert 'marketplace="kabum"' in fonte

    assert 'deteccao.marketplace == "kabum"' in fonte

    assert "resolucao = resolucao_previa" in fonte


def test_detector_nao_hardcoda_tiddly_como_kabum():
    fonte = inspect.getsource(DetectorPromocaoSocialScout)

    assert "tidd.ly" not in fonte
