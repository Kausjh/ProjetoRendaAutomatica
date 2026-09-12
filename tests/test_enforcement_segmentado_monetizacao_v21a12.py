from __future__ import annotations

from services.enforcement_segmentado_monetizacao import (
    avaliar_enforcement_segmentado,
    classificar_origem_monetizacao,
)


def _recomendacao(
    *,
    escopo: str,
    alvo: str,
    acao: str,
):
    rid = f"shadow:teste:{escopo}:" f"{alvo}:{acao}"

    return rid, {
        "schema_version": 1,
        "modo": "shadow",
        "disponivel": True,
        "autoridade_operacional": False,
        "executa_automaticamente": False,
        "recomendacoes": [
            {
                "id": rid,
                "modo": "shadow",
                "acao_sugerida": acao,
                "escopo": escopo,
                "alvo": alvo,
                "severidade": "critica",
                "executavel": False,
                "executada": False,
                "requer_confirmacao_humana": True,
                "autoridade_operacional": False,
            }
        ],
    }


def test_taxonomia_origem_reutiliza_observador():
    assert classificar_origem_monetizacao("https://www.mercadolivre.com.br/p/1") == "mercado_livre"
    assert classificar_origem_monetizacao("https://tidd.ly/abc") == "awin"
    assert classificar_origem_monetizacao("https://example.com/x") == "outro"


def test_origem_critica_pode_ser_suspensa():
    rid, shadow = _recomendacao(
        escopo="origem",
        alvo="mercado_livre",
        acao="considerar_isolamento_origem",
    )

    decisao = avaliar_enforcement_segmentado(
        shadow=shadow,
        escopo="origem",
        alvo="mercado_livre",
        acao="suspender",
        confirmacao=("CONFIRMAR_SUSPENDER:" "origem:mercado_livre"),
        recomendacao_id=rid,
    )

    assert decisao["permitido"] is True
    assert decisao["automatico"] is False


def test_afiliador_critico_pode_ser_suspenso():
    rid, shadow = _recomendacao(
        escopo="afiliador",
        alvo="awin",
        acao=("considerar_suspensao_afiliador"),
    )

    decisao = avaliar_enforcement_segmentado(
        shadow=shadow,
        escopo="afiliador",
        alvo="awin",
        acao="suspender",
        confirmacao=("CONFIRMAR_SUSPENDER:" "afiliador:awin"),
        recomendacao_id=rid,
    )

    assert decisao["permitido"] is True


def test_recomendacao_stale_e_negada():
    rid, shadow = _recomendacao(
        escopo="origem",
        alvo="amazon",
        acao="considerar_isolamento_origem",
    )

    decisao = avaliar_enforcement_segmentado(
        shadow=shadow,
        escopo="origem",
        alvo="amazon",
        acao="suspender",
        confirmacao=("CONFIRMAR_SUSPENDER:" "origem:amazon"),
        recomendacao_id=rid + ":stale",
    )

    assert decisao["permitido"] is False


def test_retomada_nao_depende_de_shadow():
    decisao = avaliar_enforcement_segmentado(
        shadow=None,
        escopo="origem",
        alvo="amazon",
        acao="retomar",
        confirmacao=("CONFIRMAR_RETOMAR:" "origem:amazon"),
    )

    assert decisao["permitido"] is True


def test_origem_outro_nao_pode_ser_suspensa():
    rid, shadow = _recomendacao(
        escopo="origem",
        alvo="outro",
        acao="considerar_isolamento_origem",
    )

    decisao = avaliar_enforcement_segmentado(
        shadow=shadow,
        escopo="origem",
        alvo="outro",
        acao="suspender",
        confirmacao=("CONFIRMAR_SUSPENDER:" "origem:outro"),
        recomendacao_id=rid,
    )

    assert decisao["permitido"] is False
    assert decisao["motivo"] == "origem_outro_nao_pode_ser_suspensa"


def test_afiliador_nenhum_nao_pode_ser_suspenso():
    rid, shadow = _recomendacao(
        escopo="afiliador",
        alvo="nenhum",
        acao=("considerar_suspensao_afiliador"),
    )

    decisao = avaliar_enforcement_segmentado(
        shadow=shadow,
        escopo="afiliador",
        alvo="nenhum",
        acao="suspender",
        confirmacao=("CONFIRMAR_SUSPENDER:" "afiliador:nenhum"),
        recomendacao_id=rid,
    )

    assert decisao["permitido"] is False


# 63.8738, -149.7525
