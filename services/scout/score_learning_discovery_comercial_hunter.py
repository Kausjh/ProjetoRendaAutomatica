from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# 63.8738, -149.7525

SCHEMA_VERSION = 1
GRANULARIDADE = "fonte_hunter"

PESO_NOVIDADE = 0.25
PESO_ELEGIBILIDADE = 0.30
PESO_SELECAO = 0.25
PESO_CONFIABILIDADE = 0.20


def criar_score_learning_discovery_comercial_hunter(
    *,
    janela_learning: Mapping[str, Any],
) -> dict[str, Any]:
    """Calcula score observacional usando somente evidencia madura.

    A publicacao real e preservada como evidencia complementar, mas
    ainda nao participa matematicamente do score.

    Isso evita atribuir a uma execucao da janela uma publicacao que
    pode ter sido originada por uma execucao anterior.
    """

    if not isinstance(
        janela_learning,
        Mapping,
    ):
        raise TypeError("janela_learning deve ser um Mapping")

    dataset_maduro = janela_learning.get("dataset_maduro")

    if not isinstance(
        dataset_maduro,
        Mapping,
    ):
        return _resultado_base(
            status="sem_dataset_maduro",
        )

    fontes_brutas = dataset_maduro.get("fontes")

    if not isinstance(
        fontes_brutas,
        list,
    ):
        fontes_brutas = []

    fontes_resultado: list[dict[str, Any]] = []

    for fonte_bruta in fontes_brutas:
        if not isinstance(
            fonte_bruta,
            Mapping,
        ):
            continue

        fonte = _normalizar_fonte(fonte_bruta.get("fonte_hunter"))

        if not fonte:
            continue

        execucoes = _inteiro_nao_negativo(fonte_bruta.get("execucoes_guiadas"))

        sucessos = _inteiro_nao_negativo(fonte_bruta.get("execucoes_sucesso"))

        falhas = _inteiro_nao_negativo(fonte_bruta.get("execucoes_falha"))

        erros = _inteiro_nao_negativo(fonte_bruta.get("execucoes_com_erro"))

        coletadas = _inteiro_nao_negativo(fonte_bruta.get("quantidade_coletada"))

        novas = _inteiro_nao_negativo(fonte_bruta.get("quantidade_novas"))

        elegiveis = _inteiro_nao_negativo(fonte_bruta.get("elegiveis_atribuidas"))

        selecionadas = _inteiro_nao_negativo(fonte_bruta.get("selecionadas_fila_atribuidas"))

        publicacoes = _inteiro_nao_negativo(fonte_bruta.get("publicacoes_atribuidas"))

        taxa_novidade = _percentual_limitado(
            novas,
            coletadas,
        )

        taxa_elegibilidade = _percentual_limitado(
            elegiveis,
            novas,
        )

        taxa_selecao = _percentual_limitado(
            selecionadas,
            elegiveis,
        )

        taxa_confiabilidade = _percentual_limitado(
            sucessos,
            execucoes,
        )

        score_calculavel = execucoes > 0 and coletadas > 0

        if score_calculavel:
            score = round(
                (taxa_novidade * PESO_NOVIDADE)
                + (taxa_elegibilidade * PESO_ELEGIBILIDADE)
                + (taxa_selecao * PESO_SELECAO)
                + (taxa_confiabilidade * PESO_CONFIABILIDADE),
                2,
            )

            motivo_sem_score = None
        else:
            score = None

            if execucoes <= 0:
                motivo_sem_score = "sem_execucoes_guiadas_maduras"
            else:
                motivo_sem_score = "sem_coleta_madura"

        confianca = _calcular_confianca(
            execucoes=execucoes,
            coletadas=coletadas,
        )

        fontes_resultado.append(
            {
                "fonte_hunter": fonte,
                "score_calculavel": (score_calculavel),
                "score_learning": score,
                "confianca": confianca,
                "motivo_sem_score": (motivo_sem_score),
                "amostra": {
                    "execucoes_guiadas": (execucoes),
                    "execucoes_sucesso": (sucessos),
                    "execucoes_falha": (falhas),
                    "execucoes_com_erro": (erros),
                    "quantidade_coletada": (coletadas),
                    "quantidade_novas": novas,
                    "elegiveis_atribuidas": (elegiveis),
                    "selecionadas_fila_atribuidas": (selecionadas),
                },
                "componentes": {
                    "novidade": {
                        "valor_percentual": (taxa_novidade),
                        "peso": (PESO_NOVIDADE),
                    },
                    "elegibilidade": {
                        "valor_percentual": (taxa_elegibilidade),
                        "peso": (PESO_ELEGIBILIDADE),
                    },
                    "selecao_fila": {
                        "valor_percentual": (taxa_selecao),
                        "peso": (PESO_SELECAO),
                    },
                    "confiabilidade_execucao": {
                        "valor_percentual": (taxa_confiabilidade),
                        "peso": (PESO_CONFIABILIDADE),
                    },
                },
                "evidencia_publicacao": {
                    "publicacoes_atribuidas": (publicacoes),
                    "entra_no_score": False,
                    "motivo": ("publicacao_assincrona_sem_coorte_" "causal_madura_comprovada"),
                },
            }
        )

    fontes_resultado.sort(
        key=lambda item: (
            item["score_learning"] is None,
            -(item["score_learning"] or 0.0),
            item["fonte_hunter"],
        )
    )

    calculaveis = sum(1 for fonte in fontes_resultado if fonte["score_calculavel"])

    if not fontes_resultado:
        status = "sem_fontes_maduras"
    elif calculaveis == 0:
        status = "evidencia_insuficiente"
    else:
        status = "observado"

    resultado = _resultado_base(
        status=status,
    )

    resultado["fontes_total"] = len(fontes_resultado)

    resultado["fontes_score_calculavel"] = calculaveis

    resultado["fontes_sem_score"] = len(fontes_resultado) - calculaveis

    resultado["fontes"] = fontes_resultado

    return resultado


