from __future__ import annotations

from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
)
from models.oferta import Oferta
from services.curadoria_publicacao_assistida_ai import (
    ACAO_MANTER,
    ACAO_REVISAO_MANUAL,
    CuradoriaPublicacaoAssistidaAI,
)
from services.inteligencia_assistiva_ai import (
    CONFIANCA_MINIMA_PADRAO,
)


class ProvedorFake:
    def __init__(
        self,
        *,
        acao=ACAO_REVISAO_MANUAL,
        motivo="ambiguidade editorial",
        confianca=0.95,
        erro=None,
        conteudo_extra=None,
    ):
        self.acao = acao
        self.motivo = motivo
        self.confianca = confianca
        self.erro = erro
        self.conteudo_extra = conteudo_extra
        self.chamadas = 0
        self.solicitacoes = []

    def interpretar(
        self,
        solicitacao,
    ):
        self.chamadas += 1
        self.solicitacoes.append(solicitacao)

        if self.erro is not None:
            raise self.erro

        conteudo = {
            "acao_sugerida": self.acao,
            "motivo_curto": self.motivo,
        }

        if self.conteudo_extra:
            conteudo.update(self.conteudo_extra)

        return RespostaProvedorInteligenciaAI(
            conteudo=conteudo,
            confianca=self.confianca,
            provedor="fake",
            modelo="fake-v19d",
        )


def _oferta(
    *,
    nome="Placa de Video RTX 4060 8GB GDDR6",
    categoria="Placa de v\u00eddeo",
    preco=2199.0,
    preco_antigo=None,
    relevancia=90.0,
    confianca=95.0,
):
    oferta = Oferta(
        nome=nome,
        loja="Teste",
        preco=preco,
        preco_antigo=preco_antigo,
        link="https://example.com/produto",
        imagem=None,
        marketplace="teste",
    )

    oferta.categoria = categoria
    oferta.eh_nicho = True
    oferta.relevancia_nicho = relevancia
    oferta.confianca_normalizacao = confianca

    return oferta


def test_oferta_bloqueada_deterministicamente_nao_chama_ai():
    provedor = ProvedorFake()

    curadoria = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = curadoria.analisar(_oferta(nome=("Placa de Video RTX 3060 ou " "RTX 4060 8GB")))

    assert resultado.publicavel is False

    assert resultado.diagnostico.motivo == "reprovada_deterministicamente"

    assert resultado.gate_ai_acionado is False
    assert resultado.inteligencia_ai is None
    assert resultado.revisao_manual_sugerida is False
    assert provedor.chamadas == 0


def test_oferta_clara_publicavel_nao_chama_ai():
    provedor = ProvedorFake()

    curadoria = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = curadoria.analisar(
        _oferta(
            confianca=95.0,
            relevancia=90.0,
        )
    )

    assert resultado.publicavel is True

    assert resultado.diagnostico.motivo == "sem_incerteza_editorial_objetiva"

    assert resultado.gate_ai_acionado is False
    assert resultado.inteligencia_ai is None
    assert provedor.chamadas == 0


def test_confianca_normalizacao_baixa_abre_gate_sem_mudar_curadoria():
    provedor = ProvedorFake(
        acao=ACAO_REVISAO_MANUAL,
    )

    curadoria = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = curadoria.analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.publicavel is True
    assert resultado.gate_ai_acionado is True
    assert provedor.chamadas == 1

    assert "confianca_normalizacao_abaixo_de_90" in resultado.diagnostico.sinais

    assert resultado.inteligencia_ai.status == "sugestao_ai_validada"

    assert resultado.revisao_manual_sugerida is True


def test_relevancia_nicho_baixa_abre_gate():
    provedor = ProvedorFake(
        acao=ACAO_MANTER,
    )

    curadoria = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = curadoria.analisar(
        _oferta(
            relevancia=70.0,
            confianca=95.0,
        )
    )

    assert resultado.publicavel is True
    assert resultado.gate_ai_acionado is True

    assert "relevancia_nicho_abaixo_de_80" in resultado.diagnostico.sinais

    assert resultado.revisao_manual_sugerida is False


def test_ai_nao_altera_resultado_deterministico():
    provedor = ProvedorFake(
        acao=ACAO_REVISAO_MANUAL,
    )

    curadoria = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = curadoria.analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.curadoria_final == resultado.curadoria_deterministica

    assert resultado.publicavel == resultado.curadoria_deterministica.publicavel

    assert resultado.nota == resultado.curadoria_deterministica.nota

    assert resultado.bloqueios == resultado.curadoria_deterministica.bloqueios

    assert resultado.motivos == resultado.curadoria_deterministica.motivos


