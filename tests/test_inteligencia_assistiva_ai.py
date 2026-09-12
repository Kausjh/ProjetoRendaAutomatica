import pytest

from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
    SolicitacaoInteligenciaAI,
)
from services.inteligencia_assistiva_ai import (
    CONFIANCA_MINIMA_PADRAO,
    interpretar_com_inteligencia_assistiva,
)


class ProvedorFake:
    def __init__(
        self,
        resposta=None,
        erro=None,
    ):
        self.resposta = resposta
        self.erro = erro
        self.chamadas = 0

    def interpretar(
        self,
        solicitacao,
    ):
        self.chamadas += 1

        if self.erro is not None:
            raise self.erro

        return self.resposta


def _solicitacao():
    return SolicitacaoInteligenciaAI(
        tarefa="classificar_ambiguidade_produto",
        contexto={
            "titulo": "Kit Gamer RTX 5070",
        },
    )


def _resposta(
    *,
    conteudo=None,
    confianca=0.95,
):
    if conteudo is None:
        conteudo = {
            "categoria_sugerida": "gpu",
        }

    return RespostaProvedorInteligenciaAI(
        conteudo=conteudo,
        confianca=confianca,
        provedor="fake",
        modelo="fake-v1",
    )


def _validar_gpu(
    sugestao,
):
    return sugestao.get("categoria_sugerida") == "gpu"


def _assert_protecoes(
    resultado,
):
    assert resultado.somente_sugestao is True
    assert resultado.autoriza_publicacao is False
    assert resultado.autoriza_alteracao_budget is False
    assert resultado.substitui_regras_deterministicas is False


def test_desabilitado_nem_chama_provedor():
    provedor = ProvedorFake(resposta=_resposta())

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=False,
        provedor=provedor,
        validador=_validar_gpu,
    )

    assert provedor.chamadas == 0
    assert resultado.status == "desabilitado"
    assert resultado.fallback_usado is True
    assert resultado.origem == "fallback_deterministico"

    _assert_protecoes(resultado)


def test_habilitado_sem_provedor_faz_fallback():
    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=None,
        validador=_validar_gpu,
    )

    assert resultado.status == "sem_provedor"
    assert resultado.fallback_usado is True

    _assert_protecoes(resultado)


def test_sem_validador_deterministico_faz_fallback():
    provedor = ProvedorFake(resposta=_resposta())

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=provedor,
        validador=None,
    )

    assert provedor.chamadas == 0

    assert resultado.status == "sem_validador_deterministico"

    _assert_protecoes(resultado)


def test_erro_do_provedor_faz_fallback():
    provedor = ProvedorFake(erro=RuntimeError("provedor fora"))

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
    )

    assert resultado.status == "erro_provedor"
    assert resultado.tipo_erro == "RuntimeError"
    assert resultado.fallback_usado is True

    _assert_protecoes(resultado)


def test_resposta_de_tipo_errado_faz_fallback():
    provedor = ProvedorFake(
        resposta={
            "categoria_sugerida": "gpu",
        }
    )

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
    )

    assert resultado.status == "resposta_provedor_invalida"

    _assert_protecoes(resultado)


def test_confianca_baixa_faz_fallback():
    provedor = ProvedorFake(resposta=_resposta(confianca=(CONFIANCA_MINIMA_PADRAO - 0.01)))

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
    )

    assert resultado.status == "confianca_insuficiente"

    assert resultado.fallback_usado is True

    _assert_protecoes(resultado)


def test_validador_rejeita_sugestao():
    provedor = ProvedorFake(
        resposta=_resposta(
            conteudo={
                "categoria_sugerida": "notebook",
            }
        )
    )

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
    )

    assert resultado.status == "rejeitado_validacao_deterministica"

    assert resultado.fallback_usado is True

    _assert_protecoes(resultado)


def test_erro_no_validador_faz_fallback():
    provedor = ProvedorFake(resposta=_resposta())

    def validador_com_erro(
        sugestao,
    ):
        raise ValueError("falha de validacao")

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=provedor,
        validador=validador_com_erro,
    )

    assert resultado.status == "erro_validacao_deterministica"

    assert resultado.tipo_erro == "ValueError"

    _assert_protecoes(resultado)


def test_sugestao_valida_e_aceita_sem_autoridade_operacional():
    provedor = ProvedorFake(resposta=_resposta())

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback={
            "categoria_sugerida": "outros",
        },
        habilitado=True,
        provedor=provedor,
        validador=_validar_gpu,
    )

    assert resultado.status == "sugestao_ai_validada"
    assert resultado.origem == "ai"
    assert resultado.fallback_usado is False

    assert resultado.validada_deterministicamente is True

    assert resultado.confianca == 0.95
    assert resultado.provedor == "fake"
    assert resultado.modelo == "fake-v1"

    assert resultado.sugestao == {
        "categoria_sugerida": "gpu",
    }

    _assert_protecoes(resultado)


def test_fallback_original_nao_e_mutado():
    fallback = {
        "categoria_sugerida": "outros",
    }

    resultado = interpretar_com_inteligencia_assistiva(
        solicitacao=_solicitacao(),
        fallback=fallback,
        habilitado=False,
    )

    resultado.sugestao["categoria_sugerida"] = "alterado"

    assert fallback == {
        "categoria_sugerida": "outros",
    }


@pytest.mark.parametrize(
    "valor",
    [
        -0.1,
        1.1,
        "abc",
        None,
    ],
)
def test_confianca_minima_invalida_falha(
    valor,
):
    with pytest.raises(ValueError):
        interpretar_com_inteligencia_assistiva(
            solicitacao=_solicitacao(),
            fallback={},
            confianca_minima=valor,
        )


def test_modelo_rejeita_confianca_fora_da_faixa():
    with pytest.raises(ValueError):
        RespostaProvedorInteligenciaAI(
            conteudo={},
            confianca=1.5,
            provedor="fake",
        )


def test_solicitacao_exige_tarefa():
    with pytest.raises(ValueError):
        SolicitacaoInteligenciaAI(
            tarefa="",
            contexto={},
        )
