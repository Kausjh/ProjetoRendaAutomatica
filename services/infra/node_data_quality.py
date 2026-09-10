# 63.8738, -149.7525

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from models.qualidade_node import (
    AnaliseQualidadeDadosNode,
    CoberturaMetricaNode,
    QualidadeJanelaNode,
    QualidadeServicoNode,
)
from services.infra.node_health import DIRETORIO_PROJETO
from services.infra.node_history_analysis import (
    DIRETORIO_HISTORICO_PADRAO,
    MAXIMO_AMOSTRAS_PADRAO,
    MAXIMO_ARQUIVOS_PADRAO,
    carregar_historico_node,
)
from services.infra.node_trend_analysis import (
    JANELA_BASELINE_MINUTOS_PADRAO,
    JANELA_RECENTE_MINUTOS_PADRAO,
)

CAMINHO_QUALIDADE_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "qualidade_atual.json"

CADENCIA_NOMINAL_SEGUNDOS_PADRAO = 300.0


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


def _percentual(
    numerador: int,
    denominador: int,
) -> float | None:
    if denominador <= 0:
        return None

    return numerador / denominador * 100.0


def _esperadas_recente(
    minutos: int,
    cadencia_segundos: float,
) -> int:
    duracao_segundos = minutos * 60.0

    return math.floor(duracao_segundos / cadencia_segundos) + 1


def _esperadas_baseline(
    minutos: int,
    cadencia_segundos: float,
) -> int:
    duracao_segundos = minutos * 60.0

    return math.ceil(duracao_segundos / cadencia_segundos)


def _qualidade_janela(
    nome: str,
    registros: tuple[
        dict[str, Any],
        ...,
    ],
    *,
    inicio: datetime,
    fim: datetime,
    duracao_minutos: int,
    cadencia_segundos: float,
    inclui_fim: bool,
) -> QualidadeJanelaNode:
    instantes = [
        instante
        for registro in registros
        if (instante := _instante(registro.get("coletado_em"))) is not None
    ]

    instantes.sort()

    maior_gap: float | None = None
    gaps_grandes = 0
    repetidos = 0

    for anterior, atual in zip(
        instantes,
        instantes[1:],
        strict=False,
    ):
        gap = (atual - anterior).total_seconds()

        if gap <= 0:
            repetidos += 1
            continue

        if maior_gap is None or gap > maior_gap:
            maior_gap = gap

        if gap >= (cadencia_segundos * 2.0):
            gaps_grandes += 1

    if inclui_fim:
        esperadas = _esperadas_recente(
            duracao_minutos,
            cadencia_segundos,
        )
    else:
        esperadas = _esperadas_baseline(
            duracao_minutos,
            cadencia_segundos,
        )

    observadas = len(instantes)

    razao = _percentual(
        observadas,
        esperadas,
    )

    multiplo = maior_gap / cadencia_segundos if maior_gap is not None else None

    return QualidadeJanelaNode(
        nome=nome,
        inicio=inicio.isoformat(),
        fim=fim.isoformat(),
        duracao_minutos=duracao_minutos,
        cadencia_nominal_segundos=(cadencia_segundos),
        amostras_esperadas=esperadas,
        amostras_observadas=observadas,
        razao_amostras_percentual=razao,
        primeira_amostra=(instantes[0].isoformat() if instantes else None),
        ultima_amostra=(instantes[-1].isoformat() if instantes else None),
        maior_gap_segundos=maior_gap,
        maior_gap_multiplo_cadencia=(multiplo),
        gaps_igual_ou_acima_2x_cadencia=(gaps_grandes),
        timestamps_repetidos=repetidos,
    )