def test_ai_nao_muda_campos_de_curadoria_da_oferta():
    provedor = ProvedorFake(
        acao=ACAO_REVISAO_MANUAL,
    )

    oferta = _oferta(
        confianca=70.0,
    )

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    ).analisar(oferta)

    assert oferta.curadoria_publicavel == resultado.curadoria_deterministica.publicavel

    assert oferta.nota_curadoria == resultado.curadoria_deterministica.nota

    assert oferta.motivos_curadoria == list(
        resultado.curadoria_deterministica.bloqueios + resultado.curadoria_deterministica.motivos
    )


def test_acao_publicar_e_rejeitada():
    provedor = ProvedorFake(
        acao="publicar",
    )

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    ).analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.inteligencia_ai.status == "rejeitado_validacao_deterministica"

    assert resultado.revisao_manual_sugerida is False

    assert resultado.curadoria_final == resultado.curadoria_deterministica


def test_payload_com_autoridade_extra_e_rejeitado():
    provedor = ProvedorFake(
        acao=ACAO_REVISAO_MANUAL,
        conteudo_extra={
            "publicavel": True,
        },
    )

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    ).analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.inteligencia_ai.status == "rejeitado_validacao_deterministica"

    assert resultado.revisao_manual_sugerida is False


def test_confianca_ai_baixa_preserva_fallback():
    provedor = ProvedorFake(
        acao=ACAO_REVISAO_MANUAL,
        confianca=(CONFIANCA_MINIMA_PADRAO - 0.01),
    )

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    ).analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.inteligencia_ai.status == "confianca_insuficiente"

    assert resultado.inteligencia_ai.fallback_usado is True

    assert resultado.revisao_manual_sugerida is False


def test_erro_do_provider_preserva_fallback():
    provedor = ProvedorFake(erro=RuntimeError("provider offline"))

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    ).analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.inteligencia_ai.status == "erro_provedor"

    assert resultado.inteligencia_ai.fallback_usado is True

    assert resultado.revisao_manual_sugerida is False


def test_ai_desabilitada_nao_chama_provider():
    provedor = ProvedorFake()

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=False,
        provedor=provedor,
    ).analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.gate_ai_acionado is True

    assert resultado.inteligencia_ai.status == "desabilitado"

    assert provedor.chamadas == 0

    assert resultado.revisao_manual_sugerida is False


def test_contexto_ai_nao_recebe_preco_link_score_ou_autoridade():
    provedor = ProvedorFake(
        acao=ACAO_MANTER,
    )

    (
        CuradoriaPublicacaoAssistidaAI(
            habilitado=True,
            provedor=provedor,
        ).analisar(
            _oferta(
                confianca=70.0,
            )
        )
    )

    assert provedor.chamadas == 1

    contexto = provedor.solicitacoes[0].contexto

    assert set(contexto.keys()) == {
        "titulo",
        "categoria",
        "sinais_deterministicos",
        "acoes_permitidas",
        "regra",
    }

    for proibido in (
        "preco",
        "preco_antigo",
        "link",
        "nota",
        "nota_curadoria",
        "publicavel",
        "budget",
        "score",
        "pontuacao",
    ):
        assert proibido not in contexto


def test_motivo_vazio_e_rejeitado():
    provedor = ProvedorFake(
        acao=ACAO_MANTER,
        motivo="   ",
    )

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    ).analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.inteligencia_ai.status == "rejeitado_validacao_deterministica"


def test_motivo_excessivamente_longo_e_rejeitado():
    provedor = ProvedorFake(
        acao=ACAO_MANTER,
        motivo="x" * 241,
    )

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    ).analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.inteligencia_ai.status == "rejeitado_validacao_deterministica"


def test_acao_manter_validada_nao_sinaliza_revisao():
    provedor = ProvedorFake(
        acao=ACAO_MANTER,
        motivo="sinais ainda aceitaveis",
    )

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    ).analisar(
        _oferta(
            confianca=70.0,
        )
    )

    assert resultado.inteligencia_ai.status == "sugestao_ai_validada"

    assert resultado.revisao_manual_sugerida is False

    assert resultado.publicavel is True


def test_preco_antigo_invalido_abre_gate_sem_enviar_preco():
    provedor = ProvedorFake(
        acao=ACAO_REVISAO_MANUAL,
    )

    resultado = CuradoriaPublicacaoAssistidaAI(
        habilitado=True,
        provedor=provedor,
    ).analisar(
        _oferta(
            preco=2199.0,
            preco_antigo=2199.0,
        )
    )

    assert resultado.publicavel is True

    assert "preco_antigo_nao_confirma_desconto" in resultado.diagnostico.sinais

    assert resultado.gate_ai_acionado is True


def test_resultado_assistido_expoe_interface_da_curadoria_original():
    resultado = CuradoriaPublicacaoAssistidaAI(habilitado=False).analisar(_oferta())

    assert isinstance(
        resultado.publicavel,
        bool,
    )

    assert resultado.publicavel == resultado.curadoria_final.publicavel

    assert resultado.nota == resultado.curadoria_final.nota

    assert resultado.motivos == resultado.curadoria_final.motivos

    assert resultado.bloqueios == resultado.curadoria_final.bloqueios
