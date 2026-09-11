from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from typing import Any

from services.scout.dataset_learning_discovery_comercial_hunter import (
    criar_dataset_learning_discovery_comercial_hunter,
)

# 63.8738, -149.7525

SCHEMA_VERSION = 1

DIAS_JANELA_PADRAO = 7
HORAS_MATURACAO_PADRAO = 24


def criar_janela_learning_discovery_comercial_hunter(
    *,
    relatorios_execucao: Iterable[Mapping[str, Any]] = (),
    historico_publicacoes: Iterable[Mapping[str, Any]] = (),
    agora: datetime | str | None = None,
    dias_janela: float = DIAS_JANELA_PADRAO,
    horas_maturacao: float = HORAS_MATURACAO_PADRAO,
) -> dict[str, Any]:
    """Separa evidencias maduras das ainda recentes.

    O objetivo desta camada e impedir que sinais recentes sejam
    julgados antes de terem tempo razoavel para produzir resultado.

    A funcao permanece observacional:
    - nao calcula score;
    - nao altera prioridade;
    - nao calcula conversao fila -> publicacao;
    - nao tenta ligar uma publicacao a um termo individual.
    """

    dias = float(dias_janela)

    horas = float(horas_maturacao)

    if dias <= 0:
        raise ValueError("dias_janela deve ser maior que zero")

    if horas < 0:
        raise ValueError("horas_maturacao nao pode ser negativa")

    if horas >= (dias * 24.0):
        raise ValueError("horas_maturacao deve ser menor que a janela total")

    agora_normalizado = _normalizar_agora(agora)

    inicio_janela = agora_normalizado - timedelta(days=dias)

    limite_maturacao = agora_normalizado - timedelta(hours=horas)

    relatorios_maduros: list[Mapping[str, Any]] = []

    relatorios_recentes: list[Mapping[str, Any]] = []

    relatorios_invalidos = 0
    relatorios_fora_janela = 0
    relatorios_futuros = 0

    for relatorio in relatorios_execucao:
        if not isinstance(
            relatorio,
            Mapping,
        ):
            continue

        data_hora = _normalizar_data_evento(
            relatorio.get("data_hora"),
            agora_normalizado,
        )

        if data_hora is None:
            relatorios_invalidos += 1
            continue

        if data_hora > agora_normalizado:
            relatorios_futuros += 1
            continue

        if data_hora < inicio_janela:
            relatorios_fora_janela += 1
            continue

        if data_hora <= limite_maturacao:
            relatorios_maduros.append(relatorio)
        else:
            relatorios_recentes.append(relatorio)

    publicacoes_maduras: list[Mapping[str, Any]] = []

    publicacoes_recentes: list[Mapping[str, Any]] = []

    publicacoes_invalidas = 0
    publicacoes_fora_janela = 0
    publicacoes_futuras = 0

    for publicacao in historico_publicacoes:
        if not isinstance(
            publicacao,
            Mapping,
        ):
            continue

        publicado_em = _normalizar_data_evento(
            publicacao.get("publicado_em"),
            agora_normalizado,
        )

        if publicado_em is None:
            publicacoes_invalidas += 1
            continue

        if publicado_em > agora_normalizado:
            publicacoes_futuras += 1
            continue

        if publicado_em < inicio_janela:
            publicacoes_fora_janela += 1
            continue

        if publicado_em <= limite_maturacao:
            publicacoes_maduras.append(publicacao)
        else:
            publicacoes_recentes.append(publicacao)

    dataset_maduro = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=(relatorios_maduros),
        historico_publicacoes=(publicacoes_maduras),
    )

    dataset_recente = criar_dataset_learning_discovery_comercial_hunter(
        relatorios_execucao=(relatorios_recentes),
        historico_publicacoes=(publicacoes_recentes),
    )

    quantidade_madura = len(relatorios_maduros) + len(publicacoes_maduras)

    quantidade_recente = len(relatorios_recentes) + len(publicacoes_recentes)

    if quantidade_madura == 0 and quantidade_recente == 0:
        status = "sem_evidencias_na_janela"
    elif quantidade_madura == 0:
        status = "aguardando_maturacao"
    else:
        status = "evidencia_madura_disponivel"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "janela": {
            "dias": dias,
            "horas_maturacao": horas,
            "inicio": inicio_janela.isoformat(timespec="seconds"),
            "limite_maturacao": (limite_maturacao.isoformat(timespec="seconds")),
            "agora": agora_normalizado.isoformat(timespec="seconds"),
        },
        "relatorios": {
            "maduros": len(relatorios_maduros),
            "recentes": len(relatorios_recentes),
            "invalidos": relatorios_invalidos,
            "fora_janela": (relatorios_fora_janela),
            "futuros": relatorios_futuros,
        },
        "publicacoes": {
            "maduras": len(publicacoes_maduras),
            "recentes": len(publicacoes_recentes),
            "invalidas": publicacoes_invalidas,
            "fora_janela": (publicacoes_fora_janela),
            "futuras": publicacoes_futuras,
        },
        "tem_evidencia_madura": (quantidade_madura > 0),
        "tem_evidencia_recente": (quantidade_recente > 0),
        "dataset_maduro": dataset_maduro,
        "dataset_recente": dataset_recente,
        "publicacao_assincrona": True,
        "taxa_publicacao_nao_calculada": True,
        "score_learning_calculado": False,
        "influencia_priorizacao": False,
    }


def _normalizar_agora(
    valor: datetime | str | None,
) -> datetime:
    if valor is None:
        return datetime.now().astimezone()

    if isinstance(
        valor,
        datetime,
    ):
        resultado = valor
    elif isinstance(
        valor,
        str,
    ):
        try:
            resultado = datetime.fromisoformat(valor.strip())
        except ValueError as erro:
            raise ValueError("agora possui formato invalido") from erro
    else:
        raise TypeError("agora deve ser datetime, string ISO ou None")

    if resultado.tzinfo is None:
        timezone_local = datetime.now().astimezone().tzinfo

        resultado = resultado.replace(tzinfo=timezone_local)

    return resultado


def _normalizar_data_evento(
    valor: Any,
    referencia: datetime,
) -> datetime | None:
    if isinstance(
        valor,
        datetime,
    ):
        resultado = valor
    elif isinstance(
        valor,
        str,
    ):
        texto = valor.strip()

        if not texto:
            return None

        try:
            resultado = datetime.fromisoformat(texto)
        except ValueError:
            return None
    else:
        return None

    if resultado.tzinfo is None:
        resultado = resultado.replace(tzinfo=referencia.tzinfo)
    else:
        resultado = resultado.astimezone(referencia.tzinfo)

    return resultado
