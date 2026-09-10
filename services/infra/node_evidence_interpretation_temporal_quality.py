# 63.8738, -149.7525

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.qualidade_temporal_interpretacoes_node import (
    QualidadeTemporalInterpretacaoItemNode,
    QualidadeTemporalInterpretacoesNode,
)
from services.infra.node_health import DIRETORIO_PROJETO

CAMINHO_RESUMO_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "resumo_temporal_interpretacoes_atual.json"
)

DIRETORIO_HISTORICO_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "historico_interpretacoes"

CAMINHO_SAIDA_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "qualidade_temporal_interpretacoes_atual.json"
)

CADENCIA_NOMINAL_SEGUNDOS = 300.0


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
) -> dict[str, Any]:
    caminho = Path(caminho)

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


def _normalizar_registro(
    registro: dict[str, Any],
) -> dict[str, Any]:
    copia = dict(registro)

    copia["referencia_temporal"] = _instante(registro.get("referencia_temporal")).isoformat()

    return copia


def _carregar_historico(
    diretorio: str | Path,
    *,
    node_id: str,
) -> list[dict[str, Any]]:
    diretorio = Path(diretorio)

    if not diretorio.exists():
        raise ValueError("Historico de interpretacoes inexistente.")

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

            if registro.get("node_id") != node_id:
                continue

            try:
                _instante(registro.get("referencia_temporal"))

            except ValueError:
                continue

            registros.append(registro)

    if not registros:
        raise ValueError("Nenhum registro historico valido " "para o node atual.")

    registros.sort(key=lambda item: _instante(item["referencia_temporal"]))

    unicos = []
    por_instante = {}

    for registro in registros:
        instante = _instante(registro["referencia_temporal"])

        existente = por_instante.get(instante)

        if existente is None:
            por_instante[instante] = registro

            unicos.append(registro)

            continue

        if _normalizar_registro(existente) != _normalizar_registro(registro):
            raise ValueError("Historico possui estados diferentes " "para o mesmo instante.")

    return unicos


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


