from __future__ import annotations

from copy import deepcopy

from services.recomendador_shadow_monetizacao import (
    ACAO_CONSIDERAR_ISOLAMENTO_ORIGEM,
    ACAO_CONSIDERAR_PAUSA_PUBLICADOR,
    ACAO_CONSIDERAR_SUSPENSAO_AFILIADOR,
    ACAO_MANTER_OPERACAO,
    ACAO_REVISAR_AFILIADOR,
    ACAO_REVISAR_DADOS,
    ACAO_REVISAR_MONETIZACAO_GLOBAL,
    ACAO_REVISAR_ORIGEM,
    gerar_recomendacao_shadow_monetizacao,
)


def _alerta(
    *,
    id_: str,
    severidade: str,
    escopo: str,
    alvo: str,
    codigo: str,
):
    return {
        "id": id_,
        "severidade": severidade,
        "status": ("critico" if severidade == "critica" else "degradado"),
        "escopo": escopo,
        "alvo": alvo,
        "codigo": codigo,
        "mensagem": "teste",
        "orientacao": "revisar",
    }


def _alertas(
    itens=None,
):
    itens_validos = itens if itens is not None else []

    return {
        "schema_version": 1,
        "disponivel": True,
        "status_saude": ("saudavel" if not itens_validos else "critico"),
        "alertas_total": len(itens_validos),
        "criticos_total": sum(1 for item in itens_validos if item["severidade"] == "critica"),
        "avisos_total": sum(1 for item in itens_validos if item["severidade"] == "aviso"),
        "alertas": itens_validos,
    }


def test_sem_alertas_recomenda_manter_operacao():
    resultado = gerar_recomendacao_shadow_monetizacao(_alertas())

    assert resultado["disponivel"] is True
    assert resultado["modo"] == "shadow"
    assert resultado["acao_sugerida_principal"] == ACAO_MANTER_OPERACAO
    assert resultado["recomendacoes_total"] == 0
    assert resultado["recomendacoes"] == []
    assert resultado["autoridade_operacional"] is False
    assert resultado["executa_automaticamente"] is False


def test_dados_invalidos_recomenda_revisao():
    resultado = gerar_recomendacao_shadow_monetizacao(
        _alertas(
            [
                _alerta(
                    id_=("monetizacao:global:" "geral:dados_invalidos"),
                    severidade="aviso",
                    escopo="global",
                    alvo="geral",
                    codigo="dados_invalidos",
                )
            ]
        )
    )

    assert resultado["acao_sugerida_principal"] == ACAO_REVISAR_DADOS


def test_aviso_global_recomenda_revisao_global():
    resultado = gerar_recomendacao_shadow_monetizacao(
        _alertas(
            [
                _alerta(
                    id_="global-aviso",
                    severidade="aviso",
                    escopo="global",
                    alvo="geral",
                    codigo=("taxa_retry_degradada"),
                )
            ]
        )
    )

    assert resultado["acao_sugerida_principal"] == ACAO_REVISAR_MONETIZACAO_GLOBAL


def test_critico_global_recomenda_pausa_em_shadow():
    resultado = gerar_recomendacao_shadow_monetizacao(
        _alertas(
            [
                _alerta(
                    id_="global-critico",
                    severidade="critica",
                    escopo="global",
                    alvo="geral",
                    codigo=("taxa_bloqueio_critica"),
                )
            ]
        )
    )

    assert resultado["acao_sugerida_principal"] == ACAO_CONSIDERAR_PAUSA_PUBLICADOR

    recomendacao = resultado["recomendacoes"][0]

    assert recomendacao["executavel"] is False
    assert recomendacao["executada"] is False
    assert recomendacao["requer_confirmacao_humana"] is True
    assert recomendacao["autoridade_operacional"] is False


def test_aviso_origem_recomenda_revisar_origem():
    resultado = gerar_recomendacao_shadow_monetizacao(
        _alertas(
            [
                _alerta(
                    id_="origem-aviso",
                    severidade="aviso",
                    escopo="origem",
                    alvo="mercadolivre",
                    codigo=("taxa_retry_degradada"),
                )
            ]
        )
    )

    assert resultado["acao_sugerida_principal"] == ACAO_REVISAR_ORIGEM


