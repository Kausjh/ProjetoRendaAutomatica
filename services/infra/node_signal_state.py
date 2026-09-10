# 63.8738, -149.7525

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from models.estado_temporal_sinais import (
    EstadoTemporalSinaisNode,
    EstadoTemporalSinalNode,
)
from models.sinais_node import (
    AnaliseSinaisNode,
)
from services.infra.node_health import (
    DIRETORIO_PROJETO,
)

CAMINHO_ESTADO_TEMPORAL_SINAIS_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "sinais_estado_atual.json"
)

DIRETORIO_HISTORICO_TEMPORAL_SINAIS_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "historico_sinais"
)


def _registro_de_dict(
    dados: dict[str, Any],
) -> EstadoTemporalSinalNode | None:
    codigo = dados.get("codigo")

    origem = dados.get("origem")

    titulo = dados.get("titulo")

    primeira = dados.get("primeira_observacao")

    ultima = dados.get("ultima_observacao")

    if not all(
        isinstance(valor, str) and valor
        for valor in (
            codigo,
            origem,
            titulo,
            primeira,
            ultima,
        )
    ):
        return None

    inicio = dados.get("inicio_sequencia_atual")

    if not isinstance(
        inicio,
        str,
    ):
        inicio = None

    deixou = dados.get("deixou_de_ser_observado_em")

    if not isinstance(
        deixou,
        str,
    ):
        deixou = None

    observado = dados.get("observado_agora")

    if not isinstance(
        observado,
        bool,
    ):
        return None

    consecutivas = dados.get("observacoes_consecutivas")

    totais = dados.get("observacoes_totais")

    ausentes = dados.get("ciclos_ausente_consecutivos")

    if not all(
        isinstance(valor, int) and valor >= 0
        for valor in (
            consecutivas,
            totais,
            ausentes,
        )
    ):
        return None

    transicao = dados.get("transicao_ultimo_ciclo")

    if not isinstance(
        transicao,
        str,
    ):
        return None

    evidencias = dados.get("evidencias_mais_recentes")

    if not isinstance(
        evidencias,
        dict,
    ):
        evidencias = {}

    return EstadoTemporalSinalNode(
        codigo=codigo,
        origem=origem,
        titulo=titulo,
        primeira_observacao=primeira,
        inicio_sequencia_atual=inicio,
        ultima_observacao=ultima,
        observado_agora=observado,
        observacoes_consecutivas=consecutivas,
        observacoes_totais=totais,
        ciclos_ausente_consecutivos=ausentes,
        deixou_de_ser_observado_em=deixou,
        transicao_ultimo_ciclo=transicao,
        evidencias_mais_recentes=evidencias,
    )


def carregar_estado_temporal_sinais(
    caminho: str | Path,
) -> EstadoTemporalSinaisNode | None:
    caminho = Path(caminho)

    if not caminho.exists():
        return None

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (
        OSError,
        json.JSONDecodeError,
    ) as erro:
        raise ValueError("Estado temporal de sinais invalido.") from erro

    if not isinstance(
        dados,
        dict,
    ):
        raise ValueError("Estado temporal de sinais invalido.")

    referencia = dados.get("referencia_temporal")

    if not isinstance(
        referencia,
        str,
    ):
        raise ValueError("Referencia temporal invalida.")

    node_id = dados.get("node_id")

    if not isinstance(
        node_id,
        str,
    ):
        node_id = None

    sinais_dados = dados.get(
        "sinais",
        [],
    )

    if not isinstance(
        sinais_dados,
        list,
    ):
        sinais_dados = []

    sinais = []

    for item in sinais_dados:
        if not isinstance(
            item,
            dict,
        ):
            continue

        registro = _registro_de_dict(item)

        if registro is not None:
            sinais.append(registro)

    return EstadoTemporalSinaisNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=referencia,
        sinais=tuple(sinais),
    )


