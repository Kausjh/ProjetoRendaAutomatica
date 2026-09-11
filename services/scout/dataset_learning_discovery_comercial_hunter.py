from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

# 63.8738, -149.7525

SCHEMA_VERSION = 1
GRANULARIDADE = "fonte_hunter"
ORIGEM_PROVENIENCIA = "commercial_discovery_hunter"


def criar_dataset_learning_discovery_comercial_hunter(
    *,
    relatorios_execucao: Iterable[Mapping[str, Any]] = (),
    historico_publicacoes: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Consolida evidencias observacionais por fonte Hunter.

    A funcao nao decide prioridades, nao altera score e nao controla
    nenhuma etapa do pipeline.

    Os relatorios de execucao representam resultados de descoberta.
    O historico de publicacoes representa eventos reais e duraveis de
    publicacao.

    Publicacao e assincrona. Por isso esta camada nao calcula uma taxa
    de conversao entre fila e publicacao. Essa relacao exige uma janela
    temporal/maturacao explicita antes de virar sinal de aprendizado.
    """

    fontes: dict[
        str,
        dict[str, Any],
    ] = {}

    relatorios_observados = 0
    ciclos_com_outcome = 0
    ciclos_sem_outcome = 0
    alvos_aplicados_total = 0

    for relatorio in relatorios_execucao:
        if not isinstance(
            relatorio,
            Mapping,
        ):
            continue

        relatorios_observados += 1

        outcome = relatorio.get("commercial_discovery_outcome")

        if not isinstance(
            outcome,
            Mapping,
        ):
            ciclos_sem_outcome += 1
            continue

        ciclos_com_outcome += 1

        alvos_aplicados_total += _inteiro_nao_negativo(outcome.get("alvos_aplicados"))

        fontes_outcome = outcome.get("fontes")

        if not isinstance(
            fontes_outcome,
            list,
        ):
            continue

        for resultado_fonte in fontes_outcome:
            if not isinstance(
                resultado_fonte,
                Mapping,
            ):
                continue

            fonte = _normalizar_fonte(resultado_fonte.get("fonte_hunter"))

            if not fonte:
                continue

            agregado = _fonte_base(
                fontes,
                fonte,
            )

            agregado["execucoes_guiadas"] += 1

            agregado["limite_solicitado"] += _inteiro_nao_negativo(
                resultado_fonte.get("limite_solicitado")
            )

            agregado["quantidade_coletada"] += _inteiro_nao_negativo(
                resultado_fonte.get("quantidade_coletada")
            )

            agregado["quantidade_novas"] += _inteiro_nao_negativo(
                resultado_fonte.get("quantidade_novas")
            )

            agregado["quantidade_duplicadas"] += _inteiro_nao_negativo(
                resultado_fonte.get("quantidade_duplicadas")
            )

            agregado["elegiveis_atribuidas"] += _inteiro_nao_negativo(
                resultado_fonte.get("elegiveis_atribuidas")
            )

            agregado["selecionadas_fila_atribuidas"] += _inteiro_nao_negativo(
                resultado_fonte.get("selecionadas_fila_atribuidas")
            )

            sucesso = resultado_fonte.get("sucesso")

            if sucesso is True:
                agregado["execucoes_sucesso"] += 1
            elif sucesso is False:
                agregado["execucoes_falha"] += 1

            if resultado_fonte.get("erro"):
                agregado["execucoes_com_erro"] += 1

    publicacoes_observadas = 0
    publicacoes_atribuidas_discovery = 0
    publicacoes_sem_proveniencia = 0
    eventos_multifonte = 0

    for publicacao in historico_publicacoes:
        if not isinstance(
            publicacao,
            Mapping,
        ):
            continue

        publicacoes_observadas += 1

        proveniencia = publicacao.get("proveniencia_discovery_comercial")

        fontes_publicacao = _fontes_publicacao(proveniencia)

        if not fontes_publicacao:
            publicacoes_sem_proveniencia += 1
            continue

        publicacoes_atribuidas_discovery += 1

        if len(fontes_publicacao) > 1:
            eventos_multifonte += 1

        for fonte in fontes_publicacao:
            agregado = _fonte_base(
                fontes,
                fonte,
            )

            agregado["publicacoes_atribuidas"] += 1

    fontes_resultado = []

    for fonte in sorted(fontes):
        agregado = fontes[fonte]

        agregado["taxa_novas_sobre_coletadas_percentual"] = _percentual(
            agregado["quantidade_novas"],
            agregado["quantidade_coletada"],
        )

        agregado["taxa_elegibilidade_sobre_novas_percentual"] = _percentual(
            agregado["elegiveis_atribuidas"],
            agregado["quantidade_novas"],
        )

        agregado["taxa_selecao_sobre_elegiveis_percentual"] = _percentual(
            agregado["selecionadas_fila_atribuidas"],
            agregado["elegiveis_atribuidas"],
        )

        agregado["tem_evidencia_execucao"] = agregado["execucoes_guiadas"] > 0

        agregado["tem_evidencia_publicacao"] = agregado["publicacoes_atribuidas"] > 0

        agregado["publicacao_sem_execucao_observada"] = (
            agregado["publicacoes_atribuidas"] > 0 and agregado["execucoes_guiadas"] == 0
        )

        fontes_resultado.append(agregado)

    if not relatorios_observados and not publicacoes_observadas:
        status = "sem_evidencias"
    elif not fontes_resultado:
        status = "sem_fontes_atribuidas"
    else:
        status = "observado"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "granularidade": GRANULARIDADE,
        "atribuicao_alvo_individual": False,
        "relatorios_observados": (relatorios_observados),
        "ciclos_com_outcome": (ciclos_com_outcome),
        "ciclos_sem_outcome": (ciclos_sem_outcome),
        "alvos_aplicados_total": (alvos_aplicados_total),
        "publicacoes_observadas": (publicacoes_observadas),
        "publicacoes_atribuidas_discovery": (publicacoes_atribuidas_discovery),
        "publicacoes_sem_proveniencia_discovery": (publicacoes_sem_proveniencia),
        "eventos_multifonte": (eventos_multifonte),
        "fontes_total": len(fontes_resultado),
        "publicacao_assincrona": True,
        "taxa_publicacao_nao_calculada": True,
        "motivo_taxa_publicacao_nao_calculada": (
            "publicacao_pode_ocorrer_em_ciclo_posterior_" "e_exige_janela_temporal_maturada"
        ),
        "fontes": fontes_resultado,
    }


def _fonte_base(
    fontes: dict[
        str,
        dict[str, Any],
    ],
    fonte: str,
) -> dict[str, Any]:
    existente = fontes.get(fonte)

    if existente is not None:
        return existente

    novo = {
        "fonte_hunter": fonte,
        "execucoes_guiadas": 0,
        "execucoes_sucesso": 0,
        "execucoes_falha": 0,
        "execucoes_com_erro": 0,
        "limite_solicitado": 0,
        "quantidade_coletada": 0,
        "quantidade_novas": 0,
        "quantidade_duplicadas": 0,
        "elegiveis_atribuidas": 0,
        "selecionadas_fila_atribuidas": 0,
        "publicacoes_atribuidas": 0,
    }

    fontes[fonte] = novo

    return novo


def _fontes_publicacao(
    proveniencia: Any,
) -> tuple[str, ...]:
    if not isinstance(
        proveniencia,
        Mapping,
    ):
        return ()

    if proveniencia.get("origem") != ORIGEM_PROVENIENCIA:
        return ()

    if proveniencia.get("granularidade") != GRANULARIDADE:
        return ()

    fontes_brutas = proveniencia.get("fontes_hunter_guiadas")

    if not isinstance(
        fontes_brutas,
        (
            list,
            tuple,
            set,
            frozenset,
        ),
    ):
        return ()

    fontes = {fonte for valor in fontes_brutas if (fonte := _normalizar_fonte(valor))}

    return tuple(sorted(fontes))


def _normalizar_fonte(
    valor: Any,
) -> str:
    return str(valor or "").strip()


def _inteiro_nao_negativo(
    valor: Any,
) -> int:
    try:
        inteiro = int(valor or 0)
    except (
        TypeError,
        ValueError,
    ):
        return 0

    return max(
        0,
        inteiro,
    )


def _percentual(
    numerador: int,
    denominador: int,
) -> float:
    if denominador <= 0:
        return 0.0

    return round(
        (numerador / denominador) * 100.0,
        2,
    )
