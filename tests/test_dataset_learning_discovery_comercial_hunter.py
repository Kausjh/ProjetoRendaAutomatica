from services.scout.dataset_learning_discovery_comercial_hunter import (
    criar_dataset_learning_discovery_comercial_hunter,
)


def _outcome_fonte(
    fonte,
    *,
    limite=10,
    coletadas=0,
    novas=0,
    duplicadas=0,
    elegiveis=0,
    selecionadas=0,
    sucesso=True,
    erro=None,
):
    return {
        "fonte_hunter": fonte,
        "limite_solicitado": limite,
        "quantidade_coletada": coletadas,
        "quantidade_novas": novas,
        "quantidade_duplicadas": duplicadas,
        "elegiveis_atribuidas": elegiveis,
        "selecionadas_fila_atribuidas": selecionadas,
        "sucesso": sucesso,
        "erro": erro,
    }


def _relatorio(
    *fontes,
    alvos_aplicados=1,
):
    return {
        "data_hora": ("2026-09-11 18:00:00"),
        "commercial_discovery_outcome": {
            "schema_version": 1,
            "status": "observado",
            "alvos_aplicados": (alvos_aplicados),
            "fontes": list(fontes),
        },
    }


def _proveniencia(
    *fontes,
):
    return {
        "schema_version": 1,
        "origem": ("commercial_discovery_hunter"),
        "granularidade": ("fonte_hunter"),
        "atribuicao_alvo_individual": False,
        "fontes_hunter_guiadas": list(fontes),
    }


def _publicacao(
    *fontes,
):
    return {
        "link": ("https://exemplo/item"),
        "publicado_em": ("2026-09-11T18:30:00-03:00"),
        "proveniencia_discovery_comercial": (_proveniencia(*fontes) if fontes else None),
    }


def _fonte(
    dataset,
    nome,
):
    return next(item for item in dataset["fontes"] if item["fonte_hunter"] == nome)


def test_sem_evidencias():
    dataset = criar_dataset_learning_discovery_comercial_hunter()

    assert dataset["status"] == "sem_evidencias"

    assert dataset["fontes"] == []


def test_agrega_execucao_de_uma_fonte():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=[
            _relatorio(
                _outcome_fonte(
                    "KabumScraper",
                    coletadas=10,
                    novas=8,
                    duplicadas=2,
                    elegiveis=4,
                    selecionadas=2,
                )
            )
        ]
    )

    kabum = _fonte(
        dataset,
        "KabumScraper",
    )

    assert kabum["execucoes_guiadas"] == 1

    assert kabum["quantidade_coletada"] == 10

    assert kabum["quantidade_novas"] == 8

    assert kabum["elegiveis_atribuidas"] == 4

    assert kabum["selecionadas_fila_atribuidas"] == 2


def test_agrega_multiplos_ciclos_da_mesma_fonte():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=[
            _relatorio(
                _outcome_fonte(
                    "KabumScraper",
                    coletadas=10,
                    novas=6,
                    elegiveis=3,
                    selecionadas=1,
                )
            ),
            _relatorio(
                _outcome_fonte(
                    "KabumScraper",
                    coletadas=20,
                    novas=10,
                    elegiveis=5,
                    selecionadas=2,
                )
            ),
        ]
    )

    kabum = _fonte(
        dataset,
        "KabumScraper",
    )

    assert kabum["execucoes_guiadas"] == 2

    assert kabum["quantidade_coletada"] == 30

    assert kabum["quantidade_novas"] == 16

    assert kabum["elegiveis_atribuidas"] == 8

    assert kabum["selecionadas_fila_atribuidas"] == 3


def test_calcula_taxas_deterministicas_intermediarias():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=[
            _relatorio(
                _outcome_fonte(
                    "KabumScraper",
                    coletadas=20,
                    novas=10,
                    elegiveis=5,
                    selecionadas=2,
                )
            )
        ]
    )

    kabum = _fonte(
        dataset,
        "KabumScraper",
    )

    assert kabum["taxa_novas_sobre_coletadas_percentual"] == 50.0

    assert kabum["taxa_elegibilidade_sobre_novas_percentual"] == 50.0

    assert kabum["taxa_selecao_sobre_elegiveis_percentual"] == 40.0


