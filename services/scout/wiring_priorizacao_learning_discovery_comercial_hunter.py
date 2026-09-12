from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from models.alvo_discovery_comercial_hunter import (
    ResultadoAlvosDiscoveryComercialHunter,
)
from services.scout.priorizacao_learning_discovery_comercial_hunter import (
    ResultadoPriorizacaoLearningDiscoveryComercialHunter,
    aplicar_priorizacao_learning_discovery_comercial_hunter,
)

SCHEMA_VERSION = 1
COOLDOWN_HORAS_PADRAO = 6.0


def aplicar_priorizacao_learning_com_historico(
    *,
    resultado: ResultadoAlvosDiscoveryComercialHunter,
    relatorios_execucao: Iterable[Mapping[str, Any]] = (),
    agora: datetime | str | None = None,
    cooldown_horas: float = COOLDOWN_HORAS_PADRAO,
) -> ResultadoPriorizacaoLearningDiscoveryComercialHunter:
    """Aplica a politica pura usando somente learning persistido.

    Fail-open:
    - sem score valido: mantem a ordem base;
    - sem score elegivel: mantem a ordem base;
    - fingerprint novo dentro do cooldown: mantem a ordem base;
    - mesmo fingerprint: permite decisao estavel.
    """

    referencia = _normalizar_datetime(agora)

    cooldown = _validar_cooldown(cooldown_horas)

    relatorios = [
        item
        for item in relatorios_execucao
        if isinstance(
            item,
            Mapping,
        )
    ]

    score_learning, data_score = _ultimo_score_valido(relatorios)

    candidato = aplicar_priorizacao_learning_discovery_comercial_hunter(
        resultado=resultado,
        score_learning=score_learning,
    )

    observabilidade = dict(candidato.observabilidade)

    observabilidade.update(
        {
            "schema_version_runtime": SCHEMA_VERSION,
            "cooldown_horas": cooldown,
            "cooldown_ativo": False,
            "histerese_ativa": True,
            "score_origem_data_hora": data_score,
            "fingerprint_score": _fingerprint_score(observabilidade),
            "fingerprint_anterior": None,
            "mudanca_fingerprint": False,
            "ultima_influencia_data_hora": None,
            "idade_ultima_influencia_horas": None,
        }
    )

    if score_learning is None:
        observabilidade["status_runtime"] = "fallback_sem_score_persistido"

        return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
            resultado=resultado,
            observabilidade=observabilidade,
        )

    if not candidato.observabilidade.get("ordem_alterada"):
        observabilidade["status_runtime"] = "sem_reordenacao"

        return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
            resultado=candidato.resultado,
            observabilidade=observabilidade,
        )

    anterior = _ultima_priorizacao_aplicada(relatorios)

    if anterior is None:
        observabilidade["status_runtime"] = "aplicado_sem_historico_anterior"

        return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
            resultado=candidato.resultado,
            observabilidade=observabilidade,
        )

    fingerprint_anterior = anterior.get("fingerprint_score")

    data_anterior = anterior.get("data_hora")

    observabilidade["fingerprint_anterior"] = fingerprint_anterior

    observabilidade["ultima_influencia_data_hora"] = data_anterior

    fingerprint_atual = observabilidade["fingerprint_score"]

    mudou_fingerprint = fingerprint_anterior != fingerprint_atual

    observabilidade["mudanca_fingerprint"] = mudou_fingerprint

    instante_anterior = _parse_datetime(data_anterior)

    if instante_anterior is None:
        observabilidade["status_runtime"] = "aplicado_historico_sem_data_valida"

        return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
            resultado=candidato.resultado,
            observabilidade=observabilidade,
        )

    idade_horas = max(
        0.0,
        (referencia - instante_anterior).total_seconds() / 3600.0,
    )

    observabilidade["idade_ultima_influencia_horas"] = round(
        idade_horas,
        4,
    )

    if mudou_fingerprint and idade_horas < cooldown:
        observabilidade["cooldown_ativo"] = True

        observabilidade["influencia_priorizacao"] = False

        observabilidade["ordem_alterada"] = False

        observabilidade["movimentos_total"] = 0

        observabilidade["movimentos_exploracao"] = 0

        observabilidade["status"] = "cooldown_histerese_ativo"

        observabilidade["status_runtime"] = "cooldown_histerese_ativo"

        return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
            resultado=resultado,
            observabilidade=observabilidade,
        )

    if mudou_fingerprint:
        observabilidade["status_runtime"] = "aplicado_apos_cooldown"
    else:
        observabilidade["status_runtime"] = "aplicado_fingerprint_estavel"

    return ResultadoPriorizacaoLearningDiscoveryComercialHunter(
        resultado=candidato.resultado,
        observabilidade=observabilidade,
    )


