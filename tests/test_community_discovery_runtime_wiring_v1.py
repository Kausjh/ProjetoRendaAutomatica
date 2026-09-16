from scrapers import registro_scrapers as registro


class CommunityFake:
    def __init__(self, *, max_descobertas_por_execucao):
        self.max_descobertas_por_execucao = max_descobertas_por_execucao


def _isolar_scrapers_base(monkeypatch):
    monkeypatch.setattr(registro, "MercadoLivreScraper", lambda: object())
    monkeypatch.setattr(registro, "ShopeeScraper", lambda: object())
    monkeypatch.setattr(registro, "KabumScraper", lambda: object())
    monkeypatch.setattr(registro, "AliExpressScraper", lambda: object())
    monkeypatch.setattr(registro, "CommunityDiscoveryScraper", CommunityFake)
    monkeypatch.delenv("SOCIAL_SCOUT_PIPELINE_ATIVO", raising=False)


def test_community_discovery_desativada_por_padrao(monkeypatch):
    _isolar_scrapers_base(monkeypatch)
    monkeypatch.delenv("COMMUNITY_DISCOVERY_PIPELINE_ATIVO", raising=False)

    scrapers = registro.criar_scrapers()

    assert len(scrapers) == 4
    assert not any(isinstance(item, CommunityFake) for item in scrapers)


def test_community_discovery_entra_no_pipeline_por_flag(monkeypatch):
    _isolar_scrapers_base(monkeypatch)
    monkeypatch.setenv("COMMUNITY_DISCOVERY_PIPELINE_ATIVO", "1")
    monkeypatch.setenv("COMMUNITY_DISCOVERY_MAX_POR_EXECUCAO", "7")

    scrapers = registro.criar_scrapers()

    community = [item for item in scrapers if isinstance(item, CommunityFake)]

    assert len(community) == 1
    assert community[0].max_descobertas_por_execucao == 7