def _resultado_base(
    *,
    status: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "granularidade": GRANULARIDADE,
        "somente_dataset_maduro": True,
        "score_observacional": True,
        "influencia_priorizacao": False,
        "publicacao_entra_no_score": False,
        "motivo_publicacao_fora_score": (
            "publicacao_assincrona_sem_coorte_" "causal_madura_comprovada"
        ),
        "pesos": {
            "novidade": PESO_NOVIDADE,
            "elegibilidade": (PESO_ELEGIBILIDADE),
            "selecao_fila": (PESO_SELECAO),
            "confiabilidade_execucao": (PESO_CONFIABILIDADE),
        },
        "fontes_total": 0,
        "fontes_score_calculavel": 0,
        "fontes_sem_score": 0,
        "fontes": [],
    }


def _calcular_confianca(
    *,
    execucoes: int,
    coletadas: int,
) -> str:
    if execucoes >= 8 and coletadas >= 80:
        return "alta"

    if execucoes >= 4 and coletadas >= 30:
        return "media"

    if execucoes >= 2 and coletadas >= 10:
        return "baixa"

    return "muito_baixa"


def _normalizar_fonte(
    valor: Any,
) -> str:
    return str(valor or "").strip()


def _inteiro_nao_negativo(
    valor: Any,
) -> int:
    try:
        resultado = int(valor or 0)
    except (
        TypeError,
        ValueError,
    ):
        return 0

    return max(
        0,
        resultado,
    )


def _percentual_limitado(
    numerador: int,
    denominador: int,
) -> float:
    if denominador <= 0:
        return 0.0

    percentual = (numerador / denominador) * 100.0

    percentual = max(
        0.0,
        min(
            100.0,
            percentual,
        ),
    )

    return round(
        percentual,
        2,
    )