def _ultimo_score_valido(
    relatorios: list[Mapping[str, Any]],
) -> tuple[Mapping[str, Any] | None, str | None]:
    for relatorio in reversed(relatorios):
        learning = relatorio.get("commercial_discovery_learning")

        if not isinstance(
            learning,
            Mapping,
        ):
            continue

        score = learning.get("score")

        if not _score_tem_contrato_valido(score):
            continue

        return (
            score,
            _texto_data_hora(relatorio.get("data_hora")),
        )

    return (
        None,
        None,
    )


def _score_tem_contrato_valido(
    score: object,
) -> bool:
    return (
        isinstance(
            score,
            Mapping,
        )
        and score.get("granularidade") == "fonte_hunter"
        and score.get("somente_dataset_maduro") is True
        and score.get("score_observacional") is True
    )


def _ultima_priorizacao_aplicada(
    relatorios: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    for relatorio in reversed(relatorios):
        discovery = relatorio.get("discovery_comercial_hunter")

        if not isinstance(
            discovery,
            Mapping,
        ):
            continue

        priorizacao = discovery.get("priorizacao_learning")

        if not isinstance(
            priorizacao,
            Mapping,
        ):
            continue

        if priorizacao.get("influencia_priorizacao") is not True:
            continue

        fingerprint = priorizacao.get("fingerprint_score")

        if not isinstance(
            fingerprint,
            list,
        ):
            continue

        return {
            "fingerprint_score": list(fingerprint),
            "data_hora": _texto_data_hora(relatorio.get("data_hora")),
        }

    return None


def _fingerprint_score(
    observabilidade: Mapping[str, Any],
) -> list[str]:
    fontes = observabilidade.get("fontes_score")

    if not isinstance(
        fontes,
        list,
    ):
        return []

    validas = [
        item
        for item in fontes
        if isinstance(
            item,
            Mapping,
        )
        and str(item.get("fonte_hunter") or "").strip()
    ]

    validas.sort(
        key=lambda item: (
            -float(item.get("bonus_sinais") or 0.0),
            -float(item.get("score_learning") or 0.0),
            str(item.get("fonte_hunter")).casefold(),
        )
    )

    return [str(item["fonte_hunter"]) for item in validas]


def _validar_cooldown(
    valor: float,
) -> float:
    try:
        cooldown = float(valor)
    except (
        TypeError,
        ValueError,
    ) as erro:
        raise ValueError("cooldown_horas deve ser numerico") from erro

    if cooldown <= 0:
        raise ValueError("cooldown_horas deve ser positivo")

    return cooldown


def _normalizar_datetime(
    valor: datetime | str | None,
) -> datetime:
    if valor is None:
        valor = datetime.now(UTC)

    instante = _parse_datetime(valor)

    if instante is None:
        raise ValueError("agora possui data invalida")

    return instante


def _parse_datetime(
    valor: object,
) -> datetime | None:
    if isinstance(
        valor,
        datetime,
    ):
        instante = valor
    else:
        texto = str(valor or "").strip()

        if not texto:
            return None

        try:
            instante = datetime.fromisoformat(texto)
        except ValueError:
            return None

    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    else:
        instante = instante.astimezone(UTC)

    return instante


def _texto_data_hora(
    valor: object,
) -> str | None:
    texto = str(valor or "").strip()

    return texto or None
