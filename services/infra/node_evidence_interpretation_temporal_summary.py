# 63.8738, -149.7525

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.resumo_temporal_interpretacoes_node import (
    ResumoTemporalInterpretacaoItemNode,
    ResumoTemporalInterpretacoesNode,
)
from services.infra.node_health import DIRETORIO_PROJETO

CAMINHO_ESTADO_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "interpretacao_estado_atual.json"

CAMINHO_ANALISE_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "analise_historico_interpretacoes_atual.json"
)

CAMINHO_RESUMO_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "resumo_temporal_interpretacoes_atual.json"
)


def _carregar_json(
    caminho: str | Path,
) -> dict[str, Any]:
    caminho = Path(caminho)

    if not caminho.exists():
        raise ValueError(f"Artefato ausente: {caminho}")

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


def _texto_opcional(
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


def _inteiro(
    valor: object,
    *,
    nome: str,
) -> int:
    if not isinstance(
        valor,
        int,
    ) or isinstance(
        valor,
        bool,
    ):
        raise ValueError(f"{nome} invalido.")

    return valor


def _numero_opcional(
    valor: object,
) -> float | None:
    if isinstance(
        valor,
        bool,
    ):
        return None

    if isinstance(
        valor,
        (
            int,
            float,
        ),
    ):
        return float(valor)

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


def _mapa(
    itens: object,
) -> dict[str, dict[str, Any]]:
    resultado: dict[
        str,
        dict[str, Any],
    ] = {}

    for item in _lista_dicts(itens):
        codigo = _texto(
            item.get("codigo"),
            nome="Codigo",
        )

        if codigo in resultado:
            raise ValueError("Codigo duplicado no artefato.")

        resultado[codigo] = item

    return resultado


def _inicio_historico_truncado(
    historico: dict[str, Any],
) -> bool:
    intervalos: list[dict[str, Any]] = []

    intervalos.extend(_lista_dicts(historico.get("episodios_observados")))

    intervalos.extend(_lista_dicts(historico.get("periodos_ausentes")))

    if not intervalos:
        return True

    validos = []

    for intervalo in intervalos:
        inicio = intervalo.get("inicio")

        if not isinstance(
            inicio,
            str,
        ):
            continue

        try:
            instante = _instante(inicio)

        except ValueError:
            continue

        validos.append(
            (
                instante,
                intervalo,
            )
        )

    if not validos:
        return True

    primeiro = min(
        validos,
        key=lambda item: item[0],
    )[1]

    return primeiro.get("inicio_confirmado") is not True


def _duracao_estado_atual(
    *,
    observado_agora: bool,
    historico: dict[str, Any],
) -> float:
    if observado_agora:
        valor = _numero_opcional(historico.get("duracao_episodio_atual_segundos"))

    else:
        valor = _numero_opcional(historico.get("duracao_ausencia_atual_segundos"))

    if valor is None:
        return 0.0

    return max(
        0.0,
        valor,
    )


def gerar_resumo_temporal_interpretacoes_node(
    caminho_estado: str | Path = (CAMINHO_ESTADO_PADRAO),
    caminho_analise: str | Path = (CAMINHO_ANALISE_PADRAO),
) -> ResumoTemporalInterpretacoesNode:
    estado = _carregar_json(caminho_estado)

    analise = _carregar_json(caminho_analise)

    node_estado = _texto(
        estado.get("node_id"),
        nome="Node ID do estado",
    )

    node_analise = _texto(
        analise.get("node_id"),
        nome="Node ID da analise",
    )

    if node_estado != node_analise:
        raise ValueError("Node IDs divergentes.")

    referencia_estado = _texto(
        estado.get("referencia_temporal"),
        nome="Referencia do estado",
    )

    referencia_analise = _texto(
        analise.get("fim_periodo"),
        nome="Fim da analise",
    )

    if _instante(referencia_estado) != _instante(referencia_analise):
        raise ValueError("Estado e analise pertencem a ciclos diferentes.")

    estado_por_codigo = _mapa(estado.get("observacoes"))

    historico_por_codigo = _mapa(analise.get("interpretacoes"))

    if set(estado_por_codigo) != set(historico_por_codigo):
        raise ValueError(
            "Estado atual e analise historica possuem " "universos de interpretacoes diferentes."
        )

    itens = []

    for codigo in sorted(estado_por_codigo):
        atual = estado_por_codigo[codigo]

        historico = historico_por_codigo[codigo]

        observado_agora = atual.get("observado_agora") is True

        transicao = _texto(
            atual.get("transicao_ultimo_ciclo"),
            nome="Transicao",
        )

        historico_observado = historico.get("observado_agora") is True

        if observado_agora != historico_observado:
            raise ValueError(
                "Estado atual e analise historica " "discordam sobre observacao atual."
            )

        item = ResumoTemporalInterpretacaoItemNode(
            codigo=codigo,
            categoria=_texto(
                atual.get("categoria"),
                nome="Categoria",
            ),
            sujeito=_texto(
                atual.get("sujeito"),
                nome="Sujeito",
            ),
            descricao=_texto(
                atual.get("descricao"),
                nome="Descricao",
            ),
            observado_agora=(observado_agora),
            transicao_ultimo_ciclo=(transicao),
            primeira_observacao=_texto(
                atual.get("primeira_observacao"),
                nome="Primeira observacao",
            ),
            inicio_sequencia_atual=_texto(
                atual.get("inicio_sequencia_atual"),
                nome="Inicio da sequencia",
            ),
            ultima_observacao=_texto(
                atual.get("ultima_observacao"),
                nome="Ultima observacao",
            ),
            deixou_de_ser_observado_em=(_texto_opcional(atual.get("deixou_de_ser_observado_em"))),
            observacoes_consecutivas=_inteiro(
                atual.get("observacoes_consecutivas"),
                nome="Observacoes consecutivas",
            ),
            observacoes_totais=_inteiro(
                atual.get("observacoes_totais"),
                nome="Observacoes totais",
            ),
            ciclos_ausente_consecutivos=_inteiro(
                atual.get("ciclos_ausente_consecutivos"),
                nome="Ciclos ausentes",
            ),
            quantidade_episodios_observados=_inteiro(
                historico.get("quantidade_episodios_observados"),
                nome="Quantidade de episodios",
            ),
            reaparecimentos=_inteiro(
                historico.get("reaparecimentos"),
                nome="Reaparecimentos",
            ),
            quantidade_periodos_ausentes=_inteiro(
                historico.get("quantidade_periodos_ausentes"),
                nome="Periodos ausentes",
            ),
            inicio_historico_truncado=(_inicio_historico_truncado(historico)),
            episodio_atual_aberto=(historico.get("episodio_atual_aberto") is True),
            periodo_ausencia_atual_aberto=(historico.get("periodo_ausencia_atual_aberto") is True),
            duracao_estado_atual_segundos=(
                _duracao_estado_atual(
                    observado_agora=(observado_agora),
                    historico=historico,
                )
            ),
            maior_duracao_observada_segundos=(
                _numero_opcional(historico.get("maior_duracao_observada_segundos"))
            ),
            maior_duracao_ausencia_segundos=(
                _numero_opcional(historico.get("maior_duracao_ausencia_segundos"))
            ),
        )

        itens.append(item)

    def contar_transicao(
        transicao: str,
    ) -> int:
        return sum(1 for item in itens if item.transicao_ultimo_ciclo == transicao)

    observadas_ranking = tuple(
        item.codigo
        for item in sorted(
            (item for item in itens if item.observado_agora),
            key=lambda item: (
                -item.duracao_estado_atual_segundos,
                item.codigo,
            ),
        )
    )

    ausentes_ranking = tuple(
        item.codigo
        for item in sorted(
            (item for item in itens if not item.observado_agora),
            key=lambda item: (
                -item.duracao_estado_atual_segundos,
                item.codigo,
            ),
        )
    )

    return ResumoTemporalInterpretacoesNode(
        versao_schema=1,
        node_id=node_estado,
        referencia_temporal=(referencia_estado),
        quantidade_interpretacoes=len(itens),
        observadas_agora=sum(1 for item in itens if item.observado_agora),
        ausentes_agora=sum(1 for item in itens if not item.observado_agora),
        novas_no_ultimo_ciclo=contar_transicao("novo"),
        continuaram_observadas=contar_transicao("continua_observado"),
        deixaram_de_ser_observadas=contar_transicao("deixou_de_ser_observado"),
        continuaram_ausentes=contar_transicao("continua_nao_observado"),
        reapareceram_no_ultimo_ciclo=contar_transicao("reapareceu"),
        com_reaparecimento_historico=sum(1 for item in itens if item.reaparecimentos > 0),
        com_inicio_historico_truncado=sum(1 for item in itens if item.inicio_historico_truncado),
        observadas_por_maior_duracao_atual=(observadas_ranking),
        ausentes_por_maior_duracao_atual=(ausentes_ranking),
        interpretacoes=tuple(itens),
    )


def salvar_resumo_temporal_interpretacoes_node(
    resumo: ResumoTemporalInterpretacoesNode,
    caminho: str | Path = (CAMINHO_RESUMO_PADRAO),
) -> Path:
    caminho = Path(caminho)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporario = caminho.with_suffix(caminho.suffix + ".tmp")

    temporario.write_text(
        json.dumps(
            resumo.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporario.replace(caminho)

    return caminho
