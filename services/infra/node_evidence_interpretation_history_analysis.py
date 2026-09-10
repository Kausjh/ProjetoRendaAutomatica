# 63.8738, -149.7525

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.analise_historico_interpretacoes_node import (
    AnaliseHistoricaInterpretacaoNode,
    AnaliseHistoricoInterpretacoesNode,
    IntervaloInterpretacaoNode,
)
from services.infra.node_health import DIRETORIO_PROJETO

DIRETORIO_HISTORICO_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "historico_interpretacoes"

CAMINHO_ANALISE_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "analise_historico_interpretacoes_atual.json"
)


def _instante(
    valor: object,
) -> datetime:
    if (
        not isinstance(
            valor,
            str,
        )
        or not valor
    ):
        raise ValueError("Referencia temporal invalida.")

    texto = valor

    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"

    try:
        instante = datetime.fromisoformat(texto)

    except ValueError as erro:
        raise ValueError("Referencia temporal invalida.") from erro

    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)

    return instante.astimezone(UTC)


def _texto(
    valor: object,
) -> str | None:
    if (
        isinstance(
            valor,
            str,
        )
        and valor
    ):
        return valor

    return None


def _lista_dicts(
    valor: object,
) -> list[dict[str, Any]]:
    if not isinstance(
        valor,
        list,
    ):
        return []

    return [
        item
        for item in valor
        if isinstance(
            item,
            dict,
        )
    ]


def _normalizar_registro(
    registro: dict[str, Any],
) -> dict[str, Any]:
    normalizado = dict(registro)

    referencia = registro.get("referencia_temporal")

    normalizado["referencia_temporal"] = _instante(referencia).isoformat()

    return normalizado


def _carregar_registros(
    diretorio: str | Path,
) -> list[dict[str, Any]]:
    diretorio = Path(diretorio)

    registros: list[dict[str, Any]] = []

    if not diretorio.exists():
        raise ValueError("Historico de interpretacoes inexistente.")

    for caminho in sorted(diretorio.glob("*.jsonl")):
        try:
            linhas = caminho.read_text(encoding="utf-8").splitlines()

        except OSError:
            continue

        for linha in linhas:
            if not linha.strip():
                continue

            try:
                registro = json.loads(linha)

            except json.JSONDecodeError:
                continue

            if not isinstance(
                registro,
                dict,
            ):
                continue

            node_id = _texto(registro.get("node_id"))

            referencia = _texto(registro.get("referencia_temporal"))

            if node_id is None or referencia is None:
                continue

            try:
                _instante(referencia)

            except ValueError:
                continue

            registros.append(registro)

    if not registros:
        raise ValueError("Nenhum registro temporal valido encontrado.")

    registros.sort(key=lambda item: _instante(item["referencia_temporal"]))

    node_mais_recente = registros[-1]["node_id"]

    registros = [registro for registro in registros if registro.get("node_id") == node_mais_recente]

    unicos: list[dict[str, Any]] = []

    por_instante: dict[
        datetime,
        dict[str, Any],
    ] = {}

    for registro in registros:
        instante = _instante(registro["referencia_temporal"])

        existente = por_instante.get(instante)

        if existente is None:
            por_instante[instante] = registro

            unicos.append(registro)

            continue

        if _normalizar_registro(existente) != _normalizar_registro(registro):
            raise ValueError("Historico possui estados diferentes " "para o mesmo instante.")

    unicos.sort(key=lambda item: _instante(item["referencia_temporal"]))

    return unicos


