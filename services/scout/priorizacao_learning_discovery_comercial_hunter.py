from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real
from typing import Any

from models.alvo_discovery_comercial_hunter import (
    AlvoDiscoveryComercialHunter,
    ResultadoAlvosDiscoveryComercialHunter,
)

# Policy marker: 63.8738, -149.7525
SCHEMA_VERSION = 1

BONUS_MAXIMO_SINAIS = 0.49
SCORE_MINIMO_BONUS = 60.0
INTERVALO_EXPLORACAO = 4

FATOR_CONFIANCA = {
    "baixa": 0.25,
    "media": 0.50,
    "alta": 1.00,
}


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoPriorizacaoLearningDiscoveryComercialHunter:
    resultado: ResultadoAlvosDiscoveryComercialHunter
    observabilidade: dict[str, Any]


def aplicar_priorizacao_learning_discovery_comercial_hunter(
    *,
    resultado: ResultadoAlvosDiscoveryComercialHunter,
    score_learning: Mapping[str, Any] | None,
) -> ResultadoPriorizacaoLearningDiscoveryComercialHunter:
    """Aplica influencia limitada do Learning nos alvos comerciais.

    O Learning somente reorganiza alvos com a mesma quantidade de
    sinais comerciais. Ele nunca exclui alvos, nunca penaliza score
    baixo e nunca opera em granularidade de termo.
    """

    if not isinstance(
        resultado,
        ResultadoAlvosDiscoveryComercialHunter,
    ):
        raise TypeError("resultado deve ser um " "ResultadoAlvosDiscoveryComercialHunter")

    alvos_base = list(resultado.alvos)

    observabilidade = _observabilidade_base(alvos_total=len(alvos_base))

    if not alvos_base:
        observabilidade["status"] = "sem_alvos"

        return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
            resultado=resultado,
            observabilidade=observabilidade,
        )

    if not isinstance(
        score_learning,
        Mapping,
    ):
        observabilidade["status"] = "fallback_sem_score_learning"

        return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
            resultado=resultado,
            observabilidade=observabilidade,
        )

    if not _contrato_score_valido(score_learning):
        observabilidade["status"] = "fallback_contrato_score_invalido"

        return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
            resultado=resultado,
            observabilidade=observabilidade,
        )

    fontes_score = _carregar_scores_elegiveis(score_learning)

    observabilidade["fontes_score_elegiveis"] = len(fontes_score)

    observabilidade["fontes_score"] = [
        {
            "fonte_hunter": item["fonte_hunter"],
            "score_learning": item["score_learning"],
            "confianca": item["confianca"],
            "bonus_sinais": item["bonus_sinais"],
        }
        for item in sorted(
            fontes_score.values(),
            key=lambda item: item["fonte_hunter"],
        )
    ]

    if not fontes_score:
        observabilidade["status"] = "fallback_sem_score_elegivel"

        return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
            resultado=resultado,
            observabilidade=observabilidade,
        )

    grupos: dict[
        int,
        list[
            tuple[
                int,
                AlvoDiscoveryComercialHunter,
            ]
        ],
    ] = {}

    for indice, alvo in enumerate(alvos_base):
        grupos.setdefault(
            int(alvo.sinais_distintos),
            [],
        ).append(
            (
                indice,
                alvo,
            )
        )

    alvos_finais: list[AlvoDiscoveryComercialHunter] = []

    movimentos_exploracao = 0

    for sinais in sorted(
        grupos,
        reverse=True,
    ):
        grupo = grupos[sinais]

        priorizados = sorted(
            grupo,
            key=lambda item: (
                -_bonus_alvo(
                    item[1],
                    fontes_score,
                ),
                item[0],
            ),
        )

        (
            priorizados,
            movimentos_bloco,
        ) = _aplicar_exploration_floor(
            priorizados,
            fontes_score=fontes_score,
        )

        movimentos_exploracao += movimentos_bloco

        alvos_finais.extend(alvo for _, alvo in priorizados)

    ordem_alterada = tuple(alvos_finais) != tuple(alvos_base)

    posicao_base = {id(alvo): indice for indice, alvo in enumerate(alvos_base)}

    movimentos_total = sum(
        1 for indice, alvo in enumerate(alvos_finais) if posicao_base[id(alvo)] != indice
    )

    observabilidade["ordem_alterada"] = ordem_alterada

    observabilidade["influencia_priorizacao"] = ordem_alterada

    observabilidade["movimentos_total"] = movimentos_total

    observabilidade["movimentos_exploracao"] = movimentos_exploracao

    observabilidade["status"] = "aplicado" if ordem_alterada else "aplicado_sem_reordenacao"

    return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
        resultado=ResultadoAlvosDiscoveryComercialHunter(alvos=tuple(alvos_finais)),
        observabilidade=observabilidade,
    )


def _contrato_score_valido(
    score_learning: Mapping[str, Any],
) -> bool:
    return (
        score_learning.get("granularidade") == "fonte_hunter"
        and score_learning.get("somente_dataset_maduro") is True
        and score_learning.get("score_observacional") is True
    )


