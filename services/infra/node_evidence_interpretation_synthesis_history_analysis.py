# 63.8738, -149.7525

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.analise_historico_sinteses_interpretacoes_node import (
    AnaliseHistoricoSintesesInterpretacoesNode,
    EvolucaoCicloSinteseInterpretacoesNode,
    HistoricoSinteseInterpretacaoNode,
)
from services.infra.node_health import DIRETORIO_PROJETO

DIRETORIO_HISTORICO_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "historico_sinteses_interpretacoes"
)

CAMINHO_SAIDA_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "analise_historico_sinteses_interpretacoes_atual.json"
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


def _inteiro(
    valor: object,
    *,
    nome: str,
) -> int:
    if (
        isinstance(
            valor,
            bool,
        )
        or not isinstance(
            valor,
            int,
        )
        or valor < 0
    ):
        raise ValueError(f"{nome} invalido.")

    return valor


def _numero(
    valor: object,
    *,
    nome: str,
) -> float:
    if isinstance(
        valor,
        bool,
    ) or not isinstance(
        valor,
        (
            int,
            float,
        ),
    ):
        raise ValueError(f"{nome} invalido.")

    numero = float(valor)

    if not math.isfinite(numero):
        raise ValueError(f"{nome} invalido.")

    return numero


def _normalizar_temporais(
    valor: Any,
) -> Any:
    if isinstance(
        valor,
        dict,
    ):
        resultado = {}

        for chave, item in valor.items():
            if (
                chave
                in {
                    "referencia_temporal",
                    "primeira_evidencia",
                    "ultima_evidencia",
                }
                and isinstance(
                    item,
                    str,
                )
                and item
            ):
                resultado[chave] = _instante(item).isoformat()

            else:
                resultado[chave] = _normalizar_temporais(item)

        return resultado

    if isinstance(
        valor,
        list,
    ):
        return [_normalizar_temporais(item) for item in valor]

    return valor


def _lista_codigos(
    valor: object,
    *,
    nome: str,
    universo: set[str],
) -> tuple[str, ...]:
    if not isinstance(
        valor,
        list,
    ):
        raise ValueError(f"{nome} invalida.")

    codigos = []

    for item in valor:
        if (
            not isinstance(
                item,
                str,
            )
            or not item
        ):
            raise ValueError(f"{nome} invalida.")

        codigos.append(item)

    if len(codigos) != len(set(codigos)):
        raise ValueError(f"{nome} possui duplicatas.")

    if not set(codigos).issubset(universo):
        raise ValueError(f"{nome} possui codigo desconhecido.")

    return tuple(codigos)


