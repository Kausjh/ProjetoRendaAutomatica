# 63.8738, -149.7525

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.interpretacao_evidencias_node import (
    InterpretacaoObservacionalEvidenciasNode,
    ObservacaoEstruturadaEvidenciaNode,
)
from services.infra.node_health import DIRETORIO_PROJETO

CAMINHO_RESUMO_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "resumo_evidencias_atual.json"

CAMINHO_QUALIDADE_TEMPORAL_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "qualidade_evidencia_temporal_atual.json"
)

CAMINHO_INTERPRETACAO_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "interpretacao_evidencias_atual.json"
)

FONTE_RESUMO = "resumo_evidencias_atual.json"

FONTE_QUALIDADE_TEMPORAL = "qualidade_evidencia_temporal_atual.json"


def _carregar_json(
    caminho: str | Path,
    *,
    nome: str,
) -> dict[str, Any]:
    caminho = Path(caminho)

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))

    except (
        OSError,
        json.JSONDecodeError,
    ) as erro:
        raise ValueError(f"Artefato {nome} invalido.") from erro

    if not isinstance(
        dados,
        dict,
    ):
        raise ValueError(f"Artefato {nome} invalido.")

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


def _numero(
    valor: object,
) -> float | None:
    if isinstance(
        valor,
        (int, float),
    ) and not isinstance(
        valor,
        bool,
    ):
        return float(valor)

    return None


def _inteiro(
    valor: object,
) -> int | None:
    if isinstance(
        valor,
        int,
    ) and not isinstance(
        valor,
        bool,
    ):
        return valor

    return None


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


def _validar_consistencia(
    resumo: dict[str, Any],
    qualidade: dict[str, Any],
) -> tuple[str, str]:
    node_resumo = _texto(resumo.get("node_id"))

    node_qualidade = _texto(qualidade.get("node_id"))

    if node_resumo is None or node_qualidade is None:
        raise ValueError("Node ID ausente.")

    if node_resumo != node_qualidade:
        raise ValueError("Artefatos pertencem a nodes diferentes.")

    referencia_resumo = _texto(resumo.get("referencia_temporal"))

    referencia_qualidade = _texto(qualidade.get("referencia_temporal"))

    if referencia_resumo is None or referencia_qualidade is None:
        raise ValueError("Referencia temporal ausente.")

    if _instante(referencia_resumo) != _instante(referencia_qualidade):
        raise ValueError("Artefatos pertencem a ciclos temporais diferentes.")

    return (
        node_resumo,
        referencia_resumo,
    )


