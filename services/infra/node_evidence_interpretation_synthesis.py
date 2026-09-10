# 63.8738, -149.7525

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.sintese_evidencias_interpretacoes_node import (
    SinteseEvidenciasInterpretacoesNode,
    SinteseInterpretacaoEvidenciaNode,
)
from services.infra.node_health import DIRETORIO_PROJETO

CAMINHO_RESUMO_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "resumo_temporal_interpretacoes_atual.json"
)

CAMINHO_QUALIDADE_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "qualidade_temporal_interpretacoes_atual.json"
)

CAMINHO_SAIDA_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "sintese_evidencias_interpretacoes_atual.json"
)


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
    nome: str,
) -> int:
    if isinstance(
        valor,
        bool,
    ) or not isinstance(
        valor,
        int,
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

    return float(valor)


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


def _lista_textos(
    valor: object,
) -> tuple[str, ...]:
    if not isinstance(
        valor,
        list,
    ):
        return ()

    resultado = []

    for item in valor:
        if (
            isinstance(
                item,
                str,
            )
            and item
        ):
            resultado.append(item)

    return tuple(resultado)


def _mapa(
    valor: object,
    *,
    nome: str,
) -> dict[str, dict[str, Any]]:
    resultado = {}

    for item in _lista_dicts(valor):
        codigo = _texto(
            item.get("codigo"),
            nome=f"Codigo em {nome}",
        )

        if codigo in resultado:
            raise ValueError(f"Codigo duplicado em {nome}.")

        resultado[codigo] = item

    return resultado


def _mesmo_numero(
    primeiro: object,
    segundo: object,
    *,
    nome: str,
) -> float:
    a = _numero(
        primeiro,
        nome=nome,
    )

    b = _numero(
        segundo,
        nome=nome,
    )

    if not math.isclose(
        a,
        b,
        rel_tol=1e-12,
        abs_tol=1e-9,
    ):
        raise ValueError(f"{nome} divergente entre artefatos.")

    return a


def gerar_sintese_evidencias_interpretacoes_node(
    caminho_resumo: str | Path = (CAMINHO_RESUMO_PADRAO),
    caminho_qualidade: str | Path = (CAMINHO_QUALIDADE_PADRAO),
) -> SinteseEvidenciasInterpretacoesNode:
    resumo = _carregar_json(caminho_resumo)

    qualidade = _carregar_json(caminho_qualidade)

    node_resumo = _texto(
        resumo.get("node_id"),
        nome="Node ID do resumo",
    )

    node_qualidade = _texto(
        qualidade.get("node_id"),
        nome="Node ID da qualidade",
    )

    if node_resumo != node_qualidade:
        raise ValueError("Node IDs divergentes.")

    referencia_resumo = _texto(
        resumo.get("referencia_temporal"),
        nome="Referencia do resumo",
    )

    referencia_qualidade = _texto(
        qualidade.get("referencia_temporal"),
        nome="Referencia da qualidade",
    )

    if _instante(referencia_resumo) != _instante(referencia_qualidade):
        raise ValueError("Resumo e qualidade pertencem a ciclos diferentes.")

    resumo_por_codigo = _mapa(
        resumo.get("interpretacoes"),
        nome="resumo",
    )

    qualidade_por_codigo = _mapa(
        qualidade.get("interpretacoes"),
        nome="qualidade",
    )

    if set(resumo_por_codigo) != set(qualidade_por_codigo):
        raise ValueError("Universo de interpretacoes divergente.")

    quantidade_resumo = _inteiro(
        resumo.get("quantidade_interpretacoes"),
        nome="Quantidade do resumo",
    )

    quantidade_qualidade = _inteiro(
        qualidade.get("quantidade_interpretacoes"),
        nome="Quantidade da qualidade",
    )

    if quantidade_resumo != quantidade_qualidade or quantidade_resumo != len(resumo_por_codigo):
        raise ValueError("Quantidade de interpretacoes inconsistente.")

    itens = []

    for codigo in sorted(resumo_por_codigo):
        item_resumo = resumo_por_codigo[codigo]

        item_qualidade = qualidade_por_codigo[codigo]

        observado_resumo = item_resumo.get("observado_agora") is True

        observado_qualidade = item_qualidade.get("observado_agora") is True

        if observado_resumo != observado_qualidade:
            raise ValueError("Observacao atual divergente " f"para {codigo}.")

        duracao = _mesmo_numero(
            item_resumo.get("duracao_estado_atual_segundos"),
            item_qualidade.get("duracao_estado_atual_segundos"),
            nome=("Duracao do estado atual " f"para {codigo}"),
        )

        episodios_resumo = _inteiro(
            item_resumo.get("quantidade_episodios_observados"),
            nome="Episodios no resumo",
        )

        episodios_qualidade = _inteiro(
            item_qualidade.get("quantidade_episodios_observados"),
            nome="Episodios na qualidade",
        )

        reaparecimentos_resumo = _inteiro(
            item_resumo.get("reaparecimentos"),
            nome="Reaparecimentos no resumo",
        )

        reaparecimentos_qualidade = _inteiro(
            item_qualidade.get("reaparecimentos"),
            nome="Reaparecimentos na qualidade",
        )

        ausencias_resumo = _inteiro(
            item_resumo.get("quantidade_periodos_ausentes"),
            nome="Periodos ausentes no resumo",
        )

        ausencias_qualidade = _inteiro(
            item_qualidade.get("quantidade_periodos_ausentes"),
            nome="Periodos ausentes na qualidade",
        )

        truncado_resumo = item_resumo.get("inicio_historico_truncado") is True

        truncado_qualidade = item_qualidade.get("inicio_historico_truncado") is True

        if (
            episodios_resumo != episodios_qualidade
            or reaparecimentos_resumo != reaparecimentos_qualidade
            or ausencias_resumo != ausencias_qualidade
            or truncado_resumo != truncado_qualidade
        ):
            raise ValueError("Historico temporal divergente " f"para {codigo}.")

        itens.append(
            SinteseInterpretacaoEvidenciaNode(
                codigo=codigo,
                categoria=_texto(
                    item_resumo.get("categoria"),
                    nome="Categoria",
                ),
                sujeito=_texto(
                    item_resumo.get("sujeito"),
                    nome="Sujeito",
                ),
                descricao=_texto(
                    item_resumo.get("descricao"),
                    nome="Descricao",
                ),
                observado_agora=(observado_resumo),
                transicao_ultimo_ciclo=_texto(
                    item_resumo.get("transicao_ultimo_ciclo"),
                    nome="Transicao",
                ),
                duracao_estado_atual_segundos=(duracao),
                duracao_estado_atual_percentual_janela=_numero(
                    item_qualidade.get("duracao_estado_atual_percentual_janela"),
                    nome="Percentual da janela",
                ),
                quantidade_episodios_observados=(episodios_resumo),
                reaparecimentos=(reaparecimentos_resumo),
                quantidade_periodos_ausentes=(ausencias_resumo),
                inicio_historico_truncado=(truncado_resumo),
                primeira_evidencia=_texto(
                    item_qualidade.get("primeira_evidencia"),
                    nome="Primeira evidencia",
                ),
                ultima_evidencia=_texto(
                    item_qualidade.get("ultima_evidencia"),
                    nome="Ultima evidencia",
                ),
                janela_evidencia_segundos=_numero(
                    item_qualidade.get("janela_evidencia_segundos"),
                    nome="Janela de evidencia",
                ),
                registros_com_evidencia=_inteiro(
                    item_qualidade.get("registros_com_evidencia"),
                    nome="Registros com evidencia",
                ),
                registros_esperados_desde_primeira_evidencia=_inteiro(
                    item_qualidade.get("registros_esperados_desde_primeira_evidencia"),
                    nome="Registros esperados",
                ),
                registros_ausentes_estimados=_inteiro(
                    item_qualidade.get("registros_ausentes_estimados"),
                    nome="Registros ausentes",
                ),
                razao_amostras_percentual=_numero(
                    item_qualidade.get("razao_amostras_percentual"),
                    nome="Razao de amostras",
                ),
                cobertura_evidencia_percentual=_numero(
                    item_qualidade.get("cobertura_normalizada_percentual"),
                    nome="Cobertura de evidencia",
                ),
                maior_gap_evidencia_segundos=_numero(
                    item_qualidade.get("maior_gap_evidencia_segundos"),
                    nome="Maior gap",
                ),
                gaps_igual_ou_acima_2x_cadencia=_inteiro(
                    item_qualidade.get("gaps_igual_ou_acima_2x_cadencia"),
                    nome="Gaps 2x",
                ),
            )
        )

    com_reaparecimento = tuple(item.codigo for item in itens if item.reaparecimentos > 0)

    com_lacunas = tuple(item.codigo for item in itens if item.registros_ausentes_estimados > 0)

    com_gaps = tuple(item.codigo for item in itens if item.gaps_igual_ou_acima_2x_cadencia > 0)

    com_truncamento = tuple(item.codigo for item in itens if item.inicio_historico_truncado)

    ranking_resumo_observadas = _lista_textos(resumo.get("observadas_por_maior_duracao_atual"))

    ranking_resumo_ausentes = _lista_textos(resumo.get("ausentes_por_maior_duracao_atual"))

    ranking_qualidade = _lista_textos(qualidade.get("interpretacoes_por_menor_cobertura_evidencia"))

    universo = set(resumo_por_codigo)

    for ranking in (
        ranking_resumo_observadas,
        ranking_resumo_ausentes,
        ranking_qualidade,
    ):
        if not set(ranking).issubset(universo):
            raise ValueError("Ranking contem codigo desconhecido.")

    return SinteseEvidenciasInterpretacoesNode(
        versao_schema=1,
        node_id=node_resumo,
        referencia_temporal=(_instante(referencia_resumo).isoformat()),
        cadencia_nominal_segundos=_numero(
            qualidade.get("cadencia_nominal_segundos"),
            nome="Cadencia nominal",
        ),
        quantidade_interpretacoes=len(itens),
        observadas_agora=sum(1 for item in itens if item.observado_agora),
        ausentes_agora=sum(1 for item in itens if not item.observado_agora),
        com_reaparecimento_historico=(com_reaparecimento),
        com_lacunas_evidencia_estimadas=(com_lacunas),
        com_gaps_igual_ou_acima_2x_cadencia=(com_gaps),
        com_inicio_historico_truncado=(com_truncamento),
        observadas_por_maior_duracao_atual=(ranking_resumo_observadas),
        ausentes_por_maior_duracao_atual=(ranking_resumo_ausentes),
        por_menor_cobertura_evidencia=(ranking_qualidade),
        interpretacoes=tuple(itens),
    )


def salvar_sintese_evidencias_interpretacoes_node(
    sintese: SinteseEvidenciasInterpretacoesNode,
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
            sintese.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporario.replace(caminho)

    return caminho
