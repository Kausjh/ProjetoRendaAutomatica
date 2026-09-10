# 63.8738, -149.7525

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.estado_interpretacao_evidencias_node import (
    EstadoInterpretacaoEvidenciasNode,
    EstadoObservacaoInterpretacaoNode,
)
from services.infra.node_health import DIRETORIO_PROJETO

CAMINHO_INTERPRETACAO_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "interpretacao_evidencias_atual.json"
)

CAMINHO_ESTADO_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "interpretacao_estado_atual.json"

DIRETORIO_HISTORICO_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "historico_interpretacoes"


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


def _carregar_json(
    caminho: str | Path,
    *,
    obrigatorio: bool,
) -> dict[str, Any] | None:
    caminho = Path(caminho)

    if not caminho.exists():
        if obrigatorio:
            raise ValueError(f"Artefato ausente: {caminho}")

        return None

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))

    except (
        OSError,
        json.JSONDecodeError,
    ) as erro:
        raise ValueError(f"Artefato invalido: {caminho}") from erro

    if not isinstance(
        dados,
        dict,
    ):
        raise ValueError(f"Artefato invalido: {caminho}")

    return dados


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


def _texto(
    valor: object,
    *,
    nome: str,
) -> str:
    if (
        not isinstance(
            valor,
            str,
        )
        or not valor
    ):
        raise ValueError(f"{nome} invalido.")

    return valor


def _inteiro(
    valor: object,
    *,
    padrao: int = 0,
) -> int:
    if isinstance(
        valor,
        int,
    ) and not isinstance(
        valor,
        bool,
    ):
        return valor

    return padrao


def _fontes(
    valor: object,
) -> tuple[str, ...]:
    if not isinstance(
        valor,
        list,
    ):
        return ()

    return tuple(
        item
        for item in valor
        if isinstance(
            item,
            str,
        )
        and item
    )


def _dados(
    valor: object,
) -> dict[str, Any]:
    if not isinstance(
        valor,
        dict,
    ):
        return {}

    return dict(valor)


