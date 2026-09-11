from types import SimpleNamespace

from services.scout.proveniencia_publicacao_discovery_comercial_hunter import (
    GRANULARIDADE,
    ORIGEM,
    SCHEMA_VERSION,
    criar_proveniencias_publicacao_discovery_comercial_hunter,
)


def oferta(link: str):
    return SimpleNamespace(
        link=link,
    )


def candidato(
    link: str,
    *fontes: str,
):
    return SimpleNamespace(
        oferta=oferta(link),
        fontes=fontes,
    )


def resultado_hunter(
    *candidatos,
):
    return SimpleNamespace(
        candidatos=candidatos,
    )


def observabilidade(
    *alvos,
):
    return {"alvos": list(alvos)}


def alvo(
    fonte: str,
    *,
    aplicado: bool,
    termo: str = "produto teste",
):
    return {
        "fonte_hunter": fonte,
        "aplicado": aplicado,
        "termo_busca": termo,
    }


def test_sem_alvo_aplicado_nao_gera_proveniencia():
    resultado = criar_proveniencias_publicacao_discovery_comercial_hunter(
        observabilidade=observabilidade(
            alvo(
                "KabumScraper",
                aplicado=False,
            )
        ),
        resultado_hunter=resultado_hunter(
            candidato(
                "https://exemplo/1",
                "KabumScraper",
            )
        ),
        ofertas_selecionadas_fila=[oferta("https://exemplo/1")],
    )

    assert resultado == {}


def test_sem_resultado_hunter_nao_gera_proveniencia():
    resultado = criar_proveniencias_publicacao_discovery_comercial_hunter(
        observabilidade=observabilidade(
            alvo(
                "KabumScraper",
                aplicado=True,
            )
        ),
        resultado_hunter=None,
        ofertas_selecionadas_fila=[oferta("https://exemplo/1")],
    )

    assert resultado == {}


def test_oferta_selecionada_recebe_fonte_guiada():
    link = "https://exemplo/1"

    resultado = criar_proveniencias_publicacao_discovery_comercial_hunter(
        observabilidade=observabilidade(
            alvo(
                "KabumScraper",
                aplicado=True,
            )
        ),
        resultado_hunter=resultado_hunter(
            candidato(
                link,
                "KabumScraper",
            )
        ),
        ofertas_selecionadas_fila=[oferta(link)],
    )

    assert set(resultado) == {link}

    payload = resultado[link]

    assert payload["schema_version"] == SCHEMA_VERSION

    assert payload["origem"] == ORIGEM

    assert payload["granularidade"] == GRANULARIDADE

    assert payload["fontes_hunter_guiadas"] == ["KabumScraper"]


def test_fonte_nao_guiada_do_mesmo_candidato_nao_e_atribuida():
    link = "https://exemplo/1"

    resultado = criar_proveniencias_publicacao_discovery_comercial_hunter(
        observabilidade=observabilidade(
            alvo(
                "KabumScraper",
                aplicado=True,
            ),
            alvo(
                "OutroScraper",
                aplicado=False,
            ),
        ),
        resultado_hunter=resultado_hunter(
            candidato(
                link,
                "KabumScraper",
                "OutroScraper",
            )
        ),
        ofertas_selecionadas_fila=[oferta(link)],
    )

    assert resultado[link]["fontes_hunter_guiadas"] == ["KabumScraper"]


def test_multifonte_guiada_preserva_todas_as_fontes():
    link = "https://exemplo/1"

    resultado = criar_proveniencias_publicacao_discovery_comercial_hunter(
        observabilidade=observabilidade(
            alvo(
                "KabumScraper",
                aplicado=True,
            ),
            alvo(
                "AliExpressScraper",
                aplicado=True,
            ),
        ),
        resultado_hunter=resultado_hunter(
            candidato(
                link,
                "AliExpressScraper",
                "KabumScraper",
            )
        ),
        ofertas_selecionadas_fila=[oferta(link)],
    )

    assert resultado[link]["fontes_hunter_guiadas"] == [
        "AliExpressScraper",
        "KabumScraper",
    ]


def test_candidato_nao_selecionado_para_fila_nao_recebe_proveniencia():
    resultado = criar_proveniencias_publicacao_discovery_comercial_hunter(
        observabilidade=observabilidade(
            alvo(
                "KabumScraper",
                aplicado=True,
            )
        ),
        resultado_hunter=resultado_hunter(
            candidato(
                "https://exemplo/1",
                "KabumScraper",
            ),
            candidato(
                "https://exemplo/2",
                "KabumScraper",
            ),
        ),
        ofertas_selecionadas_fila=[oferta("https://exemplo/2")],
    )

    assert "https://exemplo/1" not in resultado

    assert "https://exemplo/2" in resultado


def test_payload_nao_finge_atribuicao_por_termo():
    link = "https://exemplo/1"

    resultado = criar_proveniencias_publicacao_discovery_comercial_hunter(
        observabilidade=observabilidade(
            alvo(
                "KabumScraper",
                aplicado=True,
                termo="Ryzen 9 9950X3D",
            )
        ),
        resultado_hunter=resultado_hunter(
            candidato(
                link,
                "KabumScraper",
            )
        ),
        ofertas_selecionadas_fila=[oferta(link)],
    )

    payload = resultado[link]

    assert payload["atribuicao_alvo_individual"] is False

    assert "termo_busca" not in payload

    assert "alvo" not in payload

    assert "termo" not in payload
