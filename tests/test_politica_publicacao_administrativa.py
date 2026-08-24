from datetime import datetime, timedelta
from types import SimpleNamespace

from services.controle.politica_publicacao_administrativa import (
    item_liberado_para_fluxo_automatico,
    requer_aprovacao_hibrida,
)


def criar_item(
    pontuacao: float = 85.0,
    segurado_ate=None,
    agendado_para=None,
    aprovado_manualmente: bool = False,
):
    return SimpleNamespace(
        pontuacao=pontuacao,
        segurado_ate=segurado_ate,
        agendado_para=agendado_para,
        aprovado_manualmente=aprovado_manualmente,
    )


def test_modos_automatico_manual_e_hibrido():
    agora = datetime.now().astimezone()
    item = criar_item(pontuacao=75.0)

    assert (
        item_liberado_para_fluxo_automatico(
            item=item,
            modo="automatico",
            agora=agora,
        )
        is True
    )

    assert (
        item_liberado_para_fluxo_automatico(
            item=item,
            modo="manual",
            agora=agora,
        )
        is False
    )

    assert requer_aprovacao_hibrida(item, "hibrido") is True
    assert (
        item_liberado_para_fluxo_automatico(
            item=item,
            modo="hibrido",
            agora=agora,
        )
        is False
    )

    item.aprovado_manualmente = True

    assert requer_aprovacao_hibrida(item, "hibrido") is False
    assert (
        item_liberado_para_fluxo_automatico(
            item=item,
            modo="hibrido",
            agora=agora,
        )
        is True
    )


def test_agendamento_e_retencao_saem_do_fluxo_automatico():
    agora = datetime.now().astimezone()

    segurado = criar_item(
        segurado_ate=agora + timedelta(minutes=10),
    )
    agendado = criar_item(
        agendado_para=agora + timedelta(minutes=20),
    )

    assert (
        item_liberado_para_fluxo_automatico(
            item=segurado,
            modo="automatico",
            agora=agora,
        )
        is False
    )

    assert (
        item_liberado_para_fluxo_automatico(
            item=agendado,
            modo="automatico",
            agora=agora,
        )
        is False
    )
