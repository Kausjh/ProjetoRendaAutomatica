# 63.8738, -149.7525

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from models.sinais_node import (
    AnaliseSinaisNode,
    SinalNode,
    SupressaoSinalNode,
)
from services.infra.node_data_quality import (
    CAMINHO_QUALIDADE_PADRAO,
)
from services.infra.node_health import (
    CAMINHO_ESTADO_PADRAO,
    DIRETORIO_PROJETO,
)
from services.infra.node_history_analysis import (
    DIRETORIO_HISTORICO_PADRAO,
    MAXIMO_AMOSTRAS_PADRAO,
    MAXIMO_ARQUIVOS_PADRAO,
    carregar_historico_node,
)
from services.infra.node_trend_analysis import (
    CAMINHO_TENDENCIA_PADRAO,
)

CAMINHO_SINAIS_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "sinais_atual.json"

JANELA_SINAIS_RECENTES_MINUTOS = 60

COBERTURA_MINIMA_COMPARACAO_PERCENTUAL = 80.0
AMOSTRAS_MINIMAS_TENDENCIA = 3


SERVICOS_CONTINUOS = (
    "supervisor",
    "node_health_agent",
    "social_scout",
    "runtime",
    "bot_consulta",
    "publicador_fila",
)

DEPENDENCIAS_PERSISTENTES = ("chrome_cdp",)

WORKLOADS_INTERMITENTES = ("pipeline",)


METRICAS_RECURSOS = (
    (
        "cpu_percentual",
        "cpu_percentual",
    ),
    (
        "memoria_host_percentual",
        "memoria_host_percentual",
    ),
    (
        "memoria_processos_projeto_bytes",
        "memoria_processos_projeto_bytes",
    ),
    (
        "quantidade_processos_projeto",
        "quantidade_processos_projeto",
    ),
)


def _ler_json(
    caminho: str | Path,
) -> dict[str, Any]:
    caminho = Path(caminho)

    try:
        valor = json.loads(caminho.read_text(encoding="utf-8"))
    except (
        OSError,
        json.JSONDecodeError,
    ) as erro:
        raise ValueError(f"Nao foi possivel ler {caminho}.") from erro

    if not isinstance(
        valor,
        dict,
    ):
        raise ValueError(f"JSON invalido em {caminho}.")

    return valor


def _numero(
    valor: object,
) -> float | None:
    if isinstance(
        valor,
        bool,
    ):
        return None

    if not isinstance(
        valor,
        (int, float),
    ):
        return None

    numero = float(valor)

    if not math.isfinite(numero):
        return None

    return numero


def _instante(
    valor: object,
) -> datetime | None:
    if not isinstance(
        valor,
        str,
    ):
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

    return instante


