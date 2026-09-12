from __future__ import annotations

from typing import Any

SCHEMA_VERSION_ENFORCEMENT_MONETIZACAO = 1

ACAO_PAUSAR = "pausar"
ACAO_RETOMAR = "retomar"

CONFIRMACAO_PAUSAR = "CONFIRMAR_PAUSA_PUBLICADOR"
CONFIRMACAO_RETOMAR = "CONFIRMAR_RETOMADA_PUBLICADOR"

RECOMENDACAO_PAUSA = "considerar_pausa_publicador"


def _decisao(
    *,
    permitido: bool,
    acao: str,
    motivo: str,
    recomendacao_id: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION_ENFORCEMENT_MONETIZACAO,
        "permitido": permitido,
        "manual": True,
        "automatico": False,
        "requer_autenticacao_admin": True,
        "requer_confirmacao_explicita": True,
        "acao": acao,
        "componente": "publicador",
        "motivo": motivo,
        "recomendacao_id": recomendacao_id,
    }


def _shadow_valido(
    shadow: dict[str, Any] | None,
) -> bool:
    if not isinstance(
        shadow,
        dict,
    ):
        return False

    return (
        shadow.get("schema_version") == 1
        and shadow.get("modo") == "shadow"
        and shadow.get("disponivel") is True
        and shadow.get("autoridade_operacional") is False
        and shadow.get("executa_automaticamente") is False
        and isinstance(
            shadow.get("recomendacoes"),
            list,
        )
    )


def _recomendacao_pausa_atual(
    shadow: dict[str, Any],
    recomendacao_id: str,
) -> dict[str, Any] | None:
    recomendacoes = shadow.get(
        "recomendacoes",
        [],
    )

    for item in recomendacoes:
        if not isinstance(
            item,
            dict,
        ):
            continue

        if item.get("id") != recomendacao_id:
            continue

        if item.get("acao_sugerida") != RECOMENDACAO_PAUSA:
            return None

        if item.get("escopo") != "global":
            return None

        if item.get("severidade") != "critica":
            return None

        if item.get("executavel") is not False:
            return None

        if item.get("executada") is not False:
            return None

        if item.get("requer_confirmacao_humana") is not True:
            return None

        if item.get("autoridade_operacional") is not False:
            return None

        return item

    return None


def avaliar_enforcement_monetizacao(
    *,
    shadow: dict[str, Any] | None,
    acao: str,
    confirmacao: str | None,
    recomendacao_id: str | None = None,
) -> dict[str, Any]:
    acao_normalizada = str(acao).strip().lower()

    confirmacao_normalizada = str(confirmacao).strip() if confirmacao is not None else ""

    recomendacao_normalizada = str(recomendacao_id).strip() if recomendacao_id is not None else ""

    if acao_normalizada == ACAO_RETOMAR:
        if confirmacao_normalizada != CONFIRMACAO_RETOMAR:
            return _decisao(
                permitido=False,
                acao=ACAO_RETOMAR,
                motivo=("confirmacao_retomada_invalida"),
                recomendacao_id=None,
            )

        return _decisao(
            permitido=True,
            acao=ACAO_RETOMAR,
            motivo="retomada_manual_confirmada",
            recomendacao_id=None,
        )

    if acao_normalizada != ACAO_PAUSAR:
        return _decisao(
            permitido=False,
            acao=acao_normalizada,
            motivo="acao_nao_suportada",
            recomendacao_id=(recomendacao_normalizada or None),
        )

    if confirmacao_normalizada != CONFIRMACAO_PAUSAR:
        return _decisao(
            permitido=False,
            acao=ACAO_PAUSAR,
            motivo="confirmacao_pausa_invalida",
            recomendacao_id=(recomendacao_normalizada or None),
        )

    if not recomendacao_normalizada:
        return _decisao(
            permitido=False,
            acao=ACAO_PAUSAR,
            motivo="recomendacao_id_obrigatoria",
            recomendacao_id=None,
        )

    if not _shadow_valido(shadow):
        return _decisao(
            permitido=False,
            acao=ACAO_PAUSAR,
            motivo="shadow_atual_indisponivel",
            recomendacao_id=(recomendacao_normalizada),
        )

    recomendacao = _recomendacao_pausa_atual(
        shadow,
        recomendacao_normalizada,
    )

    if recomendacao is None:
        return _decisao(
            permitido=False,
            acao=ACAO_PAUSAR,
            motivo=("recomendacao_critica_global_nao_confere"),
            recomendacao_id=(recomendacao_normalizada),
        )

    return _decisao(
        permitido=True,
        acao=ACAO_PAUSAR,
        motivo="pausa_manual_confirmada",
        recomendacao_id=(recomendacao_normalizada),
    )
