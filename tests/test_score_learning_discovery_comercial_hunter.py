import pytest

from services.scout.score_learning_discovery_comercial_hunter import (
    criar_score_learning_discovery_comercial_hunter,
)


def _fonte(
    *,
    nome="KabumScraper",
    execucoes=2,
    sucessos=2,
    falhas=0,
    erros=0,
    coletadas=20,
    novas=10,
    elegiveis=5,
    selecionadas=2,
    publicacoes=0,
):
    return {
        "fonte_hunter": nome,
        "execucoes_guiadas": execucoes,
        "execucoes_sucesso": sucessos,
        "execucoes_falha": falhas,
        "execucoes_com_erro": erros,
        "quantidade_coletada": coletadas,
        "quantidade_novas": novas,
        "quantidade_duplicadas": (
            max(
                0,
                coletadas - novas,
            )
        ),
        "elegiveis_atribuidas": elegiveis,
        "selecionadas_fila_atribuidas": (selecionadas),
        "publicacoes_atribuidas": (publicacoes),
    }


def _janela(
    *,
    maduras=(),
    recentes=(),
):
    return {
        "schema_version": 1,
        "status": ("evidencia_madura_disponivel"),
        "dataset_maduro": {
            "schema_version": 1,
            "status": "observado",
            "fontes": list(maduras),
        },
        "dataset_recente": {
            "schema_version": 1,
            "status": "observado",
            "fontes": list(recentes),
        },
    }


def _resultado_fonte(
    resultado,
    nome="KabumScraper",
):
    return next(item for item in resultado["fontes"] if item["fonte_hunter"] == nome)


def test_exige_mapping():
    with pytest.raises(TypeError):
        criar_score_learning_discovery_comercial_hunter(janela_learning=None)


def test_sem_dataset_maduro():
    resultado = criar_score_learning_discovery_comercial_hunter(janela_learning={})

    assert resultado["status"] == "sem_dataset_maduro"

    assert resultado["fontes"] == []


def test_score_exato_da_formula():
    resultado = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(maduras=[_fonte()])
    )

    fonte = _resultado_fonte(resultado)

    # novidade:
    # 10 / 20 = 50%
    #
    # elegibilidade:
    # 5 / 10 = 50%
    #
    # selecao:
    # 2 / 5 = 40%
    #
    # confiabilidade:
    # 2 / 2 = 100%
    #
    # score:
    # 50*0.25 +
    # 50*0.30 +
    # 40*0.25 +
    # 100*0.20
    # = 57.50

    assert fonte["score_learning"] == 57.5


def test_score_fica_entre_zero_e_cem():
    resultado = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(
            maduras=[
                _fonte(
                    execucoes=1,
                    sucessos=99,
                    coletadas=1,
                    novas=99,
                    elegiveis=99,
                    selecionadas=99,
                )
            ]
        )
    )

    score = _resultado_fonte(resultado)["score_learning"]

    assert score == 100.0


def test_publicacao_nao_altera_score():
    sem_publicacao = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(maduras=[_fonte(publicacoes=0)])
    )

    com_publicacao = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(maduras=[_fonte(publicacoes=20)])
    )

    score_sem = _resultado_fonte(sem_publicacao)["score_learning"]

    fonte_com = _resultado_fonte(com_publicacao)

    assert fonte_com["score_learning"] == score_sem

    assert fonte_com["evidencia_publicacao"]["publicacoes_atribuidas"] == 20

    assert fonte_com["evidencia_publicacao"]["entra_no_score"] is False


def test_dataset_recente_nao_contamina_score():
    resultado = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(
            maduras=[_fonte(nome="KabumScraper")],
            recentes=[
                _fonte(
                    nome="AliExpressScraper",
                    execucoes=100,
                    sucessos=100,
                    coletadas=1000,
                    novas=1000,
                    elegiveis=1000,
                    selecionadas=1000,
                )
            ],
        )
    )

    nomes = {item["fonte_hunter"] for item in resultado["fontes"]}

    assert nomes == {"KabumScraper"}


def test_sem_execucao_nao_calcula_score():
    resultado = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(
            maduras=[
                _fonte(
                    execucoes=0,
                    sucessos=0,
                )
            ]
        )
    )

    fonte = _resultado_fonte(resultado)

    assert fonte["score_calculavel"] is False

    assert fonte["score_learning"] is None

    assert fonte["motivo_sem_score"] == "sem_execucoes_guiadas_maduras"


def test_sem_coleta_nao_calcula_score():
    resultado = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(
            maduras=[
                _fonte(
                    coletadas=0,
                    novas=0,
                    elegiveis=0,
                    selecionadas=0,
                )
            ]
        )
    )

    fonte = _resultado_fonte(resultado)

    assert fonte["score_learning"] is None

    assert fonte["motivo_sem_score"] == "sem_coleta_madura"


@pytest.mark.parametrize(
    (
        "execucoes",
        "coletadas",
        "esperada",
    ),
    [
        (
            1,
            5,
            "muito_baixa",
        ),
        (
            2,
            10,
            "baixa",
        ),
        (
            4,
            30,
            "media",
        ),
        (
            8,
            80,
            "alta",
        ),
    ],
)
def test_confianca_depende_da_amostra(
    execucoes,
    coletadas,
    esperada,
):
    resultado = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(
            maduras=[
                _fonte(
                    execucoes=execucoes,
                    sucessos=execucoes,
                    coletadas=coletadas,
                    novas=coletadas,
                    elegiveis=coletadas,
                    selecionadas=coletadas,
                )
            ]
        )
    )

    assert _resultado_fonte(resultado)["confianca"] == esperada


def test_falha_reduz_componente_confiabilidade():
    resultado = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(
            maduras=[
                _fonte(
                    execucoes=2,
                    sucessos=1,
                    falhas=1,
                )
            ]
        )
    )

    fonte = _resultado_fonte(resultado)

    assert fonte["componentes"]["confiabilidade_execucao"]["valor_percentual"] == 50.0


def test_fontes_sao_ordenadas_por_score():
    resultado = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(
            maduras=[
                _fonte(
                    nome="FonteFraca",
                    novas=2,
                    elegiveis=1,
                    selecionadas=0,
                ),
                _fonte(
                    nome="FonteForte",
                    novas=20,
                    elegiveis=20,
                    selecionadas=20,
                    coletadas=20,
                ),
            ]
        )
    )

    assert resultado["fontes"][0]["fonte_hunter"] == "FonteForte"


def test_score_e_observacional():
    resultado = criar_score_learning_discovery_comercial_hunter(
        janela_learning=_janela(maduras=[_fonte()])
    )

    assert resultado["score_observacional"] is True

    assert resultado["somente_dataset_maduro"] is True

    assert resultado["influencia_priorizacao"] is False

    assert resultado["publicacao_entra_no_score"] is False


def test_pesos_somam_um():
    resultado = criar_score_learning_discovery_comercial_hunter(janela_learning=_janela())

    assert sum(resultado["pesos"].values()) == pytest.approx(1.0)
