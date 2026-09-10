# 63.8738, -149.7525

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from models.analise_historico_sinais import (
    AnaliseHistoricoSinaisNode,
    EpisodioTemporalSinalNode,
    ResumoHistoricoSinalNode,
)
from services.infra.node_health import (
    DIRETORIO_PROJETO,
)
from services.infra.node_signal_state import (
    DIRETORIO_HISTORICO_TEMPORAL_SINAIS_PADRAO,
)

CAMINHO_ANALISE_HISTORICO_SINAIS_PADRAO = (
    DIRETORIO_PROJETO / "data" / "node" / "analise_historico_sinais_atual.json"
)

MAXIMO_ARQUIVOS_PADRAO = 30
MAXIMO_AMOSTRAS_PADRAO = 10000


def _instante(
    valor: object,
) -> datetime | None:
    if not isinstance(valor, str):
        return None

    texto = valor.strip()

    if not texto:
        return None

    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"

    try:
        instante = datetime.fromisoformat(texto)

    except ValueError:
        return None

    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)

    return instante.astimezone(UTC)


def _carregar_registros(
    diretorio: str | Path,
    *,
    maximo_arquivos: int,
    maximo_amostras: int,
) -> tuple[
    list[
        tuple[
            datetime,
            dict[str, Any],
        ]
    ],
    int,
    int,
]:
    if maximo_arquivos <= 0:
        raise ValueError("maximo_arquivos precisa ser maior que zero.")

    if maximo_amostras <= 0:
        raise ValueError("maximo_amostras precisa ser maior que zero.")

    diretorio = Path(diretorio)

    arquivos = sorted(diretorio.glob("*.jsonl"))[-maximo_arquivos:]

    registros = []
    invalidas = 0

    for arquivo in arquivos:
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()

        except OSError:
            invalidas += 1
            continue

        for linha in linhas:
            if not linha.strip():
                continue

            try:
                registro = json.loads(linha)

            except json.JSONDecodeError:
                invalidas += 1
                continue

            if not isinstance(
                registro,
                dict,
            ):
                invalidas += 1
                continue

            instante = _instante(registro.get("referencia_temporal"))

            if instante is None:
                invalidas += 1
                continue

            registros.append(
                (
                    instante,
                    registro,
                )
            )

    registros.sort(key=lambda item: item[0])

    if len(registros) > maximo_amostras:
        registros = registros[-maximo_amostras:]

    if not registros:
        raise ValueError("Historico temporal de sinais vazio.")

    node_id_atual = registros[-1][1].get("node_id")

    registros = [item for item in registros if item[1].get("node_id") == node_id_atual]

    unicos = []
    duplicadas = 0

    for instante, registro in registros:
        if unicos and instante == unicos[-1][0]:
            anterior = unicos[-1][1]

            if anterior != registro:
                raise ValueError(
                    "Historico temporal possui " "amostras inconsistentes no " "mesmo instante."
                )

            duplicadas += 1
            continue

        unicos.append(
            (
                instante,
                registro,
            )
        )

    return (
        unicos,
        invalidas,
        duplicadas,
    )