def _observacoes_registro(
    registro: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    resultado: dict[
        str,
        dict[str, Any],
    ] = {}

    for item in _lista_dicts(registro.get("observacoes")):
        codigo = _texto(item.get("codigo"))

        if codigo is None:
            continue

        if codigo in resultado:
            raise ValueError("Registro possui codigo de observacao duplicado.")

        observado = item.get("observado_agora")

        if not isinstance(
            observado,
            bool,
        ):
            continue

        resultado[codigo] = item

    return resultado


def _inicio_confirmado(
    item: dict[str, Any],
    observado: bool,
) -> bool:
    transicao = item.get("transicao_ultimo_ciclo")

    if observado:
        return transicao in {
            "novo",
            "reapareceu",
        }

    return transicao == "deixou_de_ser_observado"


def _intervalo(
    *,
    inicio: str,
    fim: str,
    inicio_confirmado: bool,
    fim_confirmado: bool,
) -> IntervaloInterpretacaoNode:
    duracao = (_instante(fim) - _instante(inicio)).total_seconds()

    return IntervaloInterpretacaoNode(
        inicio=inicio,
        fim=fim,
        inicio_confirmado=(inicio_confirmado),
        fim_confirmado=(fim_confirmado),
        duracao_acompanhada_segundos=max(
            0.0,
            duracao,
        ),
    )


def _analisar_codigo(
    codigo: str,
    eventos: list[
        tuple[
            str,
            bool,
            dict[str, Any],
        ]
    ],
) -> AnaliseHistoricaInterpretacaoNode:
    eventos.sort(key=lambda item: _instante(item[0]))

    ultimo_item = eventos[-1][2]

    categoria = _texto(ultimo_item.get("categoria")) or ""

    sujeito = _texto(ultimo_item.get("sujeito")) or codigo

    descricao = _texto(ultimo_item.get("descricao")) or ""

    episodios: list[IntervaloInterpretacaoNode] = []

    ausencias: list[IntervaloInterpretacaoNode] = []

    estado_atual: bool | None = None
    inicio_estado: str | None = None
    inicio_estado_confirmado = False

    ultima_referencia = eventos[0][0]

    for (
        referencia,
        observado,
        item,
    ) in eventos:
        if estado_atual is None:
            estado_atual = observado
            inicio_estado = referencia

            inicio_estado_confirmado = _inicio_confirmado(
                item,
                observado,
            )

            ultima_referencia = referencia

            continue

        if observado == estado_atual:
            ultima_referencia = referencia

            continue

        assert inicio_estado is not None

        fechado = _intervalo(
            inicio=inicio_estado,
            fim=referencia,
            inicio_confirmado=(inicio_estado_confirmado),
            fim_confirmado=True,
        )

        if estado_atual:
            episodios.append(fechado)
        else:
            ausencias.append(fechado)

        estado_atual = observado
        inicio_estado = referencia
        inicio_estado_confirmado = True
        ultima_referencia = referencia

    assert estado_atual is not None
    assert inicio_estado is not None

    aberto = _intervalo(
        inicio=inicio_estado,
        fim=ultima_referencia,
        inicio_confirmado=(inicio_estado_confirmado),
        fim_confirmado=False,
    )

    if estado_atual:
        episodios.append(aberto)
    else:
        ausencias.append(aberto)

    episodio_atual_aberto = estado_atual is True

    ausencia_atual_aberta = estado_atual is False

    duracao_episodio_atual = (
        episodios[-1].duracao_acompanhada_segundos if episodio_atual_aberto and episodios else None
    )

    duracao_ausencia_atual = (
        ausencias[-1].duracao_acompanhada_segundos if ausencia_atual_aberta and ausencias else None
    )

    maior_observada = (
        max(item.duracao_acompanhada_segundos for item in episodios) if episodios else None
    )

    maior_ausencia = (
        max(item.duracao_acompanhada_segundos for item in ausencias) if ausencias else None
    )

    return AnaliseHistoricaInterpretacaoNode(
        codigo=codigo,
        categoria=categoria,
        sujeito=sujeito,
        descricao=descricao,
        primeira_referencia=eventos[0][0],
        ultima_referencia=eventos[-1][0],
        observado_agora=estado_atual,
        observacoes_explicitas=len(eventos),
        quantidade_episodios_observados=len(episodios),
        reaparecimentos=max(
            0,
            len(episodios) - 1,
        ),
        quantidade_periodos_ausentes=len(ausencias),
        episodio_atual_aberto=(episodio_atual_aberto),
        periodo_ausencia_atual_aberto=(ausencia_atual_aberta),
        duracao_episodio_atual_segundos=(duracao_episodio_atual),
        duracao_ausencia_atual_segundos=(duracao_ausencia_atual),
        maior_duracao_observada_segundos=(maior_observada),
        maior_duracao_ausencia_segundos=(maior_ausencia),
        episodios_observados=tuple(episodios),
        periodos_ausentes=tuple(ausencias),
    )


def analisar_historico_interpretacoes_node(
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
) -> AnaliseHistoricoInterpretacoesNode:
    registros = _carregar_registros(diretorio_historico)

    eventos_por_codigo: dict[
        str,
        list[
            tuple[
                str,
                bool,
                dict[str, Any],
            ]
        ],
    ] = {}

    for registro in registros:
        referencia = registro["referencia_temporal"]

        for (
            codigo,
            item,
        ) in _observacoes_registro(registro).items():
            eventos_por_codigo.setdefault(
                codigo,
                [],
            ).append(
                (
                    referencia,
                    item["observado_agora"],
                    item,
                )
            )

    interpretacoes = tuple(
        _analisar_codigo(
            codigo,
            eventos,
        )
        for codigo, eventos in sorted(eventos_por_codigo.items())
    )

    if not interpretacoes:
        raise ValueError("Nenhuma interpretacao historica valida encontrada.")

    return AnaliseHistoricoInterpretacoesNode(
        versao_schema=1,
        node_id=registros[-1]["node_id"],
        inicio_periodo=registros[0]["referencia_temporal"],
        fim_periodo=registros[-1]["referencia_temporal"],
        quantidade_registros=len(registros),
        quantidade_interpretacoes=len(interpretacoes),
        interpretacoes=interpretacoes,
    )


def salvar_analise_historico_interpretacoes_node(
    analise: AnaliseHistoricoInterpretacoesNode,
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
