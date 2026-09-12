from __future__ import annotations

from typing import Any

SCHEMA_VERSION_RECOMENDACAO_SHADOW_MONETIZACAO = 1
MODO_SHADOW = "shadow"

ACAO_MANTER_OPERACAO = "manter_operacao"
ACAO_REVISAR_DADOS = "revisar_dados"
ACAO_REVISAR_MONETIZACAO_GLOBAL = "revisar_monetizacao_global"
ACAO_CONSIDERAR_PAUSA_PUBLICADOR = "considerar_pausa_publicador"
ACAO_REVISAR_ORIGEM = "revisar_origem"
ACAO_CONSIDERAR_ISOLAMENTO_ORIGEM = "considerar_isolamento_origem"
ACAO_REVISAR_AFILIADOR = "revisar_afiliador"
ACAO_CONSIDERAR_SUSPENSAO_AFILIADOR = "considerar_suspensao_afiliador"

SEVERIDADE_AVISO = "aviso"
SEVERIDADE_CRITICA = "critica"


def _acao_para_alerta(
    alerta: dict[str, Any],
) -> str | None:
    escopo = alerta.get("escopo")
    severidade = alerta.get("severidade")
    codigo = alerta.get("codigo")

    if codigo == "dados_invalidos":
        return ACAO_REVISAR_DADOS

    if escopo == "global":
        if severidade == SEVERIDADE_CRITICA:
            return ACAO_CONSIDERAR_PAUSA_PUBLICADOR

        if severidade == SEVERIDADE_AVISO:
            return ACAO_REVISAR_MONETIZACAO_GLOBAL

    if escopo == "origem":
        if severidade == SEVERIDADE_CRITICA:
            return ACAO_CONSIDERAR_ISOLAMENTO_ORIGEM

        if severidade == SEVERIDADE_AVISO:
            return ACAO_REVISAR_ORIGEM

    if escopo == "afiliador":
        if severidade == SEVERIDADE_CRITICA:
            return ACAO_CONSIDERAR_SUSPENSAO_AFILIADOR

        if severidade == SEVERIDADE_AVISO:
            return ACAO_REVISAR_AFILIADOR

    return None


def _prioridade(
    recomendacao: dict[str, Any],
) -> tuple[int, int, str]:
    severidade = recomendacao["severidade"]
    escopo = recomendacao["escopo"]

    prioridade_severidade = 0 if severidade == SEVERIDADE_CRITICA else 1

    prioridade_escopo = {
        "global": 0,
        "origem": 1,
        "afiliador": 2,
    }.get(
        str(escopo),
        9,
    )

    return (
        prioridade_severidade,
        prioridade_escopo,
        str(recomendacao["id"]),
    )


def _criar_recomendacao(
    alerta: dict[str, Any],
) -> dict[str, Any] | None:
    acao = _acao_para_alerta(alerta)

    if acao is None:
        return None

    alerta_id = alerta.get("id")
    escopo = alerta.get("escopo")
    alvo = alerta.get("alvo")
    severidade = alerta.get("severidade")
    codigo = alerta.get("codigo")

    if not all(
        isinstance(valor, str) and bool(valor.strip())
        for valor in (
            alerta_id,
            escopo,
            alvo,
            severidade,
            codigo,
        )
    ):
        return None

    return {
        "id": (f"shadow:{alerta_id}:" f"{acao}"),
        "modo": MODO_SHADOW,
        "acao_sugerida": acao,
        "escopo": escopo,
        "alvo": alvo,
        "severidade": severidade,
        "codigo_alerta": codigo,
        "alerta_id": alerta_id,
        "executavel": False,
        "executada": False,
        "requer_confirmacao_humana": True,
        "autoridade_operacional": False,
    }


def gerar_recomendacao_shadow_monetizacao(
    alertas: dict[str, Any],
) -> dict[str, Any]:
    base_indisponivel = {
        "schema_version": SCHEMA_VERSION_RECOMENDACAO_SHADOW_MONETIZACAO,
        "modo": MODO_SHADOW,
        "disponivel": False,
        "autoridade_operacional": False,
        "executa_automaticamente": False,
        "acao_sugerida_principal": None,
        "recomendacoes_total": 0,
        "recomendacoes": [],
    }

    if not isinstance(
        alertas,
        dict,
    ):
        return base_indisponivel

    if alertas.get("schema_version") != 1:
        return base_indisponivel

    if alertas.get("disponivel") is not True:
        return base_indisponivel

    itens = alertas.get("alertas")

    if not isinstance(
        itens,
        list,
    ):
        return base_indisponivel

    recomendacoes: list[dict[str, Any]] = []

    for alerta in itens:
        if not isinstance(
            alerta,
            dict,
        ):
            continue

        recomendacao = _criar_recomendacao(alerta)

        if recomendacao is not None:
            recomendacoes.append(recomendacao)

    recomendacoes = sorted(
        {recomendacao["id"]: recomendacao for recomendacao in recomendacoes}.values(),
        key=_prioridade,
    )

    if recomendacoes:
        acao_principal = recomendacoes[0]["acao_sugerida"]
    else:
        acao_principal = ACAO_MANTER_OPERACAO

    return {
        "schema_version": SCHEMA_VERSION_RECOMENDACAO_SHADOW_MONETIZACAO,
        "modo": MODO_SHADOW,
        "disponivel": True,
        "autoridade_operacional": False,
        "executa_automaticamente": False,
        "acao_sugerida_principal": acao_principal,
        "recomendacoes_total": len(recomendacoes),
        "recomendacoes": recomendacoes,
    }
