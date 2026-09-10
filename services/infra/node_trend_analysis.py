# 63.8738, -149.7525

from __future__ import annotations

import json
import math
import statistics
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from models.tendencia_node import (
    AnaliseTendenciaNode,
    ComparativoMetricaNode,
    TendenciaServicoNode,
)
from services.infra.node_health import DIRETORIO_PROJETO
from services.infra.node_history_analysis import (
    DIRETORIO_HISTORICO_PADRAO,
    MAXIMO_AMOSTRAS_PADRAO,
    MAXIMO_ARQUIVOS_PADRAO,
    carregar_historico_node,
)

CAMINHO_TENDENCIA_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "tendencia_atual.json"

JANELA_RECENTE_MINUTOS_PADRAO = 60
JANELA_BASELINE_MINUTOS_PADRAO = 360


def _numero(
    valor: object,
) -> float | None:
    if isinstance(valor, bool):
        return None

    if not isinstance(
        valor,
        (int, float),
    ):
        return None

    numero = float(valor)

    if not math.isfinite(numero):
        return None

    return numero


def _instante(
    valor: object,
) -> datetime | None:
    if not isinstance(valor, str):
        return None

    texto = valor.strip()

    if not texto:
        return None

    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"

    try:
        instante = datetime.fromisoformat(texto)
    except ValueError:
        return None

    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)

    return instante


def _amostras_metrica(
    registros: tuple[
        dict[str, Any],
        ...,
    ],
    chave: str,
) -> list[tuple[datetime, float]]:
    resultado: list[tuple[datetime, float]] = []

    for registro in registros:
        instante = _instante(registro.get("coletado_em"))

        valor = _numero(registro.get(chave))

        if instante is None or valor is None:
            continue

        resultado.append(
            (
                instante,
                valor,
            )
        )

    return resultado


def _media(
    amostras: list[tuple[datetime, float]],
) -> float | None:
    if not amostras:
        return None

    return statistics.fmean(valor for _, valor in amostras)


def _inclinacao_por_hora(
    amostras: list[tuple[datetime, float]],
) -> float | None:
    if len(amostras) < 2:
        return None

    origem = amostras[0][0]

    pontos = [
        (
            (instante - origem).total_seconds() / 3600.0,
            valor,
        )
        for instante, valor in amostras
    ]

    xs = [ponto[0] for ponto in pontos]

    ys = [ponto[1] for ponto in pontos]

    media_x = statistics.fmean(xs)
    media_y = statistics.fmean(ys)

    denominador = sum((x - media_x) ** 2 for x in xs)

    if denominador == 0:
        return None

    numerador = sum((x - media_x) * (y - media_y) for x, y in pontos)

    return numerador / denominador


def _comparar(
    recente: list[tuple[datetime, float]],
    baseline: list[tuple[datetime, float]],
) -> ComparativoMetricaNode:
    media_recente = _media(recente)

    media_baseline = _media(baseline)

    delta_absoluto: float | None = None
    delta_percentual: float | None = None

    if media_recente is not None and media_baseline is not None:
        delta_absoluto = media_recente - media_baseline

        if media_baseline != 0:
            delta_percentual = delta_absoluto / media_baseline * 100.0

    atual = recente[-1][1] if recente else None

    return ComparativoMetricaNode(
        atual=atual,
        media_recente=media_recente,
        media_baseline=media_baseline,
        delta_media_absoluto=delta_absoluto,
        delta_media_percentual=delta_percentual,
        inclinacao_recente_por_hora=(_inclinacao_por_hora(recente)),
        amostras_recente=len(recente),
        amostras_baseline=len(baseline),
    )


def _servico_em_registro(
    registro: dict[str, Any],
    nome: str,
) -> dict[str, Any] | None:
    servicos = registro.get("servicos")

    if not isinstance(
        servicos,
        list,
    ):
        return None

    for servico in servicos:
        if not isinstance(
            servico,
            dict,
        ):
            continue

        if servico.get("nome") == nome:
            return servico

    return None


def _amostras_memoria_servico(
    registros: tuple[
        dict[str, Any],
        ...,
    ],
    nome: str,
) -> list[tuple[datetime, float]]:
    resultado: list[tuple[datetime, float]] = []

    for registro in registros:
        instante = _instante(registro.get("coletado_em"))

        servico = _servico_em_registro(
            registro,
            nome,
        )

        if instante is None or servico is None:
            continue

        memoria = _numero(servico.get("memoria_rss_bytes"))

        if memoria is None:
            continue

        resultado.append(
            (
                instante,
                memoria,
            )
        )

    return resultado


def _percentual_ativo(
    registros: tuple[
        dict[str, Any],
        ...,
    ],
    nome: str,
) -> tuple[
    float | None,
    int,
]:
    observadas = 0
    ativas = 0

    for registro in registros:
        servico = _servico_em_registro(
            registro,
            nome,
        )

        if servico is None:
            continue

        observadas += 1

        if servico.get("ativo") is True:
            ativas += 1

    if observadas == 0:
        return (
            None,
            0,
        )

    return (
        ativas / observadas * 100.0,
        observadas,
    )


