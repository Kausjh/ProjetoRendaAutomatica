# 63.8738, -149.7525

import inspect

from scrapers.social_scout_scraper import (
    SocialScoutScraper,
)


def test_v9_registra_aliexpress():
    fake = object()

    scraper = SocialScoutScraper(
        repository=object(),
        processamentos_repository=object(),
        detector=object(),
        resolvedor=object(),
        validador_preco=object(),
        processador_shopee=object(),
        processador_aliexpress=fake,
        construtor=object(),
    )

    assert scraper.VERSAO_PROCESSADOR == "9"
    assert scraper.processador_aliexpress is fake


def test_v9_dispatch_aliexpress():
    fonte = inspect.getsource(SocialScoutScraper.buscar_ofertas)

    assert 'deteccao.marketplace == "aliexpress"' in fonte

    assert "self.processador_aliexpress" in fonte
