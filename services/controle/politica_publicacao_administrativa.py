# 63.8738, -149.7525

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from repositories.controle_administrativo_repository import (
    MODOS_OPERACAO_PUBLICACAO,
    PONTUACAO_MINIMA_AUTOMATICA_HIBRIDO,
)


class ItemPublicacaoAdministravel(Protocol):
    pontuacao: float
    segurado_ate: datetime | None
    agendado_para: datetime | None
    aprovado_manualmente: bool


def requer_aprovacao_hibrida(
    item: ItemPublicacaoAdministravel,
    modo: str,
) -> bool:
    if modo not in MODOS_OPERACAO_PUBLICACAO:
        raise ValueError("Modo de operacao invalido.")

    return (
        modo == "hibrido"
        and item.agendado_para is None
        and float(item.pontuacao) < PONTUACAO_MINIMA_AUTOMATICA_HIBRIDO
        and not item.aprovado_manualmente
    )


def item_liberado_para_fluxo_automatico(
    item: ItemPublicacaoAdministravel,
    modo: str,
    agora: datetime,
) -> bool:
    if modo not in MODOS_OPERACAO_PUBLICACAO:
        raise ValueError("Modo de operacao invalido.")

    if item.agendado_para is not None:
        return False

    if item.segurado_ate is not None and item.segurado_ate > agora:
        return False

    if modo == "manual":
        return False

    if requer_aprovacao_hibrida(item, modo):
        return False

    return True