def atualizar_estado_temporal_sinais(
    analise: AnaliseSinaisNode,
    estado_anterior: EstadoTemporalSinaisNode | None = None,
) -> EstadoTemporalSinaisNode:
    referencia = analise.referencia_temporal

    if (
        not isinstance(
            referencia,
            str,
        )
        or not referencia
    ):
        raise ValueError("Analise de sinais sem " "referencia temporal valida.")

    if estado_anterior is not None and estado_anterior.node_id != analise.node_id:
        estado_anterior = None

    anteriores = {}

    if estado_anterior is not None:
        anteriores = {sinal.codigo: sinal for sinal in estado_anterior.sinais}

    atuais = {}

    for sinal in analise.sinais:
        if sinal.codigo in atuais:
            raise ValueError("Codigo de sinal duplicado: " f"{sinal.codigo}")

        atuais[sinal.codigo] = sinal

    codigos = sorted(set(anteriores) | set(atuais))

    resultado = []

    for codigo in codigos:
        anterior = anteriores.get(codigo)

        atual = atuais.get(codigo)

        if atual is not None:
            if anterior is None:
                registro = EstadoTemporalSinalNode(
                    codigo=codigo,
                    origem=atual.origem,
                    titulo=atual.titulo,
                    primeira_observacao=referencia,
                    inicio_sequencia_atual=referencia,
                    ultima_observacao=referencia,
                    observado_agora=True,
                    observacoes_consecutivas=1,
                    observacoes_totais=1,
                    ciclos_ausente_consecutivos=0,
                    deixou_de_ser_observado_em=None,
                    transicao_ultimo_ciclo=("novo"),
                    evidencias_mais_recentes=dict(atual.evidencias),
                )

            elif anterior.observado_agora:
                registro = EstadoTemporalSinalNode(
                    codigo=codigo,
                    origem=atual.origem,
                    titulo=atual.titulo,
                    primeira_observacao=(anterior.primeira_observacao),
                    inicio_sequencia_atual=(anterior.inicio_sequencia_atual or referencia),
                    ultima_observacao=referencia,
                    observado_agora=True,
                    observacoes_consecutivas=(anterior.observacoes_consecutivas + 1),
                    observacoes_totais=(anterior.observacoes_totais + 1),
                    ciclos_ausente_consecutivos=0,
                    deixou_de_ser_observado_em=None,
                    transicao_ultimo_ciclo=("continua_observado"),
                    evidencias_mais_recentes=dict(atual.evidencias),
                )

            else:
                registro = EstadoTemporalSinalNode(
                    codigo=codigo,
                    origem=atual.origem,
                    titulo=atual.titulo,
                    primeira_observacao=(anterior.primeira_observacao),
                    inicio_sequencia_atual=referencia,
                    ultima_observacao=referencia,
                    observado_agora=True,
                    observacoes_consecutivas=1,
                    observacoes_totais=(anterior.observacoes_totais + 1),
                    ciclos_ausente_consecutivos=0,
                    deixou_de_ser_observado_em=None,
                    transicao_ultimo_ciclo=("reapareceu"),
                    evidencias_mais_recentes=dict(atual.evidencias),
                )

        else:
            if anterior is None:
                continue

            if anterior.observado_agora:
                transicao = "deixou_de_ser_observado"

                deixou = referencia

                ciclos_ausente = 1

            else:
                transicao = "continua_nao_observado"

                deixou = anterior.deixou_de_ser_observado_em

                ciclos_ausente = anterior.ciclos_ausente_consecutivos + 1

            registro = EstadoTemporalSinalNode(
                codigo=anterior.codigo,
                origem=anterior.origem,
                titulo=anterior.titulo,
                primeira_observacao=(anterior.primeira_observacao),
                inicio_sequencia_atual=None,
                ultima_observacao=(anterior.ultima_observacao),
                observado_agora=False,
                observacoes_consecutivas=0,
                observacoes_totais=(anterior.observacoes_totais),
                ciclos_ausente_consecutivos=(ciclos_ausente),
                deixou_de_ser_observado_em=deixou,
                transicao_ultimo_ciclo=transicao,
                evidencias_mais_recentes=(anterior.evidencias_mais_recentes),
            )

        resultado.append(registro)

    return EstadoTemporalSinaisNode(
        versao_schema=1,
        node_id=analise.node_id,
        referencia_temporal=referencia,
        sinais=tuple(resultado),
    )


def salvar_estado_temporal_sinais(
    estado: EstadoTemporalSinaisNode,
    caminho: str | Path,
) -> Path:
    caminho = Path(caminho)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporario = caminho.with_suffix(caminho.suffix + ".tmp")

    temporario.write_text(
        json.dumps(
            estado.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporario.replace(caminho)

    return caminho


def registrar_historico_temporal_sinais(
    estado: EstadoTemporalSinaisNode,
    diretorio: str | Path,
) -> Path:
    diretorio = Path(diretorio)

    try:
        instante = datetime.fromisoformat(estado.referencia_temporal)
    except ValueError as erro:
        raise ValueError("Referencia temporal " "possui formato invalido.") from erro

    caminho = diretorio / (instante.date().isoformat() + ".jsonl")

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with caminho.open(
        "a",
        encoding="utf-8",
    ) as arquivo:
        arquivo.write(
            json.dumps(
                estado.para_dict(),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

        arquivo.write("\n")

    return caminho


def persistir_estado_temporal_sinais(
    analise: AnaliseSinaisNode,
    *,
    caminho_estado: str | Path = (CAMINHO_ESTADO_TEMPORAL_SINAIS_PADRAO),
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_TEMPORAL_SINAIS_PADRAO),
) -> EstadoTemporalSinaisNode:
    anterior = carregar_estado_temporal_sinais(caminho_estado)

    atual = atualizar_estado_temporal_sinais(
        analise,
        anterior,
    )

    salvar_estado_temporal_sinais(
        atual,
        caminho_estado,
    )

    registrar_historico_temporal_sinais(
        atual,
        diretorio_historico,
    )

    return atual
