from __future__ import annotations

from typing import Any

SCHEMA_VERSION_RECONCILIACAO_ENFORCEMENT = 1

CONFIRMACAO_RECONCILIAR_PREFIXO = "CONFIRMAR_RECONCILIACAO_ENFORCEMENT:"
CONFIRMACAO_CONSUMIR_PREFIXO = "CONFIRMAR_CONSUMO_SEM_REPLAY:"
RECOMENDACAO_PAUSA_PUBLICADOR = "considerar_pausa_publicador"


def confirmacao_reconciliacao_esperada(
    recomendacao_id: str,
) -> str:
    return CONFIRMACAO_RECONCILIAR_PREFIXO + str(recomendacao_id).strip()


def confirmacao_consumo_esperada(
    recomendacao_id: str,
) -> str:
    return CONFIRMACAO_CONSUMIR_PREFIXO + str(recomendacao_id).strip()


def classificar_reserva_enforcement(
    *,
    reserva: dict[str, Any],
    segmento: dict[str, Any] | None,
    publicador_pausado: bool,
    auditoria_pausa_sucesso: bool,
) -> dict[str, Any]:
    recomendacao_id = str(reserva.get("recomendacao_id", "")).strip()
    status = str(reserva.get("status", "")).strip().casefold()

    base = {
        "schema_version": SCHEMA_VERSION_RECONCILIACAO_ENFORCEMENT,
        "recomendacao_id": recomendacao_id or None,
        "status": status,
        "automatico": False,
        "ttl_automatico": False,
        "libera_replay": False,
        "evidencia_forte": False,
        "pode_concluir": False,
        "tipo_evidencia": None,
        "motivo": "revisao_manual",
    }

    if not recomendacao_id or status != "reservado":
        return {
            **base,
            "motivo": "reserva_nao_reconciliavel",
        }

    if isinstance(segmento, dict):
        mesmo_id = str(segmento.get("recomendacao_id", "")).strip() == recomendacao_id

        if mesmo_id and segmento.get("ativo") is True:
            return {
                **base,
                "evidencia_forte": True,
                "pode_concluir": True,
                "tipo_evidencia": "segmento_ativo_mesma_recomendacao",
                "motivo": "efeito_segmentado_persistido",
            }

    pausa_global = RECOMENDACAO_PAUSA_PUBLICADOR in recomendacao_id

    if pausa_global and auditoria_pausa_sucesso:
        return {
            **base,
            "evidencia_forte": True,
            "pode_concluir": True,
            "tipo_evidencia": "auditoria_pausa_publicador_apos_reserva",
            "motivo": "efeito_global_auditado",
        }

    if pausa_global and publicador_pausado:
        return {
            **base,
            "evidencia_forte": True,
            "pode_concluir": True,
            "tipo_evidencia": "estado_publicador_pausado",
            "motivo": "estado_global_desejado_ativo",
        }

    return base