def _validar_registro(
    registro: dict[str, Any],
) -> dict[str, Any]:
    normalizado = _normalizar_temporais(registro)

    node_id = normalizado.get("node_id")

    if (
        not isinstance(
            node_id,
            str,
        )
        or not node_id
    ):
        raise ValueError("Node ID invalido.")

    normalizado["referencia_temporal"] = _instante(
        normalizado.get("referencia_temporal")
    ).isoformat()

    quantidade = _inteiro(
        normalizado.get("quantidade_interpretacoes"),
        nome="Quantidade de interpretacoes",
    )

    interpretacoes = normalizado.get("interpretacoes")

    if not isinstance(
        interpretacoes,
        list,
    ):
        raise ValueError("Interpretacoes invalidas.")

    if len(interpretacoes) != quantidade:
        raise ValueError("Quantidade de interpretacoes inconsistente.")

    mapa = {}

    for item in interpretacoes:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError("Interpretacao invalida.")

        codigo = item.get("codigo")

        if (
            not isinstance(
                codigo,
                str,
            )
            or not codigo
        ):
            raise ValueError("Codigo de interpretacao invalido.")

        if codigo in mapa:
            raise ValueError("Codigo de interpretacao duplicado.")

        observado = item.get("observado_agora")

        if not isinstance(
            observado,
            bool,
        ):
            raise ValueError("Estado observado invalido.")

        reaparecimentos = _inteiro(
            item.get("reaparecimentos"),
            nome="Reaparecimentos",
        )

        cobertura = _numero(
            item.get("cobertura_evidencia_percentual"),
            nome="Cobertura de evidencia",
        )

        if cobertura < 0.0 or cobertura > 100.0:
            raise ValueError("Cobertura fora do intervalo.")

        maior_gap = _numero(
            item.get("maior_gap_evidencia_segundos"),
            nome="Maior gap",
        )

        if maior_gap < 0.0:
            raise ValueError("Maior gap invalido.")

        mapa[codigo] = {
            "observado_agora": observado,
            "reaparecimentos": reaparecimentos,
            "cobertura": cobertura,
            "maior_gap": maior_gap,
        }

    universo = set(mapa)

    observadas_calculadas = sum(1 for item in mapa.values() if item["observado_agora"])

    ausentes_calculadas = quantidade - observadas_calculadas

    observadas_registro = _inteiro(
        normalizado.get("observadas_agora"),
        nome="Observadas agora",
    )

    ausentes_registro = _inteiro(
        normalizado.get("ausentes_agora"),
        nome="Ausentes agora",
    )

    if observadas_registro != observadas_calculadas or ausentes_registro != ausentes_calculadas:
        raise ValueError("Contagens observadas/ausentes inconsistentes.")

    for campo in (
        "com_reaparecimento_historico",
        "com_lacunas_evidencia_estimadas",
        "com_gaps_igual_ou_acima_2x_cadencia",
        "com_inicio_historico_truncado",
    ):
        _lista_codigos(
            normalizado.get(campo),
            nome=campo,
            universo=universo,
        )

    normalizado["_mapa_interpretacoes"] = mapa

    return normalizado


def _carregar_registros_raiz(
    diretorio: Path,
) -> list[dict[str, Any]]:
    if not diretorio.exists():
        raise ValueError("Historico de sinteses nao existe.")

    registros = []

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

            node_id = registro.get("node_id")

            if (
                not isinstance(
                    node_id,
                    str,
                )
                or not node_id
            ):
                continue

            try:
                referencia = _instante(registro.get("referencia_temporal"))

            except ValueError:
                continue

            registros.append(
                {
                    "node_id": node_id,
                    "referencia": referencia,
                    "registro": registro,
                }
            )

    if not registros:
        raise ValueError("Historico de sinteses sem registros validos.")

    return registros


def _registros_node_atual(
    diretorio: Path,
) -> list[dict[str, Any]]:
    raizes = _carregar_registros_raiz(diretorio)

    mais_recente = max(
        raizes,
        key=lambda item: item["referencia"],
    )

    node_id = mais_recente["node_id"]

    candidatos = [item for item in raizes if item["node_id"] == node_id]

    candidatos.sort(key=lambda item: item["referencia"])

    resultado = []

    for candidato in candidatos:
        validado = _validar_registro(candidato["registro"])

        referencia = _instante(validado["referencia_temporal"])

        if resultado and _instante(resultado[-1]["referencia_temporal"]) == referencia:
            anterior = dict(resultado[-1])

            atual = dict(validado)

            anterior.pop(
                "_mapa_interpretacoes",
                None,
            )

            atual.pop(
                "_mapa_interpretacoes",
                None,
            )

            if anterior != atual:
                raise ValueError("Historico possui sinteses diferentes " "para o mesmo instante.")

            continue

        resultado.append(validado)

    return resultado


