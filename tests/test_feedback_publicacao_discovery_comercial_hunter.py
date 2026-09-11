from services.scout.feedback_publicacao_discovery_comercial_hunter import (
    GRANULARIDADE,
    ORIGEM,
    SCHEMA_VERSION,
    criar_feedback_publicacao_discovery_comercial_hunter,
)


def proveniencia(
    *fontes: str,
):
    return {
        "schema_version": 1,
        "origem": ORIGEM,
        "granularidade": GRANULARIDADE,
        "atribuicao_alvo_individual": False,
        "fontes_hunter_guiadas": list(fontes),
    }


def publicacao(
    *,
    fontes=(),
):
    registro = {
        "link": "https://exemplo/item",
        "publicado_em": ("2026-09-11T18:00:00-03:00"),
    }

    if fontes is not None:
        registro["proveniencia_discovery_comercial"] = proveniencia(*fontes)

    return registro


def test_sem_publicacoes():
    resultado = criar_feedback_publicacao_discovery_comercial_hunter()

    assert resultado["schema_version"] == SCHEMA_VERSION

    assert resultado["status"] == "sem_publicacoes_observadas"

    assert resultado["publicacoes_observadas"] == 0

    assert resultado["publicacoes_atribuidas_discovery"] == 0

    assert resultado["fontes"] == []


def test_publicacao_sem_proveniencia_nao_e_atribuida():
    resultado = criar_feedback_publicacao_discovery_comercial_hunter(
        historico_publicacoes=[publicacao(fontes=None)]
    )

    assert resultado["status"] == "sem_publicacoes_atribuidas"

    assert resultado["publicacoes_observadas"] == 1

    assert resultado["publicacoes_sem_proveniencia_discovery"] == 1


def test_publicacao_kabum_e_atribuida():
    resultado = criar_feedback_publicacao_discovery_comercial_hunter(
        historico_publicacoes=[publicacao(fontes=["KabumScraper"])]
    )

    assert resultado["status"] == "observado"

    assert resultado["publicacoes_atribuidas_discovery"] == 1

    assert resultado["fontes"] == [
        {
            "fonte_hunter": ("KabumScraper"),
            "publicacoes_atribuidas": 1,
        }
    ]


def test_duas_publicacoes_mesma_fonte_somam():
    resultado = criar_feedback_publicacao_discovery_comercial_hunter(
        historico_publicacoes=[
            publicacao(fontes=["KabumScraper"]),
            publicacao(fontes=["KabumScraper"]),
        ]
    )

    assert resultado["publicacoes_atribuidas_discovery"] == 2

    assert resultado["fontes"][0]["publicacoes_atribuidas"] == 2


def test_multifonte_credita_evento_para_ambas():
    resultado = criar_feedback_publicacao_discovery_comercial_hunter(
        historico_publicacoes=[
            publicacao(
                fontes=[
                    "KabumScraper",
                    "AliExpressScraper",
                ]
            )
        ]
    )

    assert resultado["publicacoes_atribuidas_discovery"] == 1

    assert resultado["eventos_multifonte"] == 1

    assert resultado["fontes"] == [
        {
            "fonte_hunter": ("AliExpressScraper"),
            "publicacoes_atribuidas": 1,
        },
        {
            "fonte_hunter": ("KabumScraper"),
            "publicacoes_atribuidas": 1,
        },
    ]


def test_fontes_duplicadas_no_mesmo_evento_nao_duplicam_credito():
    resultado = criar_feedback_publicacao_discovery_comercial_hunter(
        historico_publicacoes=[
            publicacao(
                fontes=[
                    "KabumScraper",
                    "KabumScraper",
                ]
            )
        ]
    )

    assert resultado["publicacoes_atribuidas_discovery"] == 1

    assert resultado["fontes"][0]["publicacoes_atribuidas"] == 1


def test_proveniencia_de_outra_origem_nao_e_creditada():
    registro = publicacao(fontes=None)

    registro["proveniencia_discovery_comercial"] = {
        "origem": "outra_origem",
        "granularidade": ("fonte_hunter"),
        "fontes_hunter_guiadas": ["KabumScraper"],
    }

    resultado = criar_feedback_publicacao_discovery_comercial_hunter(
        historico_publicacoes=[registro]
    )

    assert resultado["publicacoes_atribuidas_discovery"] == 0


def test_nao_finge_atribuicao_por_termo():
    resultado = criar_feedback_publicacao_discovery_comercial_hunter(
        historico_publicacoes=[publicacao(fontes=["KabumScraper"])]
    )

    assert resultado["granularidade"] == "fonte_hunter"

    assert resultado["atribuicao_alvo_individual"] is False

    assert "termo_busca" not in resultado

    assert "alvo" not in resultado


def test_registros_invalidos_sao_ignorados():
    resultado = criar_feedback_publicacao_discovery_comercial_hunter(
        historico_publicacoes=[
            None,
            "invalido",
            123,
            publicacao(fontes=["KabumScraper"]),
        ]
    )

    assert resultado["publicacoes_observadas"] == 1

    assert resultado["publicacoes_atribuidas_discovery"] == 1
