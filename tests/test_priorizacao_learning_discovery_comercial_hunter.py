import pytest

from models.alvo_discovery_comercial_hunter import (
    AlvoDiscoveryComercialHunter,
    ResultadoAlvosDiscoveryComercialHunter,
)
from services.scout.priorizacao_learning_discovery_comercial_hunter import (
    BONUS_MAXIMO_SINAIS,
    INTERVALO_EXPLORACAO,
    SCORE_MINIMO_BONUS,
    aplicar_priorizacao_learning_discovery_comercial_hunter,
)


def _alvo(
    termo,
    *,
    fonte="KabumScraper",
    sinais=3,
):
    return AlvoDiscoveryComercialHunter(
        fonte_hunter=fonte,
        marketplace="teste",
        estrategia="teste",
        termo_busca=termo,
        direcao="alta",
        sinais_distintos=sinais,
        motivo="teste",
        evidencias=(),
    )


def _resultado(
    *alvos,
):
    return ResultadoAlvosDiscoveryComercialHunter(alvos=tuple(alvos))


def _score_fonte(
    nome,
    *,
    score=100.0,
    confianca="alta",
    calculavel=True,
):
    return {
        "fonte_hunter": nome,
        "score_calculavel": calculavel,
        "score_learning": score,
        "confianca": confianca,
    }


def _score(
    *fontes,
    granularidade="fonte_hunter",
    maduro=True,
    observacional=True,
):
    return {
        "schema_version": 1,
        "status": "observado",
        "granularidade": granularidade,
        "somente_dataset_maduro": maduro,
        "score_observacional": observacional,
        "fontes": list(fontes),
    }


def _termos(
    resultado,
):
    return tuple(alvo.termo_busca for alvo in resultado.alvos)


def test_exige_resultado_correto():
    with pytest.raises(TypeError):
        aplicar_priorizacao_learning_discovery_comercial_hunter(
            resultado=None,
            score_learning=None,
        )


def test_sem_alvos_faz_fallback():
    entrada = _resultado()

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(),
    )

    assert saida.resultado.alvos == ()
    assert saida.observabilidade["status"] == "sem_alvos"


def test_sem_score_preserva_ordem_exata():
    entrada = _resultado(
        _alvo("A"),
        _alvo("B"),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=None,
    )

    assert saida.resultado.alvos == entrada.alvos
    assert saida.observabilidade["status"] == "fallback_sem_score_learning"


@pytest.mark.parametrize(
    "score",
    [
        _score(granularidade="termo"),
        _score(maduro=False),
        _score(observacional=False),
    ],
)
def test_contrato_score_invalido_faz_fallback(
    score,
):
    entrada = _resultado(
        _alvo("A"),
        _alvo("B"),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=score,
    )

    assert saida.resultado.alvos == entrada.alvos
    assert saida.observabilidade["status"] == "fallback_contrato_score_invalido"


def test_sem_score_elegivel_preserva_ordem():
    entrada = _resultado(
        _alvo("A"),
        _alvo(
            "B",
            fonte="AliExpressScraper",
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "KabumScraper",
                calculavel=False,
            )
        ),
    )

    assert saida.resultado.alvos == entrada.alvos
    assert saida.observabilidade["status"] == "fallback_sem_score_elegivel"


def test_learning_reordena_mesmo_nivel_de_sinais():
    entrada = _resultado(
        _alvo(
            "Novo",
            fonte="FonteNova",
            sinais=3,
        ),
        _alvo(
            "Aprendido",
            fonte="FonteAprendida",
            sinais=3,
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteAprendida",
                score=100,
                confianca="alta",
            )
        ),
    )

    assert _termos(saida.resultado) == (
        "Aprendido",
        "Novo",
    )

    assert saida.observabilidade["ordem_alterada"] is True


def test_learning_nunca_ultrapassa_mais_sinais():
    entrada = _resultado(
        _alvo(
            "Mais sinais",
            fonte="FonteNova",
            sinais=4,
        ),
        _alvo(
            "Score perfeito",
            fonte="FonteAprendida",
            sinais=3,
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteAprendida",
                score=100,
                confianca="alta",
            )
        ),
    )

    assert _termos(saida.resultado) == (
        "Mais sinais",
        "Score perfeito",
    )

    assert saida.observabilidade["politica"]["cruza_niveis_sinais"] is False


def test_score_baixo_nao_gera_penalidade():
    entrada = _resultado(
        _alvo(
            "Score baixo",
            fonte="FonteFraca",
        ),
        _alvo(
            "Sem score",
            fonte="FonteNova",
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteFraca",
                score=10,
            )
        ),
    )

    assert saida.resultado.alvos == entrada.alvos
    assert saida.observabilidade["politica"]["penalidade_score_baixo"] is False


def test_score_exatamente_no_limiar_nao_recebe_bonus():
    entrada = _resultado(
        _alvo(
            "A",
            fonte="FonteA",
        ),
        _alvo(
            "B",
            fonte="FonteB",
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteB",
                score=SCORE_MINIMO_BONUS,
                confianca="alta",
            )
        ),
    )

    assert saida.resultado.alvos == entrada.alvos
    assert saida.observabilidade["fontes_score_elegiveis"] == 0