def _mapa_sinais(
    registro: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    sinais = registro.get("sinais")

    if not isinstance(
        sinais,
        list,
    ):
        return {}

    resultado = {}

    for sinal in sinais:
        if not isinstance(
            sinal,
            dict,
        ):
            continue

        codigo = sinal.get("codigo")

        if (
            not isinstance(
                codigo,
                str,
            )
            or not codigo
        ):
            continue

        resultado[codigo] = sinal

    return resultado


def analisar_historico_sinais_node(
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_TEMPORAL_SINAIS_PADRAO),
    *,
    maximo_arquivos: int = MAXIMO_ARQUIVOS_PADRAO,
    maximo_amostras: int = MAXIMO_AMOSTRAS_PADRAO,
) -> AnaliseHistoricoSinaisNode:
    (
        registros,
        invalidas,
        duplicadas,
    ) = _carregar_registros(
        diretorio_historico,
        maximo_arquivos=maximo_arquivos,
        maximo_amostras=maximo_amostras,
    )

    primeira_referencia = registros[0][1]["referencia_temporal"]

    ultima_referencia = registros[-1][1]["referencia_temporal"]

    node_id = registros[-1][1].get("node_id")

    if not isinstance(
        node_id,
        str,
    ):
        node_id = None

    trabalhos: dict[
        str,
        dict[str, Any],
    ] = {}

    for instante, registro in registros:
        referencia = registro.get("referencia_temporal")

        if not isinstance(
            referencia,
            str,
        ):
            continue

        sinais = _mapa_sinais(registro)

        for codigo, sinal in sinais.items():
            observado = sinal.get("observado_agora")

            if not isinstance(
                observado,
                bool,
            ):
                continue

            origem = sinal.get("origem")

            titulo = sinal.get("titulo")

            if not isinstance(
                origem,
                str,
            ):
                origem = ""

            if not isinstance(
                titulo,
                str,
            ):
                titulo = codigo

            trabalho = trabalhos.setdefault(
                codigo,
                {
                    "origem": origem,
                    "titulo": titulo,
                    "ultimo_estado": None,
                    "ativo": None,
                    "episodios": [],
                },
            )

            trabalho["origem"] = origem

            trabalho["titulo"] = titulo

            ativo = trabalho["ativo"]

            transicao = sinal.get("transicao_ultimo_ciclo")

            if observado:
                if ativo is None:
                    inicio_confirmado = transicao in {
                        "novo",
                        "reapareceu",
                    }

                    trabalho["ativo"] = {
                        "inicio_em": referencia,
                        "inicio_dt": instante,
                        "inicio_confirmado": (inicio_confirmado),
                        "observacoes": 1,
                        "ultima_dt": instante,
                    }

                else:
                    ativo["observacoes"] += 1

                    ativo["ultima_dt"] = instante

            else:
                if ativo is not None:
                    duracao = max(
                        0.0,
                        (instante - ativo["inicio_dt"]).total_seconds(),
                    )

                    trabalho["episodios"].append(
                        EpisodioTemporalSinalNode(
                            inicio_em=ativo["inicio_em"],
                            fim_detectado_em=referencia,
                            inicio_confirmado=ativo["inicio_confirmado"],
                            aberto_no_fim_da_janela=False,
                            observacoes_ativas=ativo["observacoes"],
                            duracao_acompanhada_segundos=duracao,
                        )
                    )

                    trabalho["ativo"] = None

            trabalho["ultimo_estado"] = observado

    fim_dt = registros[-1][0]

    resumos = []

    for codigo in sorted(trabalhos):
        trabalho = trabalhos[codigo]

        episodios = list(trabalho["episodios"])

        ativo = trabalho["ativo"]

        if ativo is not None:
            duracao = max(
                0.0,
                (fim_dt - ativo["inicio_dt"]).total_seconds(),
            )

            episodios.append(
                EpisodioTemporalSinalNode(
                    inicio_em=ativo["inicio_em"],
                    fim_detectado_em=None,
                    inicio_confirmado=ativo["inicio_confirmado"],
                    aberto_no_fim_da_janela=True,
                    observacoes_ativas=ativo["observacoes"],
                    duracao_acompanhada_segundos=duracao,
                )
            )

        duracoes = [episodio.duracao_acompanhada_segundos for episodio in episodios]

        encerrados = [
            episodio.duracao_acompanhada_segundos
            for episodio in episodios
            if not episodio.aberto_no_fim_da_janela
        ]

        intervalos = []

        for anterior, seguinte in zip(
            episodios,
            episodios[1:],
            strict=False,
        ):
            if anterior.fim_detectado_em is None:
                continue

            fim_anterior = _instante(anterior.fim_detectado_em)

            inicio_seguinte = _instante(seguinte.inicio_em)

            if fim_anterior is None or inicio_seguinte is None:
                continue

            intervalos.append(
                max(
                    0.0,
                    (inicio_seguinte - fim_anterior).total_seconds(),
                )
            )

        observado_agora = trabalho["ultimo_estado"] is True

        duracao_atual = None

        if observado_agora and episodios and episodios[-1].aberto_no_fim_da_janela:
            duracao_atual = episodios[-1].duracao_acompanhada_segundos

        maior_duracao = max(duracoes) if duracoes else None

        media_encerrados = sum(encerrados) / len(encerrados) if encerrados else None

        ultimo_intervalo = intervalos[-1] if intervalos else None

        media_intervalos = sum(intervalos) / len(intervalos) if intervalos else None

        quantidade_episodios = len(episodios)

        resumos.append(
            ResumoHistoricoSinalNode(
                codigo=codigo,
                origem=trabalho["origem"],
                titulo=trabalho["titulo"],
                observado_agora=observado_agora,
                quantidade_episodios=quantidade_episodios,
                reaparecimentos=max(
                    0,
                    quantidade_episodios - 1,
                ),
                duracao_episodio_atual_segundos=(duracao_atual),
                maior_duracao_acompanhada_segundos=(maior_duracao),
                media_duracao_episodios_encerrados_segundos=(media_encerrados),
                ultimo_intervalo_entre_episodios_segundos=(ultimo_intervalo),
                media_intervalo_entre_episodios_segundos=(media_intervalos),
                episodios=tuple(episodios),
            )
        )

    return AnaliseHistoricoSinaisNode(
        versao_schema=1,
        node_id=node_id,
        inicio_periodo=primeira_referencia,
        fim_periodo=ultima_referencia,
        quantidade_amostras=len(registros),
        linhas_invalidas_ignoradas=invalidas,
        amostras_duplicadas_ignoradas=duplicadas,
        sinais=tuple(resumos),
    )


def salvar_analise_historico_sinais_node(
    analise: AnaliseHistoricoSinaisNode,
    caminho: str | Path = (CAMINHO_ANALISE_HISTORICO_SINAIS_PADRAO),
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
