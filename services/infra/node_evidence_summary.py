# 63.8738, -149.7525

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.resumo_evidencias_node import (
    ResumoEvidenciaSinalNode,
    ResumoEvidenciasNode,
    ResumoSupressaoEvidenciaNode,
)
from services.infra.node_health import (
    DIRETORIO_PROJETO,
)

CAMINHO_SINAIS_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "sinais_atual.json"

CAMINHO_ESTADO_TEMPORAL_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "sinais_estado_atual.json"

CAMINHO_HISTORICO_SINAIS_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "analise_historico_sinais_atual.json"
)

CAMINHO_QUALIDADE_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "qualidade_atual.json"

CAMINHO_RESUMO_EVIDENCIAS_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "resumo_evidencias_atual.json"
)


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


def _indexar_por_codigo(
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


def _indexar_por_nome(
    itens: object,
) -> dict[str, dict[str, Any]]:
    resultado = {}

    for item in _lista_dicts(itens):
        nome = item.get("nome")

        if (
            not isinstance(
                nome,
                str,
            )
            or not nome
        ):
            continue

        resultado[nome] = item

    return resultado


def _validar_identidade_temporal(
    sinais: dict[str, Any],
    estado: dict[str, Any],
    historico: dict[str, Any],
    qualidade: dict[str, Any],
) -> tuple[str, str]:
    node_ids = [
        sinais.get("node_id"),
        estado.get("node_id"),
        historico.get("node_id"),
        qualidade.get("node_id"),
    ]

    if not all(
        isinstance(
            valor,
            str,
        )
        and valor
        for valor in node_ids
    ):
        raise ValueError("Node ID ausente em um ou mais artefatos.")

    if len(set(node_ids)) != 1:
        raise ValueError("Artefatos pertencem a nodes diferentes.")

    referencias = [
        sinais.get("referencia_temporal"),
        estado.get("referencia_temporal"),
        historico.get("fim_periodo"),
        qualidade.get("referencia_temporal"),
    ]

    if not all(
        isinstance(
            valor,
            str,
        )
        and valor
        for valor in referencias
    ):
        raise ValueError("Referencia temporal ausente " "em um ou mais artefatos.")

    if len(set(referencias)) != 1:
        raise ValueError("Artefatos pertencem a ciclos temporais diferentes.")

    return (
        node_ids[0],
        referencias[0],
    )


def _qualidade_relacionada(
    codigo: str,
    qualidade: dict[str, Any],
) -> dict[str, Any] | None:
    metricas = _indexar_por_nome(qualidade.get("metricas"))

    servicos = _indexar_por_nome(qualidade.get("servicos"))

    sufixo = (
        codigo.rsplit(
            ":",
            1,
        )[-1]
        if ":" in codigo
        else None
    )

    if sufixo is not None and sufixo in metricas:
        return {
            "tipo": "metrica",
            "nome": sufixo,
            "dados": dict(metricas[sufixo]),
        }

    if sufixo is not None and sufixo in servicos:
        return {
            "tipo": "servico",
            "nome": sufixo,
            "dados": dict(servicos[sufixo]),
        }

    if codigo in {
        "cobertura_coleta_recente_incompleta",
        "amostra_sem_autovisibilidade_processos_recente",
    }:
        janela = qualidade.get("janela_recente")

        if isinstance(
            janela,
            dict,
        ):
            return {
                "tipo": "janela_recente",
                "nome": "janela_recente",
                "dados": dict(janela),
            }

    return None


def _texto(
    valor: object,
    *,
    padrao: str = "",
) -> str:
    if isinstance(
        valor,
        str,
    ):
        return valor

    return padrao


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


def _booleano(
    valor: object,
) -> bool:
    return (
        valor
        if isinstance(
            valor,
            bool,
        )
        else False
    )


def _numero_ou_none(
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


def gerar_resumo_evidencias_node(
    caminho_sinais: str | Path = (CAMINHO_SINAIS_PADRAO),
    caminho_estado_temporal: str | Path = (CAMINHO_ESTADO_TEMPORAL_PADRAO),
    caminho_historico_sinais: str | Path = (CAMINHO_HISTORICO_SINAIS_PADRAO),
    caminho_qualidade: str | Path = (CAMINHO_QUALIDADE_PADRAO),
) -> ResumoEvidenciasNode:
    sinais = _carregar_json(
        caminho_sinais,
        nome="sinais",
    )

    estado = _carregar_json(
        caminho_estado_temporal,
        nome="estado temporal",
    )

    historico = _carregar_json(
        caminho_historico_sinais,
        nome="historico de sinais",
    )

    qualidade = _carregar_json(
        caminho_qualidade,
        nome="qualidade",
    )

    (
        node_id,
        referencia,
    ) = _validar_identidade_temporal(
        sinais,
        estado,
        historico,
        qualidade,
    )

    sinais_atuais = _indexar_por_codigo(sinais.get("sinais"))

    sinais_estado = _indexar_por_codigo(estado.get("sinais"))

    sinais_historico = _indexar_por_codigo(historico.get("sinais"))

    resumos = []

    for codigo in sorted(sinais_estado):
        temporal = sinais_estado[codigo]

        historico_sinal = sinais_historico.get(codigo)

        atual = sinais_atuais.get(codigo)

        evidencia_atual = None

        if atual is not None:
            evidencias = atual.get("evidencias")

            if isinstance(
                evidencias,
                dict,
            ):
                evidencia_atual = dict(evidencias)

        evidencias_recentes = temporal.get("evidencias_mais_recentes")

        if not isinstance(
            evidencias_recentes,
            dict,
        ):
            evidencias_recentes = {}

        historico_disponivel = historico_sinal is not None

        resumos.append(
            ResumoEvidenciaSinalNode(
                codigo=codigo,
                origem=_texto(temporal.get("origem")),
                titulo=_texto(
                    temporal.get("titulo"),
                    padrao=codigo,
                ),
                observado_agora=_booleano(temporal.get("observado_agora")),
                transicao_ultimo_ciclo=_texto(temporal.get("transicao_ultimo_ciclo")),
                primeira_observacao=_texto(temporal.get("primeira_observacao")),
                inicio_sequencia_atual=(
                    temporal.get("inicio_sequencia_atual")
                    if isinstance(
                        temporal.get("inicio_sequencia_atual"),
                        str,
                    )
                    else None
                ),
                ultima_observacao=_texto(temporal.get("ultima_observacao")),
                observacoes_consecutivas=_inteiro(temporal.get("observacoes_consecutivas")),
                observacoes_totais=_inteiro(temporal.get("observacoes_totais")),
                ciclos_ausente_consecutivos=_inteiro(temporal.get("ciclos_ausente_consecutivos")),
                deixou_de_ser_observado_em=(
                    temporal.get("deixou_de_ser_observado_em")
                    if isinstance(
                        temporal.get("deixou_de_ser_observado_em"),
                        str,
                    )
                    else None
                ),
                evidencia_ciclo_atual=(evidencia_atual),
                evidencias_mais_recentes=dict(evidencias_recentes),
                historico_disponivel=(historico_disponivel),
                quantidade_episodios=(
                    _inteiro(historico_sinal.get("quantidade_episodios"))
                    if historico_disponivel
                    else None
                ),
                reaparecimentos=(
                    _inteiro(historico_sinal.get("reaparecimentos"))
                    if historico_disponivel
                    else None
                ),
                duracao_episodio_atual_segundos=(
                    _numero_ou_none(historico_sinal.get("duracao_episodio_atual_segundos"))
                    if historico_disponivel
                    else None
                ),
                maior_duracao_acompanhada_segundos=(
                    _numero_ou_none(historico_sinal.get("maior_duracao_acompanhada_segundos"))
                    if historico_disponivel
                    else None
                ),
                media_duracao_episodios_encerrados_segundos=(
                    _numero_ou_none(
                        historico_sinal.get("media_duracao_episodios_encerrados_segundos")
                    )
                    if historico_disponivel
                    else None
                ),
                ultimo_intervalo_entre_episodios_segundos=(
                    _numero_ou_none(
                        historico_sinal.get("ultimo_intervalo_entre_episodios_segundos")
                    )
                    if historico_disponivel
                    else None
                ),
                media_intervalo_entre_episodios_segundos=(
                    _numero_ou_none(historico_sinal.get("media_intervalo_entre_episodios_segundos"))
                    if historico_disponivel
                    else None
                ),
                qualidade_relacionada=(
                    _qualidade_relacionada(
                        codigo,
                        qualidade,
                    )
                ),
            )
        )

    supressoes = []

    for supressao in _lista_dicts(sinais.get("supressoes")):
        codigo = supressao.get("codigo")

        motivo = supressao.get("motivo")

        if (
            not isinstance(
                codigo,
                str,
            )
            or not codigo
        ):
            continue

        if not isinstance(
            motivo,
            str,
        ):
            motivo = ""

        evidencias = supressao.get("evidencias")

        if not isinstance(
            evidencias,
            dict,
        ):
            evidencias = {}

        supressoes.append(
            ResumoSupressaoEvidenciaNode(
                codigo=codigo,
                motivo=motivo,
                evidencias=dict(evidencias),
                qualidade_relacionada=(
                    _qualidade_relacionada(
                        codigo,
                        qualidade,
                    )
                ),
            )
        )

    janela_recente = qualidade.get("janela_recente")

    if not isinstance(
        janela_recente,
        dict,
    ):
        janela_recente = {}

    janela_baseline = qualidade.get("janela_baseline")

    if not isinstance(
        janela_baseline,
        dict,
    ):
        janela_baseline = {}

    cadencia = _numero_ou_none(qualidade.get("cadencia_nominal_segundos"))

    quantidade_observados = sum(1 for sinal in resumos if sinal.observado_agora)

    return ResumoEvidenciasNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=referencia,
        quantidade_sinais_conhecidos=len(resumos),
        quantidade_sinais_observados_agora=(quantidade_observados),
        quantidade_supressoes_atuais=len(supressoes),
        cadencia_nominal_segundos=cadencia,
        qualidade_janela_recente=dict(janela_recente),
        qualidade_janela_baseline=dict(janela_baseline),
        sinais=tuple(resumos),
        supressoes=tuple(supressoes),
    )


def salvar_resumo_evidencias_node(
    resumo: ResumoEvidenciasNode,
    caminho: str | Path = (CAMINHO_RESUMO_EVIDENCIAS_PADRAO),
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