def _mapa_observacoes_atuais(
    interpretacao: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    resultado: dict[
        str,
        dict[str, Any],
    ] = {}

    for item in _lista_dicts(interpretacao.get("observacoes")):
        codigo = _texto(
            item.get("codigo"),
            nome="Codigo da observacao",
        )

        if codigo in resultado:
            raise ValueError("Codigo de observacao duplicado " "na mesma interpretacao.")

        resultado[codigo] = item

    return resultado


def _mapa_estado_anterior(
    estado: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if estado is None:
        return {}

    resultado: dict[
        str,
        dict[str, Any],
    ] = {}

    for item in _lista_dicts(estado.get("observacoes")):
        codigo = item.get("codigo")

        if (
            not isinstance(
                codigo,
                str,
            )
            or not codigo
        ):
            continue

        resultado[codigo] = item

    return resultado


def _snapshot_atual_equivale_estado(
    atuais: dict[str, dict[str, Any]],
    anteriores: dict[str, dict[str, Any]],
) -> bool:
    codigos_anteriores_observados = {
        codigo for codigo, item in anteriores.items() if item.get("observado_agora") is True
    }

    if set(atuais) != codigos_anteriores_observados:
        return False

    for codigo, atual in atuais.items():
        anterior = anteriores[codigo]

        if atual.get("categoria") != anterior.get("categoria"):
            return False

        if atual.get("sujeito") != anterior.get("sujeito"):
            return False

        if atual.get("descricao") != anterior.get("descricao"):
            return False

        if _dados(atual.get("dados")) != _dados(anterior.get("dados_mais_recentes")):
            return False

        if _fontes(atual.get("fontes")) != _fontes(anterior.get("fontes_mais_recentes")):
            return False

    return True


def _construir_estado(
    *,
    node_id: str,
    referencia_temporal: str,
    atuais: dict[str, dict[str, Any]],
    anteriores: dict[str, dict[str, Any]],
) -> EstadoInterpretacaoEvidenciasNode:
    resultado = []

    codigos = sorted(set(atuais) | set(anteriores))

    for codigo in codigos:
        atual = atuais.get(codigo)

        anterior = anteriores.get(codigo)

        if atual is not None:
            categoria = _texto(
                atual.get("categoria"),
                nome="Categoria",
            )

            sujeito = _texto(
                atual.get("sujeito"),
                nome="Sujeito",
            )

            descricao = _texto(
                atual.get("descricao"),
                nome="Descricao",
            )

            dados_recentes = _dados(atual.get("dados"))

            fontes_recentes = _fontes(atual.get("fontes"))

            if anterior is None:
                primeira = referencia_temporal

                inicio_sequencia = referencia_temporal

                consecutivas = 1
                totais = 1
                transicao = "novo"

            elif anterior.get("observado_agora") is True:
                primeira = _texto(
                    anterior.get("primeira_observacao"),
                    nome="Primeira observacao",
                )

                inicio_sequencia = _texto(
                    anterior.get("inicio_sequencia_atual"),
                    nome="Inicio da sequencia",
                )

                consecutivas = _inteiro(anterior.get("observacoes_consecutivas")) + 1

                totais = _inteiro(anterior.get("observacoes_totais")) + 1

                transicao = "continua_observado"

            else:
                primeira = _texto(
                    anterior.get("primeira_observacao"),
                    nome="Primeira observacao",
                )

                inicio_sequencia = referencia_temporal

                consecutivas = 1

                totais = _inteiro(anterior.get("observacoes_totais")) + 1

                transicao = "reapareceu"

            resultado.append(
                EstadoObservacaoInterpretacaoNode(
                    codigo=codigo,
                    categoria=categoria,
                    sujeito=sujeito,
                    descricao=descricao,
                    primeira_observacao=primeira,
                    inicio_sequencia_atual=(inicio_sequencia),
                    ultima_observacao=(referencia_temporal),
                    observado_agora=True,
                    observacoes_consecutivas=(consecutivas),
                    observacoes_totais=totais,
                    ciclos_ausente_consecutivos=0,
                    deixou_de_ser_observado_em=None,
                    transicao_ultimo_ciclo=(transicao),
                    dados_mais_recentes=(dados_recentes),
                    fontes_mais_recentes=(fontes_recentes),
                )
            )

            continue

        if anterior is None:
            continue

        categoria = _texto(
            anterior.get("categoria"),
            nome="Categoria anterior",
        )

        sujeito = _texto(
            anterior.get("sujeito"),
            nome="Sujeito anterior",
        )

        descricao = _texto(
            anterior.get("descricao"),
            nome="Descricao anterior",
        )

        primeira = _texto(
            anterior.get("primeira_observacao"),
            nome="Primeira observacao",
        )

        inicio_sequencia = _texto(
            anterior.get("inicio_sequencia_atual"),
            nome="Inicio da sequencia",
        )

        ultima = _texto(
            anterior.get("ultima_observacao"),
            nome="Ultima observacao",
        )

        estava_observado = anterior.get("observado_agora") is True

        if estava_observado:
            ausentes = 1
            deixou_em = referencia_temporal
            transicao = "deixou_de_ser_observado"

        else:
            ausentes = _inteiro(anterior.get("ciclos_ausente_consecutivos")) + 1

            deixou_em = anterior.get("deixou_de_ser_observado_em")

            if not isinstance(
                deixou_em,
                str,
            ):
                deixou_em = None

            transicao = "continua_nao_observado"

        resultado.append(
            EstadoObservacaoInterpretacaoNode(
                codigo=codigo,
                categoria=categoria,
                sujeito=sujeito,
                descricao=descricao,
                primeira_observacao=primeira,
                inicio_sequencia_atual=(inicio_sequencia),
                ultima_observacao=ultima,
                observado_agora=False,
                observacoes_consecutivas=0,
                observacoes_totais=_inteiro(anterior.get("observacoes_totais")),
                ciclos_ausente_consecutivos=(ausentes),
                deixou_de_ser_observado_em=(deixou_em),
                transicao_ultimo_ciclo=(transicao),
                dados_mais_recentes=_dados(anterior.get("dados_mais_recentes")),
                fontes_mais_recentes=_fontes(anterior.get("fontes_mais_recentes")),
            )
        )

    quantidade_agora = sum(1 for item in resultado if item.observado_agora)

    return EstadoInterpretacaoEvidenciasNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=(referencia_temporal),
        quantidade_observacoes_conhecidas=len(resultado),
        quantidade_observadas_agora=(quantidade_agora),
        observacoes=tuple(resultado),
    )


def _salvar_estado_atomico(
    estado: EstadoInterpretacaoEvidenciasNode,
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


def _caminho_historico(
    diretorio: str | Path,
    referencia_temporal: str,
) -> Path:
    instante = _instante(referencia_temporal)

    return Path(diretorio) / f"{instante.date().isoformat()}.jsonl"


def _garantir_historico(
    estado: EstadoInterpretacaoEvidenciasNode,
    diretorio: str | Path,
) -> Path:
    caminho = _caminho_historico(
        diretorio,
        estado.referencia_temporal,
    )

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    atual = estado.para_dict()

    if caminho.exists():
        linhas = [
            linha for linha in caminho.read_text(encoding="utf-8").splitlines() if linha.strip()
        ]

        for linha in reversed(linhas):
            try:
                registro = json.loads(linha)

            except json.JSONDecodeError:
                continue

            if not isinstance(
                registro,
                dict,
            ):
                continue

            if registro.get("node_id") != estado.node_id:
                continue

            referencia = registro.get("referencia_temporal")

            if not isinstance(
                referencia,
                str,
            ):
                continue

            if _instante(referencia) != _instante(estado.referencia_temporal):
                continue

            comparavel = dict(registro)

            comparavel["referencia_temporal"] = estado.referencia_temporal

            if comparavel != atual:
                raise ValueError("Historico contem estado diferente " "para o mesmo instante.")

            return caminho

    with caminho.open(
        "a",
        encoding="utf-8",
    ) as arquivo:
        arquivo.write(
            json.dumps(
                atual,
                ensure_ascii=False,
            )
            + "\n"
        )

    return caminho


def persistir_estado_interpretacao_evidencias_node(
    caminho_interpretacao: str | Path = (CAMINHO_INTERPRETACAO_PADRAO),
    *,
    caminho_estado: str | Path = (CAMINHO_ESTADO_PADRAO),
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
) -> EstadoInterpretacaoEvidenciasNode:
    interpretacao = _carregar_json(
        caminho_interpretacao,
        obrigatorio=True,
    )

    assert interpretacao is not None

    node_id = _texto(
        interpretacao.get("node_id"),
        nome="Node ID",
    )

    referencia_temporal = _texto(
        interpretacao.get("referencia_temporal"),
        nome="Referencia temporal",
    )

    instante_atual = _instante(referencia_temporal)

    atuais = _mapa_observacoes_atuais(interpretacao)

    estado_anterior = _carregar_json(
        caminho_estado,
        obrigatorio=False,
    )

    if estado_anterior is not None and estado_anterior.get("node_id") != node_id:
        estado_anterior = None

    anteriores = _mapa_estado_anterior(estado_anterior)

    if estado_anterior is not None:
        referencia_anterior = _texto(
            estado_anterior.get("referencia_temporal"),
            nome="Referencia temporal anterior",
        )

        instante_anterior = _instante(referencia_anterior)

        if instante_atual < instante_anterior:
            raise ValueError("Interpretacao temporal mais antiga " "que o estado persistido.")

        if instante_atual == instante_anterior:
            if not _snapshot_atual_equivale_estado(
                atuais,
                anteriores,
            ):
                raise ValueError("Interpretacao inconsistente " "para o mesmo instante.")

            estado = _construir_estado_existente(estado_anterior)

            _garantir_historico(
                estado,
                diretorio_historico,
            )

            return estado

    estado = _construir_estado(
        node_id=node_id,
        referencia_temporal=(referencia_temporal),
        atuais=atuais,
        anteriores=anteriores,
    )

    _salvar_estado_atomico(
        estado,
        caminho_estado,
    )

    _garantir_historico(
        estado,
        diretorio_historico,
    )

    return estado


def _construir_estado_existente(
    dados: dict[str, Any],
) -> EstadoInterpretacaoEvidenciasNode:
    observacoes = []

    for item in _lista_dicts(dados.get("observacoes")):
        observacoes.append(
            EstadoObservacaoInterpretacaoNode(
                codigo=_texto(
                    item.get("codigo"),
                    nome="Codigo",
                ),
                categoria=_texto(
                    item.get("categoria"),
                    nome="Categoria",
                ),
                sujeito=_texto(
                    item.get("sujeito"),
                    nome="Sujeito",
                ),
                descricao=_texto(
                    item.get("descricao"),
                    nome="Descricao",
                ),
                primeira_observacao=_texto(
                    item.get("primeira_observacao"),
                    nome="Primeira observacao",
                ),
                inicio_sequencia_atual=_texto(
                    item.get("inicio_sequencia_atual"),
                    nome="Inicio da sequencia",
                ),
                ultima_observacao=_texto(
                    item.get("ultima_observacao"),
                    nome="Ultima observacao",
                ),
                observado_agora=(item.get("observado_agora") is True),
                observacoes_consecutivas=_inteiro(item.get("observacoes_consecutivas")),
                observacoes_totais=_inteiro(item.get("observacoes_totais")),
                ciclos_ausente_consecutivos=_inteiro(item.get("ciclos_ausente_consecutivos")),
                deixou_de_ser_observado_em=(
                    item.get("deixou_de_ser_observado_em")
                    if isinstance(
                        item.get("deixou_de_ser_observado_em"),
                        str,
                    )
                    else None
                ),
                transicao_ultimo_ciclo=_texto(
                    item.get("transicao_ultimo_ciclo"),
                    nome="Transicao",
                ),
                dados_mais_recentes=_dados(item.get("dados_mais_recentes")),
                fontes_mais_recentes=_fontes(item.get("fontes_mais_recentes")),
            )
        )

    return EstadoInterpretacaoEvidenciasNode(
        versao_schema=_inteiro(
            dados.get("versao_schema"),
            padrao=1,
        ),
        node_id=_texto(
            dados.get("node_id"),
            nome="Node ID",
        ),
        referencia_temporal=_texto(
            dados.get("referencia_temporal"),
            nome="Referencia temporal",
        ),
        quantidade_observacoes_conhecidas=len(observacoes),
        quantidade_observadas_agora=sum(1 for item in observacoes if item.observado_agora),
        observacoes=tuple(observacoes),
    )
