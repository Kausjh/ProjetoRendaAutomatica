from __future__ import annotations

from typing import Any

SCHEMA_VERSION_ALERTAS_MONETIZACAO = 1

STATUS_DADOS_INSUFICIENTES = "dados_insuficientes"
STATUS_SAUDAVEL = "saudavel"
STATUS_DEGRADADO = "degradado"
STATUS_CRITICO = "critico"

SEVERIDADE_AVISO = "aviso"
SEVERIDADE_CRITICA = "critica"

CODIGOS_METRICA = {
    "taxa_bloqueio_degradada": ("Taxa de bloqueio acima do limite de atencao."),
    "taxa_bloqueio_critica": ("Taxa de bloqueio em nivel critico."),
    "taxa_retry_degradada": ("Taxa de retry acima do limite de atencao."),
    "taxa_retry_critica": ("Taxa de retry em nivel critico."),
}


def _severidade(
    status: str,
) -> str | None:
    if status == STATUS_CRITICO:
        return SEVERIDADE_CRITICA

    if status == STATUS_DEGRADADO:
        return SEVERIDADE_AVISO

    return None


def _mensagem_metrica(
    codigo: str,
    *,
    escopo: str,
    alvo: str,
) -> str:
    base = CODIGOS_METRICA.get(
        codigo,
        "Sinal de monetizacao requer revisao.",
    )

    if escopo == "global":
        return f"Monetizacao global: {base}"

    return f"Monetizacao em {escopo} " f"'{alvo}': {base}"


def _orientacao(
    codigo: str,
) -> str:
    if codigo.startswith("taxa_bloqueio_"):
        return (
            "Revisar transformacao e confirmacao "
            "dos links afiliados antes de qualquer "
            "mudanca operacional."
        )

    if codigo.startswith("taxa_retry_"):
        return (
            "Revisar disponibilidade e estabilidade "
            "da afiliacao antes de qualquer mudanca "
            "operacional."
        )

    if codigo == "dados_invalidos":
        return "Revisar a integridade do snapshot de " "saude antes de confiar na classificacao."

    return "Revisar os dados de monetizacao antes de " "qualquer mudanca operacional."


def _criar_alerta(
    *,
    escopo: str,
    alvo: str,
    status: str,
    codigo: str,
) -> dict[str, str] | None:
    severidade = _severidade(
        status,
    )

    if severidade is None:
        return None

    return {
        "id": (f"monetizacao:{escopo}:" f"{alvo}:{codigo}"),
        "severidade": severidade,
        "status": status,
        "escopo": escopo,
        "alvo": alvo,
        "codigo": codigo,
        "mensagem": _mensagem_metrica(
            codigo,
            escopo=escopo,
            alvo=alvo,
        ),
        "orientacao": _orientacao(codigo),
    }


def _alertas_de_avaliacao(
    avaliacao: dict[str, Any],
    *,
    escopo: str,
    alvo: str,
) -> list[dict[str, str]]:
    status = avaliacao.get("status")

    if status not in {
        STATUS_DEGRADADO,
        STATUS_CRITICO,
    }:
        return []

    if avaliacao.get("dados_validos") is not True:
        return []

    if avaliacao.get("amostra_suficiente") is not True:
        return []

    motivos = avaliacao.get("motivos")

    if not isinstance(
        motivos,
        list,
    ):
        return []

    alertas: list[dict[str, str]] = []

    for motivo in sorted(
        {
            str(item)
            for item in motivos
            if isinstance(
                item,
                str,
            )
        }
    ):
        if motivo not in CODIGOS_METRICA:
            continue

        alerta = _criar_alerta(
            escopo=escopo,
            alvo=alvo,
            status=str(status),
            codigo=motivo,
        )

        if alerta is not None:
            alertas.append(alerta)

    return alertas


def _alertas_segmentos(
    segmentos: Any,
    *,
    escopo: str,
) -> list[dict[str, str]]:
    if not isinstance(
        segmentos,
        dict,
    ):
        return []

    alertas: list[dict[str, str]] = []

    for nome, avaliacao in sorted(
        segmentos.items(),
        key=lambda item: str(item[0]),
    ):
        if not isinstance(
            avaliacao,
            dict,
        ):
            continue

        alertas.extend(
            _alertas_de_avaliacao(
                avaliacao,
                escopo=escopo,
                alvo=str(nome),
            )
        )

    return alertas


def _alerta_dados_invalidos(
    saude: dict[str, Any],
) -> dict[str, str] | None:
    if saude.get("dados_validos") is not False:
        return None

    return {
        "id": ("monetizacao:global:" "geral:dados_invalidos"),
        "severidade": SEVERIDADE_AVISO,
        "status": STATUS_DADOS_INSUFICIENTES,
        "escopo": "global",
        "alvo": "geral",
        "codigo": "dados_invalidos",
        "mensagem": (
            "Monetizacao global: os dados de saude "
            "nao sao validos o suficiente para uma "
            "classificacao confiavel."
        ),
        "orientacao": _orientacao("dados_invalidos"),
    }


def gerar_alertas_monetizacao(
    saude: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        saude,
        dict,
    ):
        return {
            "schema_version": SCHEMA_VERSION_ALERTAS_MONETIZACAO,
            "disponivel": False,
            "status_saude": None,
            "alertas_total": 0,
            "criticos_total": 0,
            "avisos_total": 0,
            "alertas": [],
        }

    if saude.get("schema_version") != 1:
        return {
            "schema_version": SCHEMA_VERSION_ALERTAS_MONETIZACAO,
            "disponivel": False,
            "status_saude": saude.get("status"),
            "alertas_total": 0,
            "criticos_total": 0,
            "avisos_total": 0,
            "alertas": [],
        }

    alertas: list[dict[str, str]] = []

    alerta_dados = _alerta_dados_invalidos(saude)

    if alerta_dados is not None:
        alertas.append(alerta_dados)

    motivos_globais = [
        str(motivo)
        for motivo in saude.get(
            "motivos",
            [],
        )
        if (
            isinstance(
                motivo,
                str,
            )
            and not motivo.startswith("origem:")
            and not motivo.startswith("afiliador:")
        )
    ]

    avaliacao_global = {
        "status": saude.get("status"),
        "dados_validos": saude.get("dados_validos"),
        "amostra_suficiente": saude.get("amostra_suficiente"),
        "motivos": motivos_globais,
    }

    alertas.extend(
        _alertas_de_avaliacao(
            avaliacao_global,
            escopo="global",
            alvo="geral",
        )
    )

    alertas.extend(
        _alertas_segmentos(
            saude.get("por_origem"),
            escopo="origem",
        )
    )

    alertas.extend(
        _alertas_segmentos(
            saude.get("por_afiliador"),
            escopo="afiliador",
        )
    )

    alertas = sorted(
        {alerta["id"]: alerta for alerta in alertas}.values(),
        key=lambda alerta: (
            0 if alerta["severidade"] == SEVERIDADE_CRITICA else 1,
            alerta["id"],
        ),
    )

    criticos_total = sum(1 for alerta in alertas if alerta["severidade"] == SEVERIDADE_CRITICA)

    avisos_total = sum(1 for alerta in alertas if alerta["severidade"] == SEVERIDADE_AVISO)

    return {
        "schema_version": SCHEMA_VERSION_ALERTAS_MONETIZACAO,
        "disponivel": True,
        "status_saude": saude.get("status"),
        "alertas_total": len(alertas),
        "criticos_total": criticos_total,
        "avisos_total": avisos_total,
        "alertas": alertas,
    }