def interpretar_evidencias_node(
    caminho_resumo: str | Path = (CAMINHO_RESUMO_PADRAO),
    caminho_qualidade_temporal: str | Path = (CAMINHO_QUALIDADE_TEMPORAL_PADRAO),
) -> InterpretacaoObservacionalEvidenciasNode:
    resumo = _carregar_json(
        caminho_resumo,
        nome="resumo de evidencias",
    )

    qualidade = _carregar_json(
        caminho_qualidade_temporal,
        nome="qualidade temporal",
    )

    (
        node_id,
        referencia_temporal,
    ) = _validar_consistencia(
        resumo,
        qualidade,
    )

    observacoes: list[ObservacaoEstruturadaEvidenciaNode] = []

    def adicionar(
        *,
        codigo: str,
        categoria: str,
        sujeito: str,
        descricao: str,
        dados: dict[str, Any],
        fontes: tuple[str, ...],
    ) -> None:
        observacoes.append(
            ObservacaoEstruturadaEvidenciaNode(
                codigo=codigo,
                categoria=categoria,
                sujeito=sujeito,
                descricao=descricao,
                dados=dados,
                fontes=fontes,
            )
        )

    referencia_cobertura = _numero(qualidade.get("cobertura_referencia_percentual"))

    for nome_janela in (
        "recente",
        "baseline",
    ):
        cobertura = _numero(qualidade.get(f"janela_{nome_janela}_" "cobertura_percentual"))

        esperadas = _inteiro(
            resumo.get(
                f"qualidade_janela_{nome_janela}",
                {},
            ).get("amostras_esperadas")
            if isinstance(
                resumo.get(f"qualidade_janela_{nome_janela}"),
                dict,
            )
            else None
        )

        observadas = _inteiro(
            resumo.get(
                f"qualidade_janela_{nome_janela}",
                {},
            ).get("amostras_observadas")
            if isinstance(
                resumo.get(f"qualidade_janela_{nome_janela}"),
                dict,
            )
            else None
        )

        dados_janela = resumo.get(f"qualidade_janela_{nome_janela}")

        if not isinstance(
            dados_janela,
            dict,
        ):
            dados_janela = {}

        razao_bruta = _numero(dados_janela.get("razao_amostras_percentual"))

        excedentes = _inteiro(dados_janela.get("amostras_excedentes"))

        distintos = _inteiro(dados_janela.get("timestamps_distintos"))

        if cobertura is not None and referencia_cobertura is not None:
            atingiu = cobertura >= referencia_cobertura

            if atingiu:
                codigo = f"janela_{nome_janela}:" "cobertura_atinge_referencia"

                descricao = "A cobertura observada da janela " "atinge a referencia configurada."

            else:
                codigo = f"janela_{nome_janela}:" "cobertura_nao_atinge_referencia"

                descricao = (
                    "A cobertura observada da janela " "nao atinge a referencia configurada."
                )

            adicionar(
                codigo=codigo,
                categoria="cobertura",
                sujeito=(f"janela_{nome_janela}"),
                descricao=descricao,
                dados={
                    "cobertura_percentual": cobertura,
                    "referencia_percentual": (referencia_cobertura),
                    "amostras_esperadas": esperadas,
                    "amostras_observadas": observadas,
                    "timestamps_distintos": distintos,
                },
                fontes=(
                    FONTE_RESUMO,
                    FONTE_QUALIDADE_TEMPORAL,
                ),
            )

        if excedentes is not None and excedentes > 0:
            adicionar(
                codigo=(f"janela_{nome_janela}:" "amostras_observadas_acima_esperadas"),
                categoria="amostragem",
                sujeito=(f"janela_{nome_janela}"),
                descricao=(
                    "A quantidade de amostras observadas "
                    "supera a quantidade nominalmente esperada."
                ),
                dados={
                    "amostras_esperadas": esperadas,
                    "amostras_observadas": observadas,
                    "amostras_excedentes": excedentes,
                    "razao_bruta_percentual": (razao_bruta),
                    "cobertura_normalizada_percentual": (cobertura),
                },
                fontes=(
                    FONTE_RESUMO,
                    FONTE_QUALIDADE_TEMPORAL,
                ),
            )

        gaps = _inteiro(qualidade.get(f"janela_{nome_janela}_" "gaps_2x_cadencia"))

        if gaps is not None and gaps > 0:
            adicionar(
                codigo=(f"janela_{nome_janela}:" "gap_2x_cadencia_observado"),
                categoria="continuidade_temporal",
                sujeito=(f"janela_{nome_janela}"),
                descricao=(
                    "Foi observado ao menos um intervalo "
                    "igual ou superior a duas vezes a cadencia."
                ),
                dados={
                    "quantidade_gaps": gaps,
                },
                fontes=(FONTE_QUALIDADE_TEMPORAL,),
            )

        repetidos = _inteiro(qualidade.get(f"janela_{nome_janela}_" "timestamps_repetidos"))

        if repetidos is not None and repetidos > 0:
            adicionar(
                codigo=(f"janela_{nome_janela}:" "timestamp_repetido_observado"),
                categoria="amostragem",
                sujeito=(f"janela_{nome_janela}"),
                descricao=("Foram observados timestamps repetidos " "na janela."),
                dados={
                    "quantidade_repeticoes": (repetidos),
                },
                fontes=(FONTE_QUALIDADE_TEMPORAL,),
            )

    for sinal in _lista_dicts(qualidade.get("sinais")):
        codigo_sinal = _texto(sinal.get("codigo"))

        if codigo_sinal is None:
            continue

        observado = sinal.get("observado_agora") is True

        episodios = _inteiro(sinal.get("quantidade_episodios"))

        reaparecimentos = _inteiro(sinal.get("reaparecimentos"))

        if observado:
            adicionar(
                codigo=("sinal_observado_agora:" + codigo_sinal),
                categoria="sinal",
                sujeito=codigo_sinal,
                descricao=("O sinal esta observado " "na referencia temporal atual."),
                dados={
                    "observado_agora": True,
                },
                fontes=(FONTE_QUALIDADE_TEMPORAL,),
            )

        if (episodios is not None and episodios >= 2) or (
            reaparecimentos is not None and reaparecimentos >= 1
        ):
            adicionar(
                codigo=("recorrencia_observada:" + codigo_sinal),
                categoria="recorrencia",
                sujeito=codigo_sinal,
                descricao=(
                    "O historico acompanha mais de um " "episodio ou ao menos um reaparecimento."
                ),
                dados={
                    "quantidade_episodios": episodios,
                    "reaparecimentos": reaparecimentos,
                },
                fontes=(FONTE_QUALIDADE_TEMPORAL,),
            )

        if sinal.get("inicio_historico_truncado") is True:
            adicionar(
                codigo=("inicio_historico_truncado:" + codigo_sinal),
                categoria="limite_historico",
                sujeito=codigo_sinal,
                descricao=("Ao menos um episodio comeca antes " "do inicio observavel carregado."),
                dados={
                    "inicio_historico_truncado": True,
                },
                fontes=(FONTE_QUALIDADE_TEMPORAL,),
            )

        if sinal.get("episodio_atual_aberto") is True:
            adicionar(
                codigo=("episodio_aberto_no_fim_da_janela:" + codigo_sinal),
                categoria="episodio",
                sujeito=codigo_sinal,
                descricao=("Existe episodio aberto no fim " "da janela historica carregada."),
                dados={
                    "duracao_acompanhada_segundos": (
                        _numero(sinal.get("duracao_episodio_atual_segundos"))
                    ),
                },
                fontes=(FONTE_QUALIDADE_TEMPORAL,),
            )

        cobertura_recente = _numero(sinal.get("cobertura_recente_percentual"))

        cobertura_baseline = _numero(sinal.get("cobertura_baseline_percentual"))

        referencia_sinal = _numero(sinal.get("cobertura_referencia_percentual"))

        for nome_cobertura, valor in (
            (
                "recente",
                cobertura_recente,
            ),
            (
                "baseline",
                cobertura_baseline,
            ),
        ):
            if valor is None or referencia_sinal is None:
                continue

            atingiu = valor >= referencia_sinal

            sufixo = "atinge_referencia" if atingiu else "nao_atinge_referencia"

            adicionar(
                codigo=(f"cobertura_{nome_cobertura}:" f"{sufixo}:" f"{codigo_sinal}"),
                categoria="cobertura_sinal",
                sujeito=codigo_sinal,
                descricao=(
                    "A cobertura relacionada ao sinal "
                    + ("atinge " if atingiu else "nao atinge ")
                    + "a referencia configurada."
                ),
                dados={
                    "janela": nome_cobertura,
                    "cobertura_percentual": valor,
                    "referencia_percentual": (referencia_sinal),
                },
                fontes=(FONTE_QUALIDADE_TEMPORAL,),
            )

    for supressao in _lista_dicts(qualidade.get("supressoes")):
        codigo_supressao = _texto(supressao.get("codigo"))

        if codigo_supressao is None:
            continue

        adicionar(
            codigo=("supressao_observada:" + codigo_supressao),
            categoria="supressao",
            sujeito=codigo_supressao,
            descricao=(
                "Uma supressao observacional esta presente " "na referencia temporal atual."
            ),
            dados={
                "motivo": _texto(supressao.get("motivo")),
                "qualidade_relacionada_tipo": (_texto(supressao.get("qualidade_relacionada_tipo"))),
                "qualidade_relacionada_nome": (_texto(supressao.get("qualidade_relacionada_nome"))),
                "cobertura_recente_percentual": (
                    _numero(supressao.get("cobertura_recente_percentual"))
                ),
                "cobertura_baseline_percentual": (
                    _numero(supressao.get("cobertura_baseline_percentual"))
                ),
                "cobertura_referencia_percentual": (
                    _numero(supressao.get("cobertura_referencia_percentual"))
                ),
            },
            fontes=(
                FONTE_RESUMO,
                FONTE_QUALIDADE_TEMPORAL,
            ),
        )

    observacoes.sort(
        key=lambda item: (
            item.categoria,
            item.codigo,
        )
    )

    return InterpretacaoObservacionalEvidenciasNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=referencia_temporal,
        quantidade_observacoes=len(observacoes),
        observacoes=tuple(observacoes),
    )


def salvar_interpretacao_evidencias_node(
    interpretacao: InterpretacaoObservacionalEvidenciasNode,
    caminho: str | Path = (CAMINHO_INTERPRETACAO_PADRAO),
) -> Path:
    caminho = Path(caminho)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporario = caminho.with_suffix(caminho.suffix + ".tmp")

    temporario.write_text(
        json.dumps(
            interpretacao.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporario.replace(caminho)

    return caminho