def _nomes_servicos(
    registros: tuple[
        dict[str, Any],
        ...,
    ],
) -> tuple[str, ...]:
    nomes: set[str] = set()

    for registro in registros:
        servicos = registro.get("servicos")

        if not isinstance(
            servicos,
            list,
        ):
            continue

        for servico in servicos:
            if not isinstance(
                servico,
                dict,
            ):
                continue

            nome = servico.get("nome")

            if (
                isinstance(
                    nome,
                    str,
                )
                and nome.strip()
            ):
                nomes.add(nome.strip())

    return tuple(sorted(nomes))


def _tendencias_servicos(
    recente: tuple[
        dict[str, Any],
        ...,
    ],
    baseline: tuple[
        dict[str, Any],
        ...,
    ],
) -> tuple[
    TendenciaServicoNode,
    ...,
]:
    todos = baseline + recente

    resultado: list[TendenciaServicoNode] = []

    for nome in _nomes_servicos(todos):
        ativo_recente, obs_recente = _percentual_ativo(
            recente,
            nome,
        )

        ativo_baseline, obs_baseline = _percentual_ativo(
            baseline,
            nome,
        )

        delta_ativo: float | None = None

        if ativo_recente is not None and ativo_baseline is not None:
            delta_ativo = ativo_recente - ativo_baseline

        resultado.append(
            TendenciaServicoNode(
                nome=nome,
                memoria_rss_bytes=(
                    _comparar(
                        _amostras_memoria_servico(
                            recente,
                            nome,
                        ),
                        _amostras_memoria_servico(
                            baseline,
                            nome,
                        ),
                    )
                ),
                percentual_ativo_recente=(ativo_recente),
                percentual_ativo_baseline=(ativo_baseline),
                delta_percentual_ativo_pontos=(delta_ativo),
                amostras_observadas_recente=(obs_recente),
                amostras_observadas_baseline=(obs_baseline),
            )
        )

    return tuple(resultado)


def analisar_tendencia_node(
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
    *,
    janela_recente_minutos: int = (JANELA_RECENTE_MINUTOS_PADRAO),
    janela_baseline_minutos: int = (JANELA_BASELINE_MINUTOS_PADRAO),
    maximo_arquivos: int = (MAXIMO_ARQUIVOS_PADRAO),
    maximo_amostras: int = (MAXIMO_AMOSTRAS_PADRAO),
) -> AnaliseTendenciaNode:
    if janela_recente_minutos <= 0:
        raise ValueError("janela_recente_minutos " "precisa ser maior que zero.")

    if janela_baseline_minutos <= 0:
        raise ValueError("janela_baseline_minutos " "precisa ser maior que zero.")

    registros = carregar_historico_node(
        diretorio_historico,
        maximo_arquivos=maximo_arquivos,
        maximo_amostras=maximo_amostras,
    )

    if not registros:
        raise ValueError("Nenhuma amostra valida " "foi encontrada.")

    instante_final = _instante(registros[-1].get("coletado_em"))

    if instante_final is None:
        raise ValueError("Ultima amostra possui " "timestamp invalido.")

    inicio_recente = instante_final - timedelta(minutes=(janela_recente_minutos))

    inicio_baseline = inicio_recente - timedelta(minutes=(janela_baseline_minutos))

    baseline_lista: list[dict[str, Any]] = []

    recente_lista: list[dict[str, Any]] = []

    for registro in registros:
        instante = _instante(registro.get("coletado_em"))

        if instante is None:
            continue

        if inicio_baseline <= instante < inicio_recente:
            baseline_lista.append(registro)

        elif inicio_recente <= instante <= instante_final:
            recente_lista.append(registro)

    baseline = tuple(baseline_lista)

    recente = tuple(recente_lista)

    node_ids = [
        registro.get("node_id")
        for registro in registros
        if isinstance(
            registro.get("node_id"),
            str,
        )
    ]

    node_id = node_ids[-1] if node_ids else None

    def comparar_chave(
        chave: str,
    ) -> ComparativoMetricaNode:
        return _comparar(
            _amostras_metrica(
                recente,
                chave,
            ),
            _amostras_metrica(
                baseline,
                chave,
            ),
        )

    return AnaliseTendenciaNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=(instante_final.isoformat()),
        inicio_baseline=(inicio_baseline.isoformat()),
        fim_baseline=(inicio_recente.isoformat()),
        inicio_recente=(inicio_recente.isoformat()),
        fim_recente=(instante_final.isoformat()),
        janela_recente_minutos=(janela_recente_minutos),
        janela_baseline_minutos=(janela_baseline_minutos),
        quantidade_amostras_recente=(len(recente)),
        quantidade_amostras_baseline=(len(baseline)),
        cpu_percentual=comparar_chave("cpu_percentual"),
        memoria_host_percentual=(comparar_chave("memoria_uso_percentual")),
        memoria_processos_projeto_bytes=(comparar_chave("memoria_processos_projeto_bytes")),
        quantidade_processos_projeto=(comparar_chave("quantidade_processos_projeto")),
        servicos=_tendencias_servicos(
            recente,
            baseline,
        ),
    )


def salvar_tendencia_node(
    analise: AnaliseTendenciaNode,
    caminho: str | Path = (CAMINHO_TENDENCIA_PADRAO),
) -> Path:
    caminho = Path(caminho)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporario = caminho.with_suffix(caminho.suffix + ".tmp")

    temporario.write_text(
        json.dumps(
            analise.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporario.replace(caminho)

    return caminho