def test_score_abaixo_minimo_nao_recebe_bonus():
    entrada = _resultado(
        _alvo(
            "A",
            fonte="FonteA",
        ),
        _alvo(
            "B",
            fonte="FonteB",
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteB",
                score=(SCORE_MINIMO_BONUS - 0.01),
            )
        ),
    )

    assert saida.resultado.alvos == entrada.alvos


def test_confianca_muito_baixa_nao_recebe_bonus():
    entrada = _resultado(
        _alvo(
            "A",
            fonte="FonteA",
        ),
        _alvo(
            "B",
            fonte="FonteB",
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteB",
                score=100,
                confianca="muito_baixa",
            )
        ),
    )

    assert saida.resultado.alvos == entrada.alvos


def test_bonus_maximo_e_menor_que_um_sinal():
    entrada = _resultado(
        _alvo(
            "A",
            fonte="FonteA",
        ),
        _alvo(
            "B",
            fonte="FonteB",
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteB",
                score=100,
                confianca="alta",
            )
        ),
    )

    fonte = next(
        item for item in saida.observabilidade["fontes_score"] if item["fonte_hunter"] == "FonteB"
    )

    assert fonte["bonus_sinais"] == BONUS_MAXIMO_SINAIS
    assert BONUS_MAXIMO_SINAIS < 1


def test_confianca_baixa_atenua_bonus():
    entrada = _resultado(
        _alvo(
            "A",
            fonte="FonteA",
        ),
        _alvo(
            "B",
            fonte="FonteB",
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteB",
                score=100,
                confianca="baixa",
            )
        ),
    )

    fonte = next(
        item for item in saida.observabilidade["fontes_score"] if item["fonte_hunter"] == "FonteB"
    )

    assert 0 < fonte["bonus_sinais"] < BONUS_MAXIMO_SINAIS


def test_exploration_floor_preserva_fonte_sem_score():
    aprendidos = [
        _alvo(
            f"A{indice}",
            fonte="FonteAprendida",
            sinais=3,
        )
        for indice in range(
            1,
            6,
        )
    ]

    exploracao = _alvo(
        "EXPLORAR",
        fonte="FonteNova",
        sinais=3,
    )

    entrada = _resultado(
        *aprendidos,
        exploracao,
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteAprendida",
                score=100,
                confianca="alta",
            )
        ),
    )

    termos = _termos(saida.resultado)

    assert termos.index("EXPLORAR") < INTERVALO_EXPLORACAO
    assert saida.observabilidade["movimentos_exploracao"] == 1


def test_exploration_floor_nao_cruza_nivel_de_sinais():
    entrada = _resultado(
        _alvo(
            "S4",
            fonte="FonteAprendida",
            sinais=4,
        ),
        _alvo(
            "S3-A",
            fonte="FonteAprendida",
            sinais=3,
        ),
        _alvo(
            "S3-B",
            fonte="FonteAprendida",
            sinais=3,
        ),
        _alvo(
            "S3-C",
            fonte="FonteAprendida",
            sinais=3,
        ),
        _alvo(
            "S3-D",
            fonte="FonteAprendida",
            sinais=3,
        ),
        _alvo(
            "S3-EXP",
            fonte="FonteNova",
            sinais=3,
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteAprendida",
                score=100,
                confianca="alta",
            )
        ),
    )

    assert saida.resultado.alvos[0].termo_busca == "S4"
    assert saida.resultado.alvos[0].sinais_distintos == 4


def test_nenhum_alvo_e_excluido():
    alvos = (
        _alvo(
            "A",
            fonte="FonteA",
        ),
        _alvo(
            "B",
            fonte="FonteB",
        ),
        _alvo(
            "C",
            fonte="FonteC",
        ),
    )

    entrada = _resultado(*alvos)

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteB",
                score=100,
            ),
            _score_fonte(
                "FonteC",
                score=0,
            ),
        ),
    )

    assert len(saida.resultado.alvos) == len(entrada.alvos)

    assert {id(alvo) for alvo in saida.resultado.alvos} == {id(alvo) for alvo in entrada.alvos}

    assert saida.observabilidade["politica"]["exclusao_por_score"] is False


def test_learning_permanece_na_granularidade_fonte():
    entrada = _resultado(
        _alvo(
            "Termo 1",
            fonte="FonteA",
        ),
        _alvo(
            "Termo 2",
            fonte="FonteA",
        ),
    )

    saida = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=_score(
            _score_fonte(
                "FonteA",
                score=90,
                confianca="alta",
            )
        ),
    )

    assert len(saida.observabilidade["fontes_score"]) == 1

    assert saida.observabilidade["granularidade_learning"] == "fonte_hunter"

    assert saida.observabilidade["politica"]["learning_por_termo"] is False


def test_resultado_e_deterministico():
    entrada = _resultado(
        _alvo(
            "A",
            fonte="FonteA",
        ),
        _alvo(
            "B",
            fonte="FonteB",
        ),
        _alvo(
            "C",
            fonte="FonteC",
        ),
    )

    score = _score(
        _score_fonte(
            "FonteB",
            score=88,
            confianca="media",
        )
    )

    primeira = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=score,
    )

    segunda = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=entrada,
        score_learning=score,
    )

    assert primeira.resultado.alvos == segunda.resultado.alvos
    assert primeira.observabilidade == segunda.observabilidade