def analisar_historico_sinteses_interpretacoes_node(
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
) -> AnaliseHistoricoSintesesInterpretacoesNode:
    registros = _registros_node_atual(Path(diretorio_historico))

    node_id = registros[-1]["node_id"]

    ciclos = []

    todas_coberturas = []
    maior_gap_historico = 0.0

    novas_total = 0
    removidas_total = 0
    mudancas_total = 0
    incrementos_reaparecimento_total = 0

    ciclos_com_lacunas = 0
    ciclos_com_gaps = 0
    ciclos_com_truncamento = 0

    historico_por_codigo = defaultdict(list)

    anterior = None

    for indice, registro in enumerate(registros):
        mapa = registro["_mapa_interpretacoes"]

        universo = set(mapa)

        coberturas = [item["cobertura"] for item in mapa.values()]

        gaps = [item["maior_gap"] for item in mapa.values()]

        todas_coberturas.extend(coberturas)

        if gaps:
            maior_gap_historico = max(
                maior_gap_historico,
                max(gaps),
            )

        com_reaparecimento = _lista_codigos(
            registro["com_reaparecimento_historico"],
            nome="com_reaparecimento_historico",
            universo=universo,
        )

        com_lacunas = _lista_codigos(
            registro["com_lacunas_evidencia_estimadas"],
            nome="com_lacunas_evidencia_estimadas",
            universo=universo,
        )

        com_gaps = _lista_codigos(
            registro["com_gaps_igual_ou_acima_2x_cadencia"],
            nome="com_gaps_igual_ou_acima_2x_cadencia",
            universo=universo,
        )

        com_truncamento = _lista_codigos(
            registro["com_inicio_historico_truncado"],
            nome="com_inicio_historico_truncado",
            universo=universo,
        )

        if com_lacunas:
            ciclos_com_lacunas += 1

        if com_gaps:
            ciclos_com_gaps += 1

        if com_truncamento:
            ciclos_com_truncamento += 1

        novas = ()
        removidas = ()
        passaram_observadas = ()
        deixaram_observadas = ()
        reapar_incrementados = ()

        if indice > 0 and anterior is not None:
            mapa_anterior = anterior["_mapa_interpretacoes"]

            universo_anterior = set(mapa_anterior)

            novas = tuple(sorted(universo - universo_anterior))

            removidas = tuple(sorted(universo_anterior - universo))

            comuns = sorted(universo & universo_anterior)

            passaram_observadas = tuple(
                codigo
                for codigo in comuns
                if (
                    not mapa_anterior[codigo]["observado_agora"] and mapa[codigo]["observado_agora"]
                )
            )

            deixaram_observadas = tuple(
                codigo
                for codigo in comuns
                if (
                    mapa_anterior[codigo]["observado_agora"] and not mapa[codigo]["observado_agora"]
                )
            )

            reapar_incrementados = tuple(
                codigo
                for codigo in comuns
                if (mapa[codigo]["reaparecimentos"] > mapa_anterior[codigo]["reaparecimentos"])
            )

            novas_total += len(novas)

            removidas_total += len(removidas)

            mudancas_total += len(passaram_observadas) + len(deixaram_observadas)

            incrementos_reaparecimento_total += len(reapar_incrementados)

        ciclos.append(
            EvolucaoCicloSinteseInterpretacoesNode(
                referencia_temporal=registro["referencia_temporal"],
                quantidade_interpretacoes=len(mapa),
                observadas_agora=sum(1 for item in mapa.values() if item["observado_agora"]),
                ausentes_agora=sum(1 for item in mapa.values() if not item["observado_agora"]),
                com_reaparecimento_historico=len(com_reaparecimento),
                com_lacunas_evidencia_estimadas=len(com_lacunas),
                com_gaps_igual_ou_acima_2x_cadencia=len(com_gaps),
                com_inicio_historico_truncado=len(com_truncamento),
                novas_interpretacoes=novas,
                interpretacoes_removidas=removidas,
                passaram_a_ser_observadas=(passaram_observadas),
                deixaram_de_ser_observadas=(deixaram_observadas),
                reaparecimentos_incrementados=(reapar_incrementados),
                cobertura_media_percentual=(
                    sum(coberturas) / len(coberturas) if coberturas else 0.0
                ),
                menor_cobertura_percentual=(min(coberturas) if coberturas else 0.0),
                maior_gap_evidencia_segundos=(max(gaps) if gaps else 0.0),
            )
        )

        for codigo, item in mapa.items():
            historico_por_codigo[codigo].append(
                (
                    registro["referencia_temporal"],
                    item,
                    indice,
                )
            )

        anterior = registro

    ultima = registros[-1]
    mapa_ultima = ultima["_mapa_interpretacoes"]

    analises_interpretacoes = []

    for codigo in sorted(historico_por_codigo):
        aparicoes = historico_por_codigo[codigo]

        coberturas = [item["cobertura"] for _, item, _ in aparicoes]

        gaps = [item["maior_gap"] for _, item, _ in aparicoes]

        observadas = sum(1 for _, item, _ in aparicoes if item["observado_agora"])

        mudancas = 0
        incrementos = 0

        for posicao in range(
            1,
            len(aparicoes),
        ):
            referencia_anterior, item_anterior, indice_anterior = aparicoes[posicao - 1]

            referencia_atual, item_atual, indice_atual = aparicoes[posicao]

            del referencia_anterior
            del referencia_atual

            if indice_atual != indice_anterior + 1:
                continue

            if item_anterior["observado_agora"] != item_atual["observado_agora"]:
                mudancas += 1

            if item_atual["reaparecimentos"] > item_anterior["reaparecimentos"]:
                incrementos += 1

        atual = mapa_ultima.get(codigo)

        analises_interpretacoes.append(
            HistoricoSinteseInterpretacaoNode(
                codigo=codigo,
                primeira_evidencia_no_historico=(aparicoes[0][0]),
                ultima_evidencia_no_historico=(aparicoes[-1][0]),
                registros_presente=len(aparicoes),
                registros_observada=observadas,
                registros_ausente=(len(aparicoes) - observadas),
                mudancas_estado_observado=(mudancas),
                incrementos_reaparecimento=(incrementos),
                cobertura_minima_percentual=min(coberturas),
                cobertura_media_percentual=(sum(coberturas) / len(coberturas)),
                maior_gap_evidencia_segundos=max(gaps),
                presente_agora=(atual is not None),
                observado_agora=(atual["observado_agora"] if atual is not None else None),
                reaparecimentos_agora=(atual["reaparecimentos"] if atual is not None else None),
            )
        )

    cobertura_minima = min(todas_coberturas) if todas_coberturas else 0.0

    cobertura_media = sum(todas_coberturas) / len(todas_coberturas) if todas_coberturas else 0.0

    return AnaliseHistoricoSintesesInterpretacoesNode(
        versao_schema=1,
        node_id=node_id,
        inicio_historico=registros[0]["referencia_temporal"],
        fim_historico=registros[-1]["referencia_temporal"],
        quantidade_registros=len(registros),
        quantidade_interpretacoes_ultima_sintese=len(mapa_ultima),
        quantidade_interpretacoes_distintas=len(historico_por_codigo),
        novas_interpretacoes_total=novas_total,
        interpretacoes_removidas_total=(removidas_total),
        mudancas_estado_observado_total=(mudancas_total),
        incrementos_reaparecimento_total=(incrementos_reaparecimento_total),
        ciclos_com_lacunas_evidencia=(ciclos_com_lacunas),
        ciclos_com_gaps_igual_ou_acima_2x_cadencia=(ciclos_com_gaps),
        ciclos_com_inicio_historico_truncado=(ciclos_com_truncamento),
        cobertura_minima_historica_percentual=(cobertura_minima),
        cobertura_media_historica_percentual=(cobertura_media),
        maior_gap_evidencia_historico_segundos=(maior_gap_historico),
        ciclos=tuple(ciclos),
        interpretacoes=tuple(analises_interpretacoes),
    )


def salvar_analise_historico_sinteses_interpretacoes_node(
    analise: AnaliseHistoricoSintesesInterpretacoesNode,
    caminho: str | Path = (CAMINHO_SAIDA_PADRAO),
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
