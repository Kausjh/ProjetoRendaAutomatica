# 63.8738, -149.7525

import scrapers.registro_scrapers as registro


class ScraperFake:
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.args = args
        self.kwargs = kwargs


class SocialFake:
    instancias = []

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.args = args
        self.kwargs = kwargs

        self.__class__.instancias.append(self)


def preparar(
    monkeypatch,
    *,
    limite=None,
):
    SocialFake.instancias.clear()

    monkeypatch.setattr(
        registro,
        "MercadoLivreScraper",
        ScraperFake,
    )

    monkeypatch.setattr(
        registro,
        "ShopeeScraper",
        ScraperFake,
    )

    monkeypatch.setattr(
        registro,
        "KabumScraper",
        ScraperFake,
    )

    monkeypatch.setattr(
        registro,
        "AliExpressScraper",
        ScraperFake,
    )

    monkeypatch.setattr(
        registro,
        "SocialScoutScraper",
        SocialFake,
    )

    monkeypatch.setenv(
        "SOCIAL_SCOUT_PIPELINE_ATIVO",
        "true",
    )

    monkeypatch.setenv(
        "SOCIAL_SCOUT_MODO_SOMBRA",
        "true",
    )

    if limite is None:
        monkeypatch.delenv(
            "SOCIAL_SCOUT_MAX_MENSAGENS_POR_EXECUCAO",
            raising=False,
        )

    else:
        monkeypatch.setenv(
            "SOCIAL_SCOUT_MAX_MENSAGENS_POR_EXECUCAO",
            str(limite),
        )


def social():
    assert len(SocialFake.instancias) == 1

    return SocialFake.instancias[0]


def test_default_canary_e_cinco(
    monkeypatch,
):
    preparar(monkeypatch)

    registro.criar_scrapers()

    assert social().kwargs["max_mensagens_por_execucao"] == 5


def test_shadow_continua_true(
    monkeypatch,
):
    preparar(monkeypatch)

    registro.criar_scrapers()

    assert social().kwargs["modo_sombra"] is True


def test_env_customizado(
    monkeypatch,
):
    preparar(
        monkeypatch,
        limite=7,
    )

    registro.criar_scrapers()

    assert social().kwargs["max_mensagens_por_execucao"] == 7


def test_env_invalido_retorna_default(
    monkeypatch,
):
    preparar(
        monkeypatch,
        limite="banana",
    )

    registro.criar_scrapers()

    assert social().kwargs["max_mensagens_por_execucao"] == 5


def test_zero_retorna_default(
    monkeypatch,
):
    preparar(
        monkeypatch,
        limite=0,
    )

    registro.criar_scrapers()

    assert social().kwargs["max_mensagens_por_execucao"] == 5


def test_env_example_documenta_canary():
    texto = open(
        ".env.example",
        encoding="utf-8",
    ).read()

    assert "SOCIAL_SCOUT_MAX_MENSAGENS_POR_EXECUCAO=5" in texto
