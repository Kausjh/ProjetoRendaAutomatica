from datetime import UTC, datetime, timedelta

import pytest

from models.alvo_discovery_comercial_hunter import (
    AlvoDiscoveryComercialHunter,
    ResultadoAlvosDiscoveryComercialHunter,
)
from services.scout.wiring_priorizacao_learning_discovery_comercial_hunter import (
    COOLDOWN_HORAS_PADRAO,
    aplicar_priorizacao_learning_com_historico,
)

AGORA = datetime(
    2026,
    9,
    11,
    22,
    0,
    tzinfo=UTC,
)


def _alvo(
    termo,
    *,
    fonte,
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


def _resultado():
    return ResultadoAlvosDiscoveryComercialHunter(
        alvos=(
            _alvo(
                "Nova",
                fonte="FonteNova",
            ),
            _alvo(
                "Aprendida",
                fonte="FonteAprendida",
            ),
        )
    )


def _score(
    *,
    fonte="FonteAprendida",
    score=100.0,
):
    return {
        "schema_version": 1,
        "status": "observado",
        "granularidade": "fonte_hunter",
        "somente_dataset_maduro": True,
        "score_observacional": True,
        "fontes": [
            {
                "fonte_hunter": fonte,
                "score_calculavel": True,
                "score_learning": score,
                "confianca": "alta",
            }
        ],
    }


def _relatorio_score(
    *,
    data,
    score=None,
):
    return {
        "data_hora": data.isoformat(),
        "commercial_discovery_learning": {"score": (score if score is not None else _score())},
    }


def _relatorio_priorizacao(
    *,
    data,
    fingerprint,
    influencia=True,
):
    return {
        "data_hora": data.isoformat(),
        "discovery_comercial_hunter": {
            "priorizacao_learning": {
                "influencia_priorizacao": influencia,
                "fingerprint_score": list(fingerprint),
            }
        },
    }


def _termos(
    saida,
):
    return tuple(alvo.termo_busca for alvo in saida.resultado.alvos)


def test_sem_historico_faz_fallback():
    entrada = _resultado()

    saida = aplicar_priorizacao_learning_com_historico(
        resultado=entrada,
        relatorios_execucao=(),
        agora=AGORA,
    )

    assert saida.resultado.alvos == entrada.alvos

    assert saida.observabilidade["status_runtime"] == "fallback_sem_score_persistido"


def test_ultimo_score_valido_e_aplicado():
    saida = aplicar_priorizacao_learning_com_historico(
        resultado=_resultado(),
        relatorios_execucao=[_relatorio_score(data=(AGORA - timedelta(hours=2)))],
        agora=AGORA,
    )

    assert _termos(saida) == (
        "Aprendida",
        "Nova",
    )

    assert saida.observabilidade["status_runtime"] == "aplicado_sem_historico_anterior"


def test_score_invalido_mais_novo_nao_apaga_valido_antigo():
    antigo = _relatorio_score(data=(AGORA - timedelta(hours=3)))

    novo = {
        "data_hora": (AGORA - timedelta(hours=1)).isoformat(),
        "commercial_discovery_learning": {
            "score": {
                "granularidade": "termo",
            }
        },
    }

    saida = aplicar_priorizacao_learning_com_historico(
        resultado=_resultado(),
        relatorios_execucao=[
            antigo,
            novo,
        ],
        agora=AGORA,
    )

    assert _termos(saida)[0] == "Aprendida"

    assert saida.observabilidade["score_origem_data_hora"] == antigo["data_hora"]


def test_score_valido_sem_fontes_faz_zero_reordenacao():
    score_vazio = {
        "schema_version": 1,
        "status": "sem_fontes_maduras",
        "granularidade": "fonte_hunter",
        "somente_dataset_maduro": True,
        "score_observacional": True,
        "fontes": [],
    }

    entrada = _resultado()

    saida = aplicar_priorizacao_learning_com_historico(
        resultado=entrada,
        relatorios_execucao=[
            _relatorio_score(
                data=AGORA,
                score=score_vazio,
            )
        ],
        agora=AGORA,
    )

    assert saida.resultado.alvos == entrada.alvos

    assert saida.observabilidade["influencia_priorizacao"] is False


def test_mesmo_fingerprint_nao_e_bloqueado_por_cooldown():
    relatorios = [
        _relatorio_priorizacao(
            data=(AGORA - timedelta(hours=1)),
            fingerprint=["FonteAprendida"],
        ),
        _relatorio_score(data=(AGORA - timedelta(minutes=10))),
    ]

    saida = aplicar_priorizacao_learning_com_historico(
        resultado=_resultado(),
        relatorios_execucao=relatorios,
        agora=AGORA,
    )

    assert _termos(saida)[0] == "Aprendida"

    assert saida.observabilidade["cooldown_ativo"] is False

    assert saida.observabilidade["status_runtime"] == "aplicado_fingerprint_estavel"


def test_fingerprint_novo_dentro_cooldown_faz_fallback():
    entrada = _resultado()

    relatorios = [
        _relatorio_priorizacao(
            data=(AGORA - timedelta(hours=1)),
            fingerprint=["OutraFonte"],
        ),
        _relatorio_score(data=(AGORA - timedelta(minutes=10))),
    ]

    saida = aplicar_priorizacao_learning_com_historico(
        resultado=entrada,
        relatorios_execucao=relatorios,
        agora=AGORA,
    )

    assert saida.resultado.alvos == entrada.alvos

    assert saida.observabilidade["cooldown_ativo"] is True

    assert saida.observabilidade["status_runtime"] == "cooldown_histerese_ativo"


def test_fingerprint_novo_apos_cooldown_pode_mudar():
    relatorios = [
        _relatorio_priorizacao(
            data=(AGORA - timedelta(hours=(COOLDOWN_HORAS_PADRAO + 1))),
            fingerprint=["OutraFonte"],
        ),
        _relatorio_score(data=(AGORA - timedelta(minutes=10))),
    ]

    saida = aplicar_priorizacao_learning_com_historico(
        resultado=_resultado(),
        relatorios_execucao=relatorios,
        agora=AGORA,
    )

    assert _termos(saida)[0] == "Aprendida"

    assert saida.observabilidade["status_runtime"] == "aplicado_apos_cooldown"


def test_priorizacao_sem_influencia_nao_aciona_cooldown():
    relatorios = [
        _relatorio_priorizacao(
            data=(AGORA - timedelta(hours=1)),
            fingerprint=["OutraFonte"],
            influencia=False,
        ),
        _relatorio_score(data=AGORA),
    ]

    saida = aplicar_priorizacao_learning_com_historico(
        resultado=_resultado(),
        relatorios_execucao=relatorios,
        agora=AGORA,
    )

    assert _termos(saida)[0] == "Aprendida"


@pytest.mark.parametrize(
    "valor",
    [
        0,
        -1,
        "abc",
        None,
    ],
)
def test_cooldown_invalido_falha(
    valor,
):
    with pytest.raises(ValueError):
        aplicar_priorizacao_learning_com_historico(
            resultado=_resultado(),
            relatorios_execucao=(),
            agora=AGORA,
            cooldown_horas=valor,
        )