def _selecionar_janelas(
    registros: tuple[
        dict[str, Any],
        ...,
    ],
    *,
    janela_recente_minutos: int,
    janela_baseline_minutos: int,
) -> tuple[
    datetime,
    datetime,
    datetime,
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
]:
    instante_final = _instante(registros[-1].get("coletado_em"))

    if instante_final is None:
        raise ValueError("Ultima amostra possui " "timestamp invalido.")

    inicio_recente = instante_final - timedelta(minutes=(janela_recente_minutos))

    inicio_baseline = inicio_recente - timedelta(minutes=(janela_baseline_minutos))

    recente: list[dict[str, Any]] = []

    baseline: list[dict[str, Any]] = []

    for registro in registros:
        instante = _instante(registro.get("coletado_em"))

        if instante is None:
            continue

        if inicio_baseline <= instante < inicio_recente:
            baseline.append(registro)

        elif inicio_recente <= instante <= instante_final:
            recente.append(registro)

    return (
        instante_final,
        inicio_recente,
        inicio_baseline,
        tuple(recente),
        tuple(baseline),
    )


def _cobertura_metrica(
    nome: str,
    chave: str,
    recente: tuple[
        dict[str, Any],
        ...,
    ],
    baseline: tuple[
        dict[str, Any],
        ...,
    ],
) -> CoberturaMetricaNode:
    recente_com_valor = sum(1 for registro in recente if _numero(registro.get(chave)) is not None)

    baseline_com_valor = sum(1 for registro in baseline if _numero(registro.get(chave)) is not None)

    return CoberturaMetricaNode(
        nome=nome,
        amostras_com_valor_recente=(recente_com_valor),
        amostras_com_valor_baseline=(baseline_com_valor),
        percentual_presenca_recente=(
            _percentual(
                recente_com_valor,
                len(recente),
            )
        ),
        percentual_presenca_baseline=(
            _percentual(
                baseline_com_valor,
                len(baseline),
            )
        ),
        comparacao_disponivel=(recente_com_valor > 0 and baseline_com_valor > 0),
        inclinacao_recente_disponivel=(recente_com_valor >= 2),
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


def _cobertura_memoria_servico(
    nome: str,
    recente: tuple[
        dict[str, Any],
        ...,
    ],
    baseline: tuple[
        dict[str, Any],
        ...,
    ],
) -> CoberturaMetricaNode:
    recente_com_valor = 0
    baseline_com_valor = 0

    for registro in recente:
        servico = _servico_em_registro(
            registro,
            nome,
        )

        if servico is not None and _numero(servico.get("memoria_rss_bytes")) is not None:
            recente_com_valor += 1

    for registro in baseline:
        servico = _servico_em_registro(
            registro,
            nome,
        )

        if servico is not None and _numero(servico.get("memoria_rss_bytes")) is not None:
            baseline_com_valor += 1

    return CoberturaMetricaNode(
        nome="memoria_rss_bytes",
        amostras_com_valor_recente=(recente_com_valor),
        amostras_com_valor_baseline=(baseline_com_valor),
        percentual_presenca_recente=(
            _percentual(
                recente_com_valor,
                len(recente),
            )
        ),
        percentual_presenca_baseline=(
            _percentual(
                baseline_com_valor,
                len(baseline),
            )
        ),
        comparacao_disponivel=(recente_com_valor > 0 and baseline_com_valor > 0),
        inclinacao_recente_disponivel=(recente_com_valor >= 2),
    )


def _qualidade_servicos(
    recente: tuple[
        dict[str, Any],
        ...,
    ],
    baseline: tuple[
        dict[str, Any],
        ...,
    ],
) -> tuple[
    QualidadeServicoNode,
    ...,
]:
    resultado: list[QualidadeServicoNode] = []

    todos = baseline + recente

    for nome in _nomes_servicos(todos):
        obs_recente = sum(
            1
            for registro in recente
            if _servico_em_registro(
                registro,
                nome,
            )
            is not None
        )

        obs_baseline = sum(
            1
            for registro in baseline
            if _servico_em_registro(
                registro,
                nome,
            )
            is not None
        )

        resultado.append(
            QualidadeServicoNode(
                nome=nome,
                amostras_observadas_recente=(obs_recente),
                amostras_observadas_baseline=(obs_baseline),
                percentual_presenca_recente=(
                    _percentual(
                        obs_recente,
                        len(recente),
                    )
                ),
                percentual_presenca_baseline=(
                    _percentual(
                        obs_baseline,
                        len(baseline),
                    )
                ),
                memoria_rss_bytes=(
                    _cobertura_memoria_servico(
                        nome,
                        recente,
                        baseline,
                    )
                ),
            )
        )

    return tuple(resultado)


def analisar_qualidade_dados_node(
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
    *,
    janela_recente_minutos: int = (JANELA_RECENTE_MINUTOS_PADRAO),
    janela_baseline_minutos: int = (JANELA_BASELINE_MINUTOS_PADRAO),
    cadencia_nominal_segundos: float = (CADENCIA_NOMINAL_SEGUNDOS_PADRAO),
    maximo_arquivos: int = (MAXIMO_ARQUIVOS_PADRAO),
    maximo_amostras: int = (MAXIMO_AMOSTRAS_PADRAO),
) -> AnaliseQualidadeDadosNode:
    if janela_recente_minutos <= 0:
        raise ValueError("janela_recente_minutos " "precisa ser maior que zero.")

    if janela_baseline_minutos <= 0:
        raise ValueError("janela_baseline_minutos " "precisa ser maior que zero.")

    if not math.isfinite(cadencia_nominal_segundos) or cadencia_nominal_segundos <= 0:
        raise ValueError("cadencia_nominal_segundos " "precisa ser maior que zero.")

    registros = carregar_historico_node(
        diretorio_historico,
        maximo_arquivos=maximo_arquivos,
        maximo_amostras=maximo_amostras,
    )

    if not registros:
        raise ValueError("Nenhuma amostra valida " "foi encontrada.")

    (
        referencia,
        inicio_recente,
        inicio_baseline,
        recente,
        baseline,
    ) = _selecionar_janelas(
        registros,
        janela_recente_minutos=(janela_recente_minutos),
        janela_baseline_minutos=(janela_baseline_minutos),
    )

    node_ids = [
        registro.get("node_id")
        for registro in registros
        if isinstance(
            registro.get("node_id"),
            str,
        )
    ]

    node_id = node_ids[-1] if node_ids else None

    metricas = (
        _cobertura_metrica(
            "cpu_percentual",
            "cpu_percentual",
            recente,
            baseline,
        ),
        _cobertura_metrica(
            "memoria_host_percentual",
            "memoria_uso_percentual",
            recente,
            baseline,
        ),
        _cobertura_metrica(
            "memoria_processos_projeto_bytes",
            "memoria_processos_projeto_bytes",
            recente,
            baseline,
        ),
        _cobertura_metrica(
            "quantidade_processos_projeto",
            "quantidade_processos_projeto",
            recente,
            baseline,
        ),
    )

    return AnaliseQualidadeDadosNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=(referencia.isoformat()),
        cadencia_nominal_segundos=(cadencia_nominal_segundos),
        janela_recente=_qualidade_janela(
            "recente",
            recente,
            inicio=inicio_recente,
            fim=referencia,
            duracao_minutos=(janela_recente_minutos),
            cadencia_segundos=(cadencia_nominal_segundos),
            inclui_fim=True,
        ),
        janela_baseline=_qualidade_janela(
            "baseline",
            baseline,
            inicio=inicio_baseline,
            fim=inicio_recente,
            duracao_minutos=(janela_baseline_minutos),
            cadencia_segundos=(cadencia_nominal_segundos),
            inclui_fim=False,
        ),
        metricas=metricas,
        servicos=_qualidade_servicos(
            recente,
            baseline,
        ),
    )


def salvar_qualidade_dados_node(
    analise: AnaliseQualidadeDadosNode,
    caminho: str | Path = (CAMINHO_QUALIDADE_PADRAO),
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
