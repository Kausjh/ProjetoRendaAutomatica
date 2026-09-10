# 63.8738, -149.7525

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.infra.node_health import DIRETORIO_PROJETO

CAMINHO_SINTESE_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "sintese_evidencias_interpretacoes_atual.json"
)

DIRETORIO_HISTORICO_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "historico_sinteses_interpretacoes"
)


@dataclass(frozen=True, slots=True)
class ResultadoPersistenciaSinteseNode:
    node_id: str
    referencia_temporal: str
    caminho_historico: Path
    registro_adicionado: bool
    quantidade_registros_validos_node: int


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


def _carregar_sintese(
    caminho: str | Path,
) -> dict[str, Any]:
    caminho = Path(caminho)

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))

    except (
        OSError,
        json.JSONDecodeError,
    ) as erro:
        raise ValueError(f"Sintese invalida: {caminho}") from erro

    if not isinstance(
        dados,
        dict,
    ):
        raise ValueError(f"Sintese invalida: {caminho}")

    node_id = dados.get("node_id")

    if (
        not isinstance(
            node_id,
            str,
        )
        or not node_id
    ):
        raise ValueError("Node ID invalido.")

    referencia = _instante(dados.get("referencia_temporal"))

    quantidade = dados.get("quantidade_interpretacoes")

    if (
        isinstance(
            quantidade,
            bool,
        )
        or not isinstance(
            quantidade,
            int,
        )
        or quantidade < 0
    ):
        raise ValueError("Quantidade de interpretacoes invalida.")

    interpretacoes = dados.get("interpretacoes")

    if not isinstance(
        interpretacoes,
        list,
    ):
        raise ValueError("Interpretacoes invalidas.")

    if len(interpretacoes) != quantidade:
        raise ValueError("Quantidade de interpretacoes inconsistente.")

    codigos = []

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

        codigos.append(codigo)

    if len(codigos) != len(set(codigos)):
        raise ValueError("Codigos de interpretacao duplicados.")

    normalizada = dict(dados)

    normalizada["referencia_temporal"] = referencia.isoformat()

    return normalizada


def _normalizar_temporais_sintese(
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
                resultado[chave] = _normalizar_temporais_sintese(item)

        return resultado

    if isinstance(
        valor,
        list,
    ):
        return [_normalizar_temporais_sintese(item) for item in valor]

    return valor


def _normalizar_registro_existente(
    registro: dict[str, Any],
) -> dict[str, Any]:
    return _normalizar_temporais_sintese(registro)


def _registros_validos(
    diretorio: Path,
) -> list[dict[str, Any]]:
    if not diretorio.exists():
        return []

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
                _instante(registro.get("referencia_temporal"))

            except ValueError:
                continue

            registros.append(registro)

    return registros


def persistir_sintese_evidencias_interpretacoes_node(
    caminho_sintese: str | Path = (CAMINHO_SINTESE_PADRAO),
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
) -> ResultadoPersistenciaSinteseNode:
    sintese = _normalizar_temporais_sintese(_carregar_sintese(caminho_sintese))

    node_id = sintese["node_id"]

    referencia = _instante(sintese["referencia_temporal"])

    diretorio = Path(diretorio_historico)

    diretorio.mkdir(
        parents=True,
        exist_ok=True,
    )

    existentes = _registros_validos(diretorio)

    existentes_node = [registro for registro in existentes if registro.get("node_id") == node_id]

    mesmo_instante = [
        registro
        for registro in existentes_node
        if _instante(registro["referencia_temporal"]) == referencia
    ]

    for registro in mesmo_instante:
        if _normalizar_registro_existente(registro) != sintese:
            raise ValueError("Historico possui sintese diferente " "para o mesmo instante.")

    if mesmo_instante:
        caminho_destino = diretorio / (referencia.strftime("%Y-%m-%d") + ".jsonl")

        return ResultadoPersistenciaSinteseNode(
            node_id=node_id,
            referencia_temporal=(referencia.isoformat()),
            caminho_historico=(caminho_destino),
            registro_adicionado=False,
            quantidade_registros_validos_node=len(existentes_node),
        )

    if existentes_node:
        maior_referencia = max(
            _instante(registro["referencia_temporal"]) for registro in existentes_node
        )

        if referencia < maior_referencia:
            raise ValueError("Sintese mais antiga que o ultimo " "registro persistido para o node.")

    caminho_destino = diretorio / (referencia.strftime("%Y-%m-%d") + ".jsonl")

    texto_anterior = ""

    if caminho_destino.exists():
        try:
            texto_anterior = caminho_destino.read_text(encoding="utf-8")

        except OSError as erro:
            raise ValueError("Nao foi possivel ler " "o historico existente.") from erro

    if texto_anterior and not texto_anterior.endswith("\n"):
        texto_anterior += "\n"

    nova_linha = (
        json.dumps(
            sintese,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )

    temporario = caminho_destino.with_suffix(caminho_destino.suffix + ".tmp")

    temporario.write_text(
        texto_anterior + nova_linha,
        encoding="utf-8",
    )

    temporario.replace(caminho_destino)

    return ResultadoPersistenciaSinteseNode(
        node_id=node_id,
        referencia_temporal=(referencia.isoformat()),
        caminho_historico=(caminho_destino),
        registro_adicionado=True,
        quantidade_registros_validos_node=(len(existentes_node) + 1),
    )
