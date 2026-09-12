from __future__ import annotations

from services.politica_enforcement_monetizacao import (
    CONFIRMACAO_PAUSAR,
    CONFIRMACAO_RETOMAR,
    avaliar_enforcement_monetizacao,
)

RECOMENDACAO_ID = (
    "shadow:monetizacao:global:geral:" "taxa_bloqueio_critica:" "considerar_pausa_publicador"
)


def _shadow_critico():
    return {
        "schema_version": 1,
        "modo": "shadow",
        "disponivel": True,
        "autoridade_operacional": False,
        "executa_automaticamente": False,
        "acao_sugerida_principal": ("considerar_pausa_publicador"),
        "recomendacoes_total": 1,
        "recomendacoes": [
            {
                "id": RECOMENDACAO_ID,
                "modo": "shadow",
                "acao_sugerida": ("considerar_pausa_publicador"),
                "escopo": "global",
                "alvo": "geral",
                "severidade": "critica",
                "codigo_alerta": ("taxa_bloqueio_critica"),
                "alerta_id": ("monetizacao:global:geral:" "taxa_bloqueio_critica"),
                "executavel": False,
                "executada": False,
                "requer_confirmacao_humana": True,
                "autoridade_operacional": False,
            }
        ],
    }


def test_pausa_exige_confirmacao_exata():
    decisao = avaliar_enforcement_monetizacao(
        shadow=_shadow_critico(),
        acao="pausar",
        confirmacao="sim",
        recomendacao_id=RECOMENDACAO_ID,
    )

    assert decisao["permitido"] is False
    assert decisao["motivo"] == "confirmacao_pausa_invalida"


def test_pausa_exige_recomendacao_id():
    decisao = avaliar_enforcement_monetizacao(
        shadow=_shadow_critico(),
        acao="pausar",
        confirmacao=CONFIRMACAO_PAUSAR,
        recomendacao_id=None,
    )

    assert decisao["permitido"] is False
    assert decisao["motivo"] == "recomendacao_id_obrigatoria"


def test_pausa_rejeita_recomendacao_antiga():
    decisao = avaliar_enforcement_monetizacao(
        shadow=_shadow_critico(),
        acao="pausar",
        confirmacao=CONFIRMACAO_PAUSAR,
        recomendacao_id="shadow:antiga",
    )

    assert decisao["permitido"] is False
    assert decisao["motivo"] == ("recomendacao_critica_global_" "nao_confere")


def test_pausa_rejeita_shadow_indisponivel():
    decisao = avaliar_enforcement_monetizacao(
        shadow=None,
        acao="pausar",
        confirmacao=CONFIRMACAO_PAUSAR,
        recomendacao_id=RECOMENDACAO_ID,
    )

    assert decisao["permitido"] is False
    assert decisao["motivo"] == "shadow_atual_indisponivel"


def test_pausa_atual_critica_pode_ser_confirmada():
    decisao = avaliar_enforcement_monetizacao(
        shadow=_shadow_critico(),
        acao="pausar",
        confirmacao=CONFIRMACAO_PAUSAR,
        recomendacao_id=RECOMENDACAO_ID,
    )

    assert decisao["permitido"] is True
    assert decisao["manual"] is True
    assert decisao["automatico"] is False
    assert decisao["requer_autenticacao_admin"] is True
    assert decisao["requer_confirmacao_explicita"] is True


def test_retomada_exige_confirmacao_exata():
    decisao = avaliar_enforcement_monetizacao(
        shadow=None,
        acao="retomar",
        confirmacao="sim",
    )

    assert decisao["permitido"] is False
    assert decisao["motivo"] == "confirmacao_retomada_invalida"


def test_retomada_e_reversao_manual_independente_do_shadow():
    decisao = avaliar_enforcement_monetizacao(
        shadow=None,
        acao="retomar",
        confirmacao=CONFIRMACAO_RETOMAR,
    )

    assert decisao["permitido"] is True
    assert decisao["acao"] == "retomar"
    assert decisao["manual"] is True
    assert decisao["automatico"] is False


def test_acao_desconhecida_e_negada():
    decisao = avaliar_enforcement_monetizacao(
        shadow=_shadow_critico(),
        acao="bloquear_afiliador",
        confirmacao="qualquer",
    )

    assert decisao["permitido"] is False
    assert decisao["motivo"] == "acao_nao_suportada"


# 63.8738, -149.7525