def _carregar_scores_elegiveis(
    score_learning: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    fontes = score_learning.get("fontes")

    if not isinstance(
        fontes,
        list,
    ):
        return {}

    resultado: dict[
        str,
        dict[str, Any],
    ] = {}

    for fonte in fontes:
        if not isinstance(
            fonte,
            Mapping,
        ):
            continue

        nome = _normalizar_fonte(fonte.get("fonte_hunter"))

        if not nome:
            continue

        if fonte.get("score_calculavel") is not True:
            continue

        score = fonte.get("score_learning")

        if not isinstance(
            score,
            Real,
        ) or isinstance(
            score,
            bool,
        ):
            continue

        score_normalizado = max(
            0.0,
            min(
                100.0,
                float(score),
            ),
        )

        confianca = str(fonte.get("confianca") or "").strip().casefold()

        fator = FATOR_CONFIANCA.get(confianca)

        if fator is None:
            continue

        if score_normalizado < SCORE_MINIMO_BONUS:
            continue

        bonus = _calcular_bonus(
            score=score_normalizado,
            fator_confianca=fator,
        )

        if bonus <= 0:
            continue

        resultado[nome.casefold()] = {
            "fonte_hunter": nome,
            "score_learning": score_normalizado,
            "confianca": confianca,
            "bonus_sinais": bonus,
        }

    return resultado


def _calcular_bonus(
    *,
    score: float,
    fator_confianca: float,
) -> float:
    faixa_util = 100.0 - SCORE_MINIMO_BONUS

    if faixa_util <= 0:
        return 0.0

    proporcao = (score - SCORE_MINIMO_BONUS) / faixa_util

    proporcao = max(
        0.0,
        min(
            1.0,
            proporcao,
        ),
    )

    return round(
        BONUS_MAXIMO_SINAIS * proporcao * fator_confianca,
        4,
    )


def _bonus_alvo(
    alvo: AlvoDiscoveryComercialHunter,
    fontes_score: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> float:
    fonte = fontes_score.get(alvo.fonte_hunter.casefold())

    if not isinstance(
        fonte,
        Mapping,
    ):
        return 0.0

    bonus = fonte.get("bonus_sinais")

    if not isinstance(
        bonus,
        Real,
    ):
        return 0.0

    return float(bonus)


def _aplicar_exploration_floor(
    itens: list[
        tuple[
            int,
            AlvoDiscoveryComercialHunter,
        ]
    ],
    *,
    fontes_score: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> tuple[
    list[
        tuple[
            int,
            AlvoDiscoveryComercialHunter,
        ]
    ],
    int,
]:
    if INTERVALO_EXPLORACAO <= 1 or len(itens) <= 1:
        return (
            list(itens),
            0,
        )

    resultado = list(itens)

    movimentos = 0
    inicio = 0

    while inicio < len(resultado):
        fim = min(
            inicio + INTERVALO_EXPLORACAO,
            len(resultado),
        )

        bloco = resultado[inicio:fim]

        possui_exploracao = any(
            not _fonte_tem_bonus(
                alvo,
                fontes_score,
            )
            for _, alvo in bloco
        )

        if not possui_exploracao:
            indice_exploracao = next(
                (
                    indice
                    for indice in range(
                        fim,
                        len(resultado),
                    )
                    if not _fonte_tem_bonus(
                        resultado[indice][1],
                        fontes_score,
                    )
                ),
                None,
            )

            if indice_exploracao is not None:
                alvo_exploracao = resultado.pop(indice_exploracao)

                resultado.insert(
                    fim - 1,
                    alvo_exploracao,
                )

                movimentos += 1

        inicio = fim

    return (
        resultado,
        movimentos,
    )


def _fonte_tem_bonus(
    alvo: AlvoDiscoveryComercialHunter,
    fontes_score: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> bool:
    return alvo.fonte_hunter.casefold() in fontes_score


def _normalizar_fonte(
    valor: object,
) -> str:
    return str(valor or "").strip()


def _observabilidade_base(
    *,
    alvos_total: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "nao_avaliado",
        "granularidade_learning": "fonte_hunter",
        "alvos_total": alvos_total,
        "fontes_score_elegiveis": 0,
        "fontes_score": [],
        "ordem_alterada": False,
        "influencia_priorizacao": False,
        "movimentos_total": 0,
        "movimentos_exploracao": 0,
        "politica": {
            "bonus_maximo_sinais": BONUS_MAXIMO_SINAIS,
            "score_minimo_bonus": SCORE_MINIMO_BONUS,
            "intervalo_exploracao": INTERVALO_EXPLORACAO,
            "penalidade_score_baixo": False,
            "exclusao_por_score": False,
            "cruza_niveis_sinais": False,
            "fallback_ordem_base": True,
            "learning_por_termo": False,
            "exige_dataset_maduro": True,
            "exige_score_observacional": True,
        },
    }
