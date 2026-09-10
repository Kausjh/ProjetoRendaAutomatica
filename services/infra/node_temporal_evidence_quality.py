# 63.8738, -149.7525

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.qualidade_evidencia_temporal_node import (
    AnaliseQualidadeTemporalEvidenciaNode,
    QualidadeTemporalEvidenciaSinalNode,
    QualidadeTemporalSupressaoNode,
)
from services.infra.node_health import (
    DIRETORIO_PROJETO,
)

CAMINHO_RESUMO_EVIDENCIAS_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "resumo_evidencias_atual.json"
)

CAMINHO_HISTORICO_SINAIS_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "analise_historico_sinais_atual.json"
)

CAMINHO_QUALIDADE_EVIDENCIA_TEMPORAL_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "qualidade_evidencia_temporal_atual.json"
)

COBERTURA_REFERENCIA_PERCENTUAL = 80.0


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


def _indexar_codigo(
    itens: object,
) -> dict[str, dict[str, Any]]:
    resultado = {}

    for item in _lista_dicts(itens):
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


def _texto_ou_none(
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


def _atinge_referencia(
    cobertura: float | None,
    referencia: float | None,
) -> bool | None:
    if cobertura is None or referencia is None:
        return None

    return cobertura >= referencia


def _cobertura_janela(
    dados: object,
) -> float | None:
    if not isinstance(
        dados,
        dict,
    ):
        return None

    normalizada = _numero(dados.get("cobertura_normalizada_percentual"))

    if normalizada is not None:
        return normalizada

    return _numero(dados.get("razao_amostras_percentual"))


def _extrair_cobertura(
    qualidade_relacionada: object,
) -> tuple[
    str | None,
    str | None,
    float | None,
    float | None,
]:
    if not isinstance(
        qualidade_relacionada,
        dict,
    ):
        return (
            None,
            None,
            None,
            None,
        )

    tipo = _texto_ou_none(qualidade_relacionada.get("tipo"))

    nome = _texto_ou_none(qualidade_relacionada.get("nome"))

    dados = qualidade_relacionada.get("dados")

    if not isinstance(
        dados,
        dict,
    ):
        return (
            tipo,
            nome,
            None,
            None,
        )

    if tipo in {
        "metrica",
        "servico",
    }:
        recente = _numero(dados.get("percentual_presenca_recente"))

        baseline = _numero(dados.get("percentual_presenca_baseline"))

        return (
            tipo,
            nome,
            recente,
            baseline,
        )

    if tipo == "janela_recente":
        recente = _cobertura_janela(dados)

        return (
            tipo,
            nome,
            recente,
            None,
        )

    return (
        tipo,
        nome,
        None,
        None,
    )


def _validar_consistencia(
    resumo: dict[str, Any],
    historico: dict[str, Any],
) -> tuple[str, str]:
    node_resumo = resumo.get("node_id")

    node_historico = historico.get("node_id")

    if (
        not isinstance(
            node_resumo,
            str,
        )
        or not node_resumo
    ):
        raise ValueError("Node ID ausente no resumo.")

    if (
        not isinstance(
            node_historico,
            str,
        )
        or not node_historico
    ):
        raise ValueError("Node ID ausente no historico.")

    if node_resumo != node_historico:
        raise ValueError("Artefatos pertencem a nodes diferentes.")

    referencia_resumo = resumo.get("referencia_temporal")

    referencia_historico = historico.get("fim_periodo")

    instante_resumo = _instante(referencia_resumo)

    instante_historico = _instante(referencia_historico)

    if instante_resumo != instante_historico:
        raise ValueError("Artefatos pertencem a ciclos temporais diferentes.")

    return (
        node_resumo,
        str(referencia_resumo),
    )


def _episodios_do_historico(
    historico_sinal: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if historico_sinal is None:
        return []

    return _lista_dicts(historico_sinal.get("episodios"))


def analisar_qualidade_temporal_evidencia_node(
    caminho_resumo: str | Path = (CAMINHO_RESUMO_EVIDENCIAS_PADRAO),
    caminho_historico_sinais: str | Path = (CAMINHO_HISTORICO_SINAIS_PADRAO),
    *,
    cobertura_referencia_percentual: float = (COBERTURA_REFERENCIA_PERCENTUAL),
) -> AnaliseQualidadeTemporalEvidenciaNode:
    if not (0.0 <= cobertura_referencia_percentual <= 100.0):
        raise ValueError("Referencia de cobertura invalida.")

    resumo = _carregar_json(
        caminho_resumo,
        nome="resumo de evidencias",
    )

    historico = _carregar_json(
        caminho_historico_sinais,
        nome="historico de sinais",
    )

    (
        node_id,
        referencia_temporal,
    ) = _validar_consistencia(
        resumo,
        historico,
    )

    historico_por_codigo = _indexar_codigo(historico.get("sinais"))

    sinais_resultado = []

    for sinal in _lista_dicts(resumo.get("sinais")):
        codigo = sinal.get("codigo")

        if (
            not isinstance(
                codigo,
                str,
            )
            or not codigo
        ):
            continue

        historico_sinal = historico_por_codigo.get(codigo)

        episodios = _episodios_do_historico(historico_sinal)

        historico_disponivel = isinstance(
            historico_sinal,
            dict,
        )

        inicio_truncado = None
        episodio_aberto = None

        if historico_disponivel:
            inicio_truncado = any(
                episodio.get("inicio_confirmado") is False for episodio in episodios
            )

            episodio_aberto = any(
                episodio.get("aberto_no_fim_da_janela") is True for episodio in episodios
            )

        (
            qualidade_tipo,
            qualidade_nome,
            cobertura_recente,
            cobertura_baseline,
        ) = _extrair_cobertura(sinal.get("qualidade_relacionada"))

        quantidade_episodios = _inteiro(sinal.get("quantidade_episodios"))

        reaparecimentos = _inteiro(sinal.get("reaparecimentos"))

        sinais_resultado.append(
            QualidadeTemporalEvidenciaSinalNode(
                codigo=codigo,
                observado_agora=(sinal.get("observado_agora") is True),
                quantidade_episodios=(quantidade_episodios),
                reaparecimentos=(reaparecimentos),
                inicio_historico_truncado=(inicio_truncado),
                episodio_atual_aberto=(episodio_aberto),
                duracao_episodio_atual_segundos=(
                    _numero(sinal.get("duracao_episodio_atual_segundos"))
                ),
                maior_duracao_acompanhada_segundos=(
                    _numero(sinal.get("maior_duracao_acompanhada_segundos"))
                ),
                qualidade_relacionada_tipo=(qualidade_tipo),
                qualidade_relacionada_nome=(qualidade_nome),
                cobertura_recente_percentual=(cobertura_recente),
                cobertura_baseline_percentual=(cobertura_baseline),
                cobertura_referencia_percentual=(cobertura_referencia_percentual),
                cobertura_recente_atinge_referencia=(
                    _atinge_referencia(
                        cobertura_recente,
                        cobertura_referencia_percentual,
                    )
                ),
                cobertura_baseline_atinge_referencia=(
                    _atinge_referencia(
                        cobertura_baseline,
                        cobertura_referencia_percentual,
                    )
                ),
            )
        )

    supressoes_resultado = []

    for supressao in _lista_dicts(resumo.get("supressoes")):
        codigo = supressao.get("codigo")

        if (
            not isinstance(
                codigo,
                str,
            )
            or not codigo
        ):
            continue

        motivo = supressao.get("motivo")

        if not isinstance(
            motivo,
            str,
        ):
            motivo = ""

        (
            qualidade_tipo,
            qualidade_nome,
            cobertura_recente,
            cobertura_baseline,
        ) = _extrair_cobertura(supressao.get("qualidade_relacionada"))

        evidencias = supressao.get("evidencias")

        referencia_supressao = None

        if isinstance(
            evidencias,
            dict,
        ):
            referencia_supressao = _numero(evidencias.get("cobertura_minima_percentual"))

        if referencia_supressao is None:
            referencia_supressao = cobertura_referencia_percentual

        supressoes_resultado.append(
            QualidadeTemporalSupressaoNode(
                codigo=codigo,
                motivo=motivo,
                qualidade_relacionada_tipo=(qualidade_tipo),
                qualidade_relacionada_nome=(qualidade_nome),
                cobertura_recente_percentual=(cobertura_recente),
                cobertura_baseline_percentual=(cobertura_baseline),
                cobertura_referencia_percentual=(referencia_supressao),
                cobertura_recente_atinge_referencia=(
                    _atinge_referencia(
                        cobertura_recente,
                        referencia_supressao,
                    )
                ),
                cobertura_baseline_atinge_referencia=(
                    _atinge_referencia(
                        cobertura_baseline,
                        referencia_supressao,
                    )
                ),
            )
        )

    janela_recente = resumo.get("qualidade_janela_recente")

    if not isinstance(
        janela_recente,
        dict,
    ):
        janela_recente = {}

    janela_baseline = resumo.get("qualidade_janela_baseline")

    if not isinstance(
        janela_baseline,
        dict,
    ):
        janela_baseline = {}

    return AnaliseQualidadeTemporalEvidenciaNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=referencia_temporal,
        cobertura_referencia_percentual=(cobertura_referencia_percentual),
        janela_recente_cobertura_percentual=(_cobertura_janela(janela_recente)),
        janela_baseline_cobertura_percentual=(_cobertura_janela(janela_baseline)),
        janela_recente_amostras_esperadas=(_inteiro(janela_recente.get("amostras_esperadas"))),
        janela_recente_amostras_observadas=(_inteiro(janela_recente.get("amostras_observadas"))),
        janela_baseline_amostras_esperadas=(_inteiro(janela_baseline.get("amostras_esperadas"))),
        janela_baseline_amostras_observadas=(_inteiro(janela_baseline.get("amostras_observadas"))),
        janela_recente_gaps_2x_cadencia=(
            _inteiro(janela_recente.get("gaps_igual_ou_acima_2x_cadencia"))
        ),
        janela_baseline_gaps_2x_cadencia=(
            _inteiro(janela_baseline.get("gaps_igual_ou_acima_2x_cadencia"))
        ),
        janela_recente_timestamps_repetidos=(_inteiro(janela_recente.get("timestamps_repetidos"))),
        janela_baseline_timestamps_repetidos=(
            _inteiro(janela_baseline.get("timestamps_repetidos"))
        ),
        quantidade_sinais=len(sinais_resultado),
        quantidade_supressoes=len(supressoes_resultado),
        sinais=tuple(sinais_resultado),
        supressoes=tuple(supressoes_resultado),
    )


def salvar_qualidade_temporal_evidencia_node(
    analise: AnaliseQualidadeTemporalEvidenciaNode,
    caminho: str | Path = (CAMINHO_QUALIDADE_EVIDENCIA_TEMPORAL_PADRAO),
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