def test_critico_origem_recomenda_isolamento_shadow():
    resultado = gerar_recomendacao_shadow_monetizacao(
        _alertas(
            [
                _alerta(
                    id_="origem-critica",
                    severidade="critica",
                    escopo="origem",
                    alvo="mercadolivre",
                    codigo=("taxa_bloqueio_critica"),
                )
            ]
        )
    )

    assert resultado["acao_sugerida_principal"] == ACAO_CONSIDERAR_ISOLAMENTO_ORIGEM


def test_aviso_afiliador_recomenda_revisar_afiliador():
    resultado = gerar_recomendacao_shadow_monetizacao(
        _alertas(
            [
                _alerta(
                    id_="afiliador-aviso",
                    severidade="aviso",
                    escopo="afiliador",
                    alvo="awin",
                    codigo=("taxa_retry_degradada"),
                )
            ]
        )
    )

    assert resultado["acao_sugerida_principal"] == ACAO_REVISAR_AFILIADOR


def test_critico_afiliador_recomenda_suspensao_shadow():
    resultado = gerar_recomendacao_shadow_monetizacao(
        _alertas(
            [
                _alerta(
                    id_="afiliador-critico",
                    severidade="critica",
                    escopo="afiliador",
                    alvo="awin",
                    codigo=("taxa_retry_critica"),
                )
            ]
        )
    )

    assert resultado["acao_sugerida_principal"] == ACAO_CONSIDERAR_SUSPENSAO_AFILIADOR


def test_critico_tem_prioridade_sobre_aviso():
    resultado = gerar_recomendacao_shadow_monetizacao(
        _alertas(
            [
                _alerta(
                    id_="aviso-global",
                    severidade="aviso",
                    escopo="global",
                    alvo="geral",
                    codigo=("taxa_retry_degradada"),
                ),
                _alerta(
                    id_="critico-afiliador",
                    severidade="critica",
                    escopo="afiliador",
                    alvo="awin",
                    codigo=("taxa_retry_critica"),
                ),
            ]
        )
    )

    assert resultado["acao_sugerida_principal"] == ACAO_CONSIDERAR_SUSPENSAO_AFILIADOR


def test_critico_global_tem_prioridade_sobre_segmento_critico():
    resultado = gerar_recomendacao_shadow_monetizacao(
        _alertas(
            [
                _alerta(
                    id_="critico-afiliador",
                    severidade="critica",
                    escopo="afiliador",
                    alvo="awin",
                    codigo=("taxa_retry_critica"),
                ),
                _alerta(
                    id_="critico-global",
                    severidade="critica",
                    escopo="global",
                    alvo="geral",
                    codigo=("taxa_bloqueio_critica"),
                ),
            ]
        )
    )

    assert resultado["acao_sugerida_principal"] == ACAO_CONSIDERAR_PAUSA_PUBLICADOR


def test_recomendador_e_deterministico():
    entrada = _alertas(
        [
            _alerta(
                id_="critico-global",
                severidade="critica",
                escopo="global",
                alvo="geral",
                codigo=("taxa_bloqueio_critica"),
            )
        ]
    )

    primeiro = gerar_recomendacao_shadow_monetizacao(entrada)
    segundo = gerar_recomendacao_shadow_monetizacao(entrada)

    assert primeiro == segundo


def test_recomendador_nao_muta_alertas():
    entrada = _alertas(
        [
            _alerta(
                id_="aviso-global",
                severidade="aviso",
                escopo="global",
                alvo="geral",
                codigo=("taxa_retry_degradada"),
            )
        ]
    )

    antes = deepcopy(entrada)

    gerar_recomendacao_shadow_monetizacao(entrada)

    assert entrada == antes


def test_schema_incompativel_fica_indisponivel():
    entrada = _alertas()
    entrada["schema_version"] = 999

    resultado = gerar_recomendacao_shadow_monetizacao(entrada)

    assert resultado["disponivel"] is False
    assert resultado["acao_sugerida_principal"] is None


# 63.8738, -149.7525
