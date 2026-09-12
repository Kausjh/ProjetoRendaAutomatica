from __future__ import annotations

import ast
from pathlib import Path

import pytest

from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
    SolicitacaoInteligenciaAI,
)
from models.observabilidade_ai import (
    ESTADO_CIRCUITO_FECHADO,
)
from services.controle_operacional_ai import (
    ControleOperacionalInteligenciaAI,
)
from services.inteligencia_assistiva_ai import (
    interpretar_com_inteligencia_assistiva,
)


class ProvedorContador:
    def __init__(
        self,
    ) -> None:
        self.chamadas = 0

    def interpretar(
        self,
        solicitacao,
    ):
        self.chamadas += 1

        return RespostaProvedorInteligenciaAI(
            conteudo={
                "acao": "manter",
            },
            confianca=0.95,
            provedor="fake",
            modelo="fake-v1",
        )


def _solicitacao():
    return SolicitacaoInteligenciaAI(
        tarefa="teste_kill_switch",
        contexto={},
    )


def test_kill_switch_desligado_por_padrao_preserva_legado():
    controle = ControleOperacionalInteligenciaAI()

    assert controle.kill_switch_ativo is False

    decisao = controle.avaliar_chamada_externa()

    assert decisao.permitido is True
    assert decisao.estado == ESTADO_CIRCUITO_FECHADO
    assert decisao.motivo == "circuito_fechado"


def test_kill_switch_ativo_bloqueia_antes_do_circuit_breaker():
    controle = ControleOperacionalInteligenciaAI(
        kill_switch_ativo=True,
    )

    decisao = controle.avaliar_chamada_externa()

    assert decisao.permitido is False
    assert decisao.estado == ESTADO_CIRCUITO_FECHADO
    assert decisao.motivo == "kill_switch_ativo"

    circuito = controle.snapshot().circuit_breaker

    assert circuito.estado == ESTADO_CIRCUITO_FECHADO
    assert circuito.falhas_consecutivas == 0


def test_kill_switch_pode_ser_ativado_e_desativado():
    controle = ControleOperacionalInteligenciaAI()

    controle.ativar_kill_switch()

    assert controle.kill_switch_ativo is True
    assert controle.avaliar_chamada_externa().permitido is False

    controle.desativar_kill_switch()

    assert controle.kill_switch_ativo is False
    assert controle.avaliar_chamada_externa().permitido is True


@pytest.mark.parametrize(
    "valor",
    [
        None,
        0,
        1,
        "true",
        [],
    ],
)
def test_kill_switch_rejeita_valor_nao_booleano(
    valor,
):
    with pytest.raises(TypeError):
        ControleOperacionalInteligenciaAI(
            kill_switch_ativo=valor,
        )


def test_snapshot_expoe_estado_do_kill_switch():
    controle = ControleOperacionalInteligenciaAI(
        kill_switch_ativo=True,
    )

    snapshot = controle.snapshot()

    assert snapshot.kill_switch_ativo is True

    controle.desativar_kill_switch()

    snapshot = controle.snapshot()

    assert snapshot.kill_switch_ativo is False


def test_orquestrador_kill_switch_faz_fallback_sem_chamar_provider():
    controle = ControleOperacionalInteligenciaAI(
        kill_switch_ativo=True,
    )

    provedor = ProvedorContador()

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "acao": "fallback",
        },
        habilitado=True,
        provedor=provedor,
        validador=lambda sugestao: True,
        controle_operacional=controle,
    )

    assert resultado.status == "kill_switch_bloqueado"
    assert resultado.fallback_usado is True
    assert resultado.sugestao == {
        "acao": "fallback",
    }

    assert provedor.chamadas == 0

    snapshot = controle.snapshot()

    obs = snapshot.observabilidade

    assert obs.eventos_total == 1
    assert obs.chamadas_externas_total == 0
    assert obs.bloqueios_circuit_breaker_total == 0

    assert obs.por_status == {
        "kill_switch_bloqueado": 1,
    }

    assert snapshot.circuit_breaker.estado == ESTADO_CIRCUITO_FECHADO

    assert snapshot.circuit_breaker.falhas_consecutivas == 0


def test_configuracao_runtime_tem_kill_switch_default_true():
    texto = Path("config/configuracoes.py").read_text(encoding="utf-8-sig")

    assert '"AI_KILL_SWITCH_ATIVO"' in texto

    assert "valor_padrao=True" in texto


def test_main_repassa_kill_switch_da_configuracao():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    main = next(
        node
        for node in arvore.body
        if (
            isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name == "main"
        )
    )

    assignments = {
        node.targets[0].id: node.value
        for node in main.body
        if (
            isinstance(
                node,
                ast.Assign,
            )
            and len(node.targets) == 1
            and isinstance(
                node.targets[0],
                ast.Name,
            )
        )
    }

    controle = assignments["controle_operacional_ai"]

    kwargs = {keyword.arg: keyword.value for keyword in controle.keywords}

    valor = kwargs["kill_switch_ativo"]

    assert isinstance(
        valor,
        ast.Attribute,
    )

    assert valor.attr == "ai_kill_switch_ativo"


def test_main_mantem_consumidores_ai_desligados():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    main = next(
        node
        for node in arvore.body
        if (
            isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name == "main"
        )
    )

    assignments = {
        node.targets[0].id: node.value
        for node in main.body
        if (
            isinstance(
                node,
                ast.Assign,
            )
            and len(node.targets) == 1
            and isinstance(
                node.targets[0],
                ast.Name,
            )
        )
    }

    for nome in (
        "classificador",
        "curadoria_publicacao",
    ):

        chamada = assignments[nome]

        kwargs = {keyword.arg: keyword.value for keyword in chamada.keywords}

        habilitado = kwargs["habilitado"]

        assert isinstance(
            habilitado,
            ast.Constant,
        )

        assert habilitado.value is False


# 63.8738, -149.7525
