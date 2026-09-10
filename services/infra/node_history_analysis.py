# 63.8738, -149.7525

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

from models.analise_node import (
    AnaliseHistoricoNode,
    ResumoMetricaNode,
    ResumoServicoNode,
)
from services.infra.node_health import DIRETORIO_PROJETO

DIRETORIO_HISTORICO_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "historico"

CAMINHO_ANALISE_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "analise_atual.json"

MAXIMO_ARQUIVOS_PADRAO = 7
MAXIMO_AMOSTRAS_PADRAO = 2016


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
    if not isinstance(
        valor,
        str,
    ):
        return None

    texto = valor.strip()

    if not texto:
        return None

    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        return None


def _resumo(
    valores: list[float],
) -> ResumoMetricaNode:
    if not valores:
        return ResumoMetricaNode(
            atual=None,
            minimo=None,
            maximo=None,
            media=None,
            mediana=None,
            delta_primeira_ultima=None,
            quantidade_amostras=0,
        )

    primeiro = valores[0]
    ultimo = valores[-1]

    return ResumoMetricaNode(
        atual=ultimo,
        minimo=min(valores),
        maximo=max(valores),
        media=statistics.fmean(valores),
        mediana=statistics.median(valores),
        delta_primeira_ultima=(ultimo - primeiro),
        quantidade_amostras=len(valores),
    )


def _carregar_arquivo(
    caminho: Path,
) -> list[dict[str, Any]]:
    registros: list[dict[str, Any]] = []

    try:
        linhas = caminho.read_text(
            encoding="utf-8",
        ).splitlines()
    except (
        OSError,
        UnicodeDecodeError,
    ):
        return registros

    for linha in linhas:
        linha = linha.strip()

        if not linha:
            continue

        try:
            dado = json.loads(linha)
        except json.JSONDecodeError:
            continue

        if not isinstance(
            dado,
            dict,
        ):
            continue

        if _instante(dado.get("coletado_em")) is None:
            continue

        registros.append(dado)

    return registros


def carregar_historico_node(
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
    *,
    maximo_arquivos: int = (MAXIMO_ARQUIVOS_PADRAO),
    maximo_amostras: int = (MAXIMO_AMOSTRAS_PADRAO),
) -> tuple[dict[str, Any], ...]:
    if maximo_arquivos <= 0:
        raise ValueError("maximo_arquivos precisa " "ser maior que zero.")

    if maximo_amostras <= 0:
        raise ValueError("maximo_amostras precisa " "ser maior que zero.")

    diretorio = Path(diretorio_historico)

    if not diretorio.exists():
        return ()

    arquivos = sorted(diretorio.glob("*.jsonl"))

    arquivos = arquivos[-maximo_arquivos:]

    registros: list[dict[str, Any]] = []

    for caminho in arquivos:
        registros.extend(_carregar_arquivo(caminho))

    registros.sort(key=lambda item: (_instante(item.get("coletado_em")) or datetime.min))

    if len(registros) > maximo_amostras:
        registros = registros[-maximo_amostras:]

    return tuple(registros)


def _valores(
    registros: tuple[
        dict[str, Any],
        ...,
    ],
    chave: str,
) -> list[float]:
    resultado: list[float] = []

    for registro in registros:
        numero = _numero(registro.get(chave))

        if numero is not None:
            resultado.append(numero)

    return resultado


def _reinicios_detectados(
    registros: tuple[
        dict[str, Any],
        ...,
    ],
) -> int:
    reinicios = 0
    uptime_anterior: float | None = None

    for registro in registros:
        uptime = _numero(registro.get("uptime_segundos"))

        if uptime is None:
            continue

        if uptime_anterior is not None and uptime < uptime_anterior:
            reinicios += 1

        uptime_anterior = uptime

    return reinicios


def _resumos_servicos(
    registros: tuple[
        dict[str, Any],
        ...,
    ],
) -> tuple[
    ResumoServicoNode,
    ...,
]:
    acumulador: dict[
        str,
        dict[str, Any],
    ] = {}

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

            if not isinstance(
                nome,
                str,
            ):
                continue

            nome = nome.strip()

            if not nome:
                continue

            dados = acumulador.setdefault(
                nome,
                {
                    "observadas": 0,
                    "ativas": 0,
                    "memoria": [],
                },
            )

            dados["observadas"] += 1

            if servico.get("ativo") is True:
                dados["ativas"] += 1

            memoria = _numero(servico.get("memoria_rss_bytes"))

            if memoria is not None:
                dados["memoria"].append(memoria)

    resumos: list[ResumoServicoNode] = []

    for nome in sorted(acumulador):
        dados = acumulador[nome]

        observadas = int(dados["observadas"])

        ativas = int(dados["ativas"])

        disponibilidade = (ativas / observadas) * 100.0 if observadas else None

        resumos.append(
            ResumoServicoNode(
                nome=nome,
                amostras_observadas=(observadas),
                amostras_ativas=ativas,
                percentual_ativo=(disponibilidade),
                memoria_rss_bytes=(_resumo(dados["memoria"])),
            )
        )

    return tuple(resumos)


def analisar_historico_node(
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
    *,
    maximo_arquivos: int = (MAXIMO_ARQUIVOS_PADRAO),
    maximo_amostras: int = (MAXIMO_AMOSTRAS_PADRAO),
) -> AnaliseHistoricoNode:
    registros = carregar_historico_node(
        diretorio_historico,
        maximo_arquivos=(maximo_arquivos),
        maximo_amostras=(maximo_amostras),
    )

    if not registros:
        raise ValueError("Nenhuma amostra valida " "foi encontrada.")

    inicio = registros[0]["coletado_em"]

    fim = registros[-1]["coletado_em"]

    node_ids = [
        registro.get("node_id")
        for registro in registros
        if isinstance(
            registro.get("node_id"),
            str,
        )
    ]

    node_id = node_ids[-1] if node_ids else None

    quantidade_v13 = sum(
        1
        for registro in registros
        if _numero(registro.get("memoria_processos_projeto_bytes")) is not None
    )

    return AnaliseHistoricoNode(
        versao_schema=1,
        node_id=node_id,
        inicio_periodo=inicio,
        fim_periodo=fim,
        quantidade_amostras=len(registros),
        quantidade_amostras_v13=(quantidade_v13),
        reinicios_detectados=(_reinicios_detectados(registros)),
        cpu_percentual=_resumo(
            _valores(
                registros,
                "cpu_percentual",
            )
        ),
        memoria_host_percentual=_resumo(
            _valores(
                registros,
                "memoria_uso_percentual",
            )
        ),
        memoria_processos_projeto_bytes=(
            _resumo(
                _valores(
                    registros,
                    "memoria_processos_projeto_bytes",
                )
            )
        ),
        quantidade_processos_projeto=(
            _resumo(
                _valores(
                    registros,
                    "quantidade_processos_projeto",
                )
            )
        ),
        servicos=_resumos_servicos(registros),
    )


def salvar_analise_node(
    analise: AnaliseHistoricoNode,
    caminho: str | Path = (CAMINHO_ANALISE_PADRAO),
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