def _mapa_observacoes(
    registro: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    resultado = {}

    for item in _lista_dicts(registro.get("observacoes")):
        codigo = item.get("codigo")

        if (
            not isinstance(
                codigo,
                str,
            )
            or not codigo
        ):
            continue

        if codigo in resultado:
            raise ValueError("Codigo duplicado no historico.")

        resultado[codigo] = item

    return resultado


def _esperadas(
    inicio: datetime,
    fim: datetime,
    cadencia: float,
) -> int:
    janela = max(
        0.0,
        (fim - inicio).total_seconds(),
    )

    return max(
        1,
        int(math.floor(janela / cadencia)) + 1,
    )


def _razao(
    observadas: int,
    esperadas: int,
) -> float:
    if esperadas <= 0:
        return 0.0

    return observadas / esperadas * 100.0


def _maior_gap(
    instantes: list[datetime],
) -> float:
    if len(instantes) < 2:
        return 0.0

    return max(
        (atual - anterior).total_seconds()
        for anterior, atual in zip(
            instantes,
            instantes[1:],
            strict=False,
        )
    )


def _gaps_2x(
    instantes: list[datetime],
    cadencia: float,
) -> int:
    limite = cadencia * 2.0

    return sum(
        1
        for anterior, atual in zip(
            instantes,
            instantes[1:],
            strict=False,
        )
        if (atual - anterior).total_seconds() >= limite
    )


def analisar_qualidade_temporal_interpretacoes_node(
    caminho_resumo: str | Path = (CAMINHO_RESUMO_PADRAO),
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
    *,
    cadencia_nominal_segundos: float = (CADENCIA_NOMINAL_SEGUNDOS),
) -> QualidadeTemporalInterpretacoesNode:
    if cadencia_nominal_segundos <= 0:
        raise ValueError("Cadencia nominal deve ser positiva.")

    resumo = _carregar_json(caminho_resumo)

    node_id = resumo.get("node_id")

    if (
        not isinstance(
            node_id,
            str,
        )
        or not node_id
    ):
        raise ValueError("Node ID invalido.")

    referencia = resumo.get("referencia_temporal")

    referencia_dt = _instante(referencia)

    registros = _carregar_historico(
        diretorio_historico,
        node_id=node_id,
    )

    ultimo_dt = _instante(registros[-1]["referencia_temporal"])

    if ultimo_dt != referencia_dt:
        raise ValueError("Resumo e historico pertencem " "a ciclos diferentes.")

    primeiro_dt = _instante(registros[0]["referencia_temporal"])

    instantes_globais = [_instante(registro["referencia_temporal"]) for registro in registros]

    esperadas_globais = _esperadas(
        primeiro_dt,
        ultimo_dt,
        cadencia_nominal_segundos,
    )

    observadas_globais = len(registros)

    razao_global = _razao(
        observadas_globais,
        esperadas_globais,
    )

    resumo_itens = _lista_dicts(resumo.get("interpretacoes"))

    itens = []

    for resumo_item in resumo_itens:
        codigo = resumo_item.get("codigo")

        if (
            not isinstance(
                codigo,
                str,
            )
            or not codigo
        ):
            raise ValueError("Codigo invalido no resumo.")

        evidencias = []

        for registro in registros:
            mapa = _mapa_observacoes(registro)

            if codigo in mapa:
                evidencias.append(_instante(registro["referencia_temporal"]))

        if not evidencias:
            raise ValueError("Interpretacao do resumo sem " "evidencia no historico.")

        primeira = evidencias[0]
        ultima = evidencias[-1]

        esperadas_item = _esperadas(
            primeira,
            ultimo_dt,
            cadencia_nominal_segundos,
        )

        observadas_item = len(evidencias)

        razao_item = _razao(
            observadas_item,
            esperadas_item,
        )

        janela_item = max(
            0.0,
            (ultimo_dt - primeira).total_seconds(),
        )

        duracao_atual = resumo_item.get("duracao_estado_atual_segundos")

        if isinstance(
            duracao_atual,
            bool,
        ) or not isinstance(
            duracao_atual,
            (
                int,
                float,
            ),
        ):
            raise ValueError("Duracao atual invalida.")

        duracao_atual_float = max(
            0.0,
            float(duracao_atual),
        )

        if janela_item > 0:
            percentual_janela = min(
                100.0,
                (duracao_atual_float / janela_item * 100.0),
            )

        else:
            percentual_janela = 100.0 if duracao_atual_float == 0 else 0.0

        item = QualidadeTemporalInterpretacaoItemNode(
            codigo=codigo,
            observado_agora=(resumo_item.get("observado_agora") is True),
            primeira_evidencia=(primeira.isoformat()),
            ultima_evidencia=(ultima.isoformat()),
            registros_com_evidencia=(observadas_item),
            registros_esperados_desde_primeira_evidencia=(esperadas_item),
            registros_ausentes_estimados=max(
                0,
                esperadas_item - observadas_item,
            ),
            razao_amostras_percentual=(razao_item),
            cobertura_normalizada_percentual=min(
                100.0,
                razao_item,
            ),
            maior_gap_evidencia_segundos=(_maior_gap(evidencias)),
            gaps_igual_ou_acima_2x_cadencia=(
                _gaps_2x(
                    evidencias,
                    cadencia_nominal_segundos,
                )
            ),
            janela_evidencia_segundos=(janela_item),
            duracao_estado_atual_segundos=(duracao_atual_float),
            duracao_estado_atual_percentual_janela=(percentual_janela),
            quantidade_episodios_observados=int(
                resumo_item.get(
                    "quantidade_episodios_observados",
                    0,
                )
            ),
            reaparecimentos=int(
                resumo_item.get(
                    "reaparecimentos",
                    0,
                )
            ),
            quantidade_periodos_ausentes=int(
                resumo_item.get(
                    "quantidade_periodos_ausentes",
                    0,
                )
            ),
            inicio_historico_truncado=(resumo_item.get("inicio_historico_truncado") is True),
        )

        itens.append(item)

    if len(itens) != int(
        resumo.get(
            "quantidade_interpretacoes",
            -1,
        )
    ):
        raise ValueError("Universo de interpretacoes inconsistente.")

    ranking = tuple(
        item.codigo
        for item in sorted(
            itens,
            key=lambda item: (
                item.cobertura_normalizada_percentual,
                -item.maior_gap_evidencia_segundos,
                item.codigo,
            ),
        )
    )

    janela_global = max(
        0.0,
        (ultimo_dt - primeiro_dt).total_seconds(),
    )

    return QualidadeTemporalInterpretacoesNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=(referencia_dt.isoformat()),
        cadencia_nominal_segundos=float(cadencia_nominal_segundos),
        inicio_historico=(primeiro_dt.isoformat()),
        fim_historico=(ultimo_dt.isoformat()),
        janela_historica_segundos=(janela_global),
        registros_observados=(observadas_globais),
        registros_esperados=(esperadas_globais),
        registros_excedentes=max(
            0,
            observadas_globais - esperadas_globais,
        ),
        razao_amostras_percentual=(razao_global),
        cobertura_normalizada_percentual=min(
            100.0,
            razao_global,
        ),
        maior_gap_historico_segundos=(_maior_gap(instantes_globais)),
        gaps_igual_ou_acima_2x_cadencia=(
            _gaps_2x(
                instantes_globais,
                cadencia_nominal_segundos,
            )
        ),
        quantidade_interpretacoes=len(itens),
        com_inicio_historico_truncado=sum(1 for item in itens if item.inicio_historico_truncado),
        interpretacoes_por_menor_cobertura_evidencia=(ranking),
        interpretacoes=tuple(
            sorted(
                itens,
                key=lambda item: item.codigo,
            )
        ),
    )


def salvar_qualidade_temporal_interpretacoes_node(
    analise: QualidadeTemporalInterpretacoesNode,
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