def _mapa_servicos(
    registro: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    servicos = registro.get("servicos")

    if not isinstance(
        servicos,
        list,
    ):
        return {}

    resultado: dict[
        str,
        dict[str, Any],
    ] = {}

    for servico in servicos:
        if not isinstance(
            servico,
            dict,
        ):
            continue

        nome = servico.get("nome")

        if not isinstance(
            nome,
            str,
        ):
            continue

        resultado[nome] = servico

    return resultado


def _amostra_sem_autovisibilidade(
    registro: dict[str, Any],
) -> bool:
    quantidade = _numero(registro.get("quantidade_processos_projeto"))

    if quantidade != 0:
        return False

    agente = _mapa_servicos(registro).get("node_health_agent")

    if agente is None:
        return False

    if agente.get("ativo") is not False:
        return False

    pids = agente.get("pids")

    if (
        isinstance(
            pids,
            list,
        )
        and pids
    ):
        return False

    return True


def _cobertura_por_nome(
    qualidade: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    metricas = qualidade.get("metricas")

    if not isinstance(
        metricas,
        list,
    ):
        return {}

    resultado = {}

    for metrica in metricas:
        if not isinstance(
            metrica,
            dict,
        ):
            continue

        nome = metrica.get("nome")

        if isinstance(
            nome,
            str,
        ):
            resultado[nome] = metrica

    return resultado


def _registrar_presenca_atual(
    estado: dict[str, Any],
    sinais: list[SinalNode],
    supressoes: list[SupressaoSinalNode],
) -> None:
    if _amostra_sem_autovisibilidade(estado):
        supressoes.append(
            SupressaoSinalNode(
                codigo=("presenca_servicos_atual"),
                motivo=(
                    "A amostra atual nao possui "
                    "autovisibilidade do Node Agent; "
                    "ausencias de processos nao sao "
                    "interpretadas individualmente."
                ),
                evidencias={
                    "quantidade_processos_projeto": (estado.get("quantidade_processos_projeto")),
                    "coletado_em": estado.get("coletado_em"),
                },
            )
        )

        return

    servicos = _mapa_servicos(estado)

    for nome in SERVICOS_CONTINUOS:
        servico = servicos.get(nome)

        if servico is not None and servico.get("ativo") is True:
            continue

        sinais.append(
            SinalNode(
                codigo=("servico_continuo_ausente_atual:" + nome),
                origem="estado_atual",
                titulo=(f"Servico continuo ausente: {nome}"),
                descricao=(
                    "O componente esperado continuamente " "nao aparece ativo na amostra atual."
                ),
                evidencias={
                    "servico": nome,
                    "ativo": (None if servico is None else servico.get("ativo")),
                    "pids": (None if servico is None else servico.get("pids")),
                    "coletado_em": estado.get("coletado_em"),
                },
            )
        )

    for nome in DEPENDENCIAS_PERSISTENTES:
        servico = servicos.get(nome)

        if servico is not None and servico.get("ativo") is True:
            continue

        sinais.append(
            SinalNode(
                codigo=("dependencia_persistente_ausente_atual:" + nome),
                origem="estado_atual",
                titulo=(f"Dependencia persistente ausente: {nome}"),
                descricao=(
                    "A dependencia esperada persistentemente " "nao aparece ativa na amostra atual."
                ),
                evidencias={
                    "servico": nome,
                    "ativo": (None if servico is None else servico.get("ativo")),
                    "pids": (None if servico is None else servico.get("pids")),
                    "coletado_em": estado.get("coletado_em"),
                },
            )
        )


def _registrar_amostras_sem_visibilidade(
    registros: tuple[
        dict[str, Any],
        ...,
    ],
    sinais: list[SinalNode],
) -> None:
    validos = [
        (
            instante,
            registro,
        )
        for registro in registros
        if (instante := _instante(registro.get("coletado_em"))) is not None
    ]

    if not validos:
        return

    referencia = max(instante for instante, _ in validos)

    inicio = referencia - timedelta(minutes=(JANELA_SINAIS_RECENTES_MINUTOS))

    afetadas = [
        instante.isoformat()
        for instante, registro in validos
        if (inicio <= instante <= referencia and _amostra_sem_autovisibilidade(registro))
    ]

    if not afetadas:
        return

    sinais.append(
        SinalNode(
            codigo=("amostra_sem_autovisibilidade_processos_recente"),
            origem="historico_recente",
            titulo=("Amostra recente sem autovisibilidade " "de processos"),
            descricao=(
                "Uma ou mais coletas recentes registraram "
                "zero processos do projeto e o proprio "
                "Node Agent como inativo. Essas amostras "
                "nao devem ser interpretadas como quedas "
                "individuais dos servicos."
            ),
            evidencias={
                "quantidade_amostras": len(afetadas),
                "timestamps": afetadas,
                "janela_minutos": (JANELA_SINAIS_RECENTES_MINUTOS),
            },
        )
    )


def _registrar_qualidade_coleta(
    qualidade: dict[str, Any],
    sinais: list[SinalNode],
) -> None:
    recente = qualidade.get("janela_recente")

    if not isinstance(
        recente,
        dict,
    ):
        return

    esperadas = recente.get("amostras_esperadas")

    observadas = recente.get("amostras_observadas")

    gaps = recente.get("gaps_igual_ou_acima_2x_cadencia")

    repetidos = recente.get("timestamps_repetidos")

    incompleta = (
        isinstance(esperadas, int) and isinstance(observadas, int) and observadas < esperadas
    )

    gaps_presentes = isinstance(gaps, int) and gaps > 0

    repetidos_presentes = isinstance(repetidos, int) and repetidos > 0

    if not (incompleta or gaps_presentes or repetidos_presentes):
        return

    sinais.append(
        SinalNode(
            codigo=("cobertura_coleta_recente_incompleta"),
            origem="qualidade",
            titulo=("Cobertura recente da coleta nao foi integral"),
            descricao=(
                "A janela recente possui ausencia de amostras, "
                "gap temporal relevante ou timestamp repetido."
            ),
            evidencias={
                "amostras_esperadas": esperadas,
                "amostras_observadas": observadas,
                "gaps_2x": gaps,
                "timestamps_repetidos": repetidos,
                "razao_amostras_percentual": (recente.get("razao_amostras_percentual")),
            },
        )
    )


def _registrar_tendencias_recursos(
    tendencia: dict[str, Any],
    qualidade: dict[str, Any],
    sinais: list[SinalNode],
    supressoes: list[SupressaoSinalNode],
) -> None:
    coberturas = _cobertura_por_nome(qualidade)

    for (
        nome_qualidade,
        nome_tendencia,
    ) in METRICAS_RECURSOS:
        cobertura = coberturas.get(nome_qualidade)

        dados = tendencia.get(nome_tendencia)

        if not isinstance(
            cobertura,
            dict,
        ):
            continue

        if not isinstance(
            dados,
            dict,
        ):
            continue

        comparavel = cobertura.get("comparacao_disponivel") is True

        presenca_recente = _numero(cobertura.get("percentual_presenca_recente"))

        presenca_baseline = _numero(cobertura.get("percentual_presenca_baseline"))

        n_recente = dados.get("amostras_recente")

        n_baseline = dados.get("amostras_baseline")

        evidencia_suficiente = (
            comparavel
            and presenca_recente is not None
            and presenca_baseline is not None
            and presenca_recente >= COBERTURA_MINIMA_COMPARACAO_PERCENTUAL
            and presenca_baseline >= COBERTURA_MINIMA_COMPARACAO_PERCENTUAL
            and isinstance(n_recente, int)
            and isinstance(n_baseline, int)
            and n_recente >= AMOSTRAS_MINIMAS_TENDENCIA
            and n_baseline >= AMOSTRAS_MINIMAS_TENDENCIA
        )

        if not evidencia_suficiente:
            supressoes.append(
                SupressaoSinalNode(
                    codigo=("tendencia_recurso:" + nome_qualidade),
                    motivo=("Evidencia insuficiente para " "comparacao recente versus baseline."),
                    evidencias={
                        "comparacao_disponivel": comparavel,
                        "presenca_recente_percentual": (presenca_recente),
                        "presenca_baseline_percentual": (presenca_baseline),
                        "amostras_recente": n_recente,
                        "amostras_baseline": n_baseline,
                        "cobertura_minima_percentual": (COBERTURA_MINIMA_COMPARACAO_PERCENTUAL),
                        "amostras_minimas": (AMOSTRAS_MINIMAS_TENDENCIA),
                    },
                )
            )

            continue

        atual = _numero(dados.get("atual"))

        media_recente = _numero(dados.get("media_recente"))

        media_baseline = _numero(dados.get("media_baseline"))

        inclinacao = _numero(dados.get("inclinacao_recente_por_hora"))

        if atual is None or media_recente is None or media_baseline is None or inclinacao is None:
            continue

        if not (atual > media_recente > media_baseline and inclinacao > 0):
            continue

        sinais.append(
            SinalNode(
                codigo=("recurso_acima_baseline_e_subindo:" + nome_qualidade),
                origem="tendencia",
                titulo=("Recurso acima do baseline " "e com inclinacao positiva"),
                descricao=(
                    "O valor atual esta acima da media recente, "
                    "a media recente esta acima do baseline e "
                    "a regressao da janela recente possui "
                    "inclinacao positiva."
                ),
                evidencias={
                    "metrica": nome_qualidade,
                    "atual": atual,
                    "media_recente": media_recente,
                    "media_baseline": media_baseline,
                    "inclinacao_por_hora": inclinacao,
                    "delta_media_absoluto": (dados.get("delta_media_absoluto")),
                    "delta_media_percentual": (dados.get("delta_media_percentual")),
                    "amostras_recente": n_recente,
                    "amostras_baseline": n_baseline,
                    "presenca_recente_percentual": (presenca_recente),
                    "presenca_baseline_percentual": (presenca_baseline),
                },
            )
        )


def analisar_sinais_node(
    caminho_estado: str | Path = (CAMINHO_ESTADO_PADRAO),
    caminho_tendencia: str | Path = (CAMINHO_TENDENCIA_PADRAO),
    caminho_qualidade: str | Path = (CAMINHO_QUALIDADE_PADRAO),
    diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
    *,
    maximo_arquivos: int = (MAXIMO_ARQUIVOS_PADRAO),
    maximo_amostras: int = (MAXIMO_AMOSTRAS_PADRAO),
) -> AnaliseSinaisNode:
    estado = _ler_json(caminho_estado)

    tendencia = _ler_json(caminho_tendencia)

    qualidade = _ler_json(caminho_qualidade)

    registros = carregar_historico_node(
        diretorio_historico,
        maximo_arquivos=maximo_arquivos,
        maximo_amostras=maximo_amostras,
    )

    sinais: list[SinalNode] = []
    supressoes: list[SupressaoSinalNode] = []

    _registrar_presenca_atual(
        estado,
        sinais,
        supressoes,
    )

    _registrar_amostras_sem_visibilidade(
        registros,
        sinais,
    )

    _registrar_qualidade_coleta(
        qualidade,
        sinais,
    )

    _registrar_tendencias_recursos(
        tendencia,
        qualidade,
        sinais,
        supressoes,
    )

    node_id = estado.get("node_id")

    if not isinstance(
        node_id,
        str,
    ):
        node_id = None

    referencia = estado.get("coletado_em")

    if not isinstance(
        referencia,
        str,
    ):
        referencia = None

    return AnaliseSinaisNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=referencia,
        servicos_continuos=SERVICOS_CONTINUOS,
        dependencias_persistentes=(DEPENDENCIAS_PERSISTENTES),
        workloads_intermitentes=(WORKLOADS_INTERMITENTES),
        sinais=tuple(sinais),
        supressoes=tuple(supressoes),
    )


def salvar_sinais_node(
    analise: AnaliseSinaisNode,
    caminho: str | Path = (CAMINHO_SINAIS_PADRAO),
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