def test_publicacao_real_e_creditada_a_fonte():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio(_outcome_fonte("KabumScraper"))],
        historico_publicacoes=[_publicacao("KabumScraper")],
    )

    kabum = _fonte(
        dataset,
        "KabumScraper",
    )

    assert kabum["publicacoes_atribuidas"] == 1

    assert dataset["publicacoes_atribuidas_discovery"] == 1


def test_publicacao_multifonte_credita_ambas_sem_duplicar_evento():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        historico_publicacoes=[
            _publicacao(
                "KabumScraper",
                "AliExpressScraper",
            )
        ]
    )

    assert dataset["publicacoes_atribuidas_discovery"] == 1

    assert dataset["eventos_multifonte"] == 1

    assert (
        _fonte(
            dataset,
            "KabumScraper",
        )["publicacoes_atribuidas"]
        == 1
    )

    assert (
        _fonte(
            dataset,
            "AliExpressScraper",
        )["publicacoes_atribuidas"]
        == 1
    )


def test_publicacao_sem_execucao_observada_e_preservada():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        historico_publicacoes=[_publicacao("KabumScraper")]
    )

    kabum = _fonte(
        dataset,
        "KabumScraper",
    )

    assert kabum["execucoes_guiadas"] == 0

    assert kabum["publicacoes_atribuidas"] == 1

    assert kabum["publicacao_sem_execucao_observada"] is True


def test_nao_calcula_taxa_publicacao():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=[
            _relatorio(
                _outcome_fonte(
                    "KabumScraper",
                    selecionadas=5,
                )
            )
        ],
        historico_publicacoes=[_publicacao("KabumScraper")],
    )

    kabum = _fonte(
        dataset,
        "KabumScraper",
    )

    assert dataset["taxa_publicacao_nao_calculada"] is True

    assert dataset["publicacao_assincrona"] is True

    assert "taxa_publicacao_percentual" not in kabum


def test_registros_antigos_sem_outcome_sao_tolerados():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=[
            {"data_hora": ("2026-09-10 10:00:00")},
            _relatorio(_outcome_fonte("KabumScraper")),
        ]
    )

    assert dataset["relatorios_observados"] == 2

    assert dataset["ciclos_com_outcome"] == 1

    assert dataset["ciclos_sem_outcome"] == 1


def test_proveniencia_invalida_nao_e_atribuida():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        historico_publicacoes=[
            {
                "proveniencia_discovery_comercial": {
                    "origem": ("outra_origem"),
                    "granularidade": ("fonte_hunter"),
                    "fontes_hunter_guiadas": ["KabumScraper"],
                }
            }
        ]
    )

    assert dataset["publicacoes_observadas"] == 1

    assert dataset["publicacoes_atribuidas_discovery"] == 0

    assert dataset["publicacoes_sem_proveniencia_discovery"] == 1


def test_nao_finge_atribuicao_por_termo_ou_alvo():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio(_outcome_fonte("KabumScraper"))]
    )

    assert dataset["granularidade"] == "fonte_hunter"

    assert dataset["atribuicao_alvo_individual"] is False

    assert "termo_busca" not in dataset

    assert "alvo" not in dataset


def test_valores_invalidos_nao_geram_contagens_negativas():
    dataset = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=[
            _relatorio(
                _outcome_fonte(
                    "KabumScraper",
                    coletadas=-5,
                    novas="invalido",
                    elegiveis=None,
                    selecionadas=-1,
                )
            )
        ]
    )

    kabum = _fonte(
        dataset,
        "KabumScraper",
    )

    assert kabum["quantidade_coletada"] == 0

    assert kabum["quantidade_novas"] == 0

    assert kabum["selecionadas_fila_atribuidas"] == 0
