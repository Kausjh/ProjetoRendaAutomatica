from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
)
from models.oferta import Oferta
from services.classificador_produto_assistido_ai import (
    ClassificadorProdutoAssistidoAI,
)
from services.inteligencia_assistiva_ai import (
    CONFIANCA_MINIMA_PADRAO,
)


class ProvedorFake:
    def __init__(
        self,
        *,
        categoria="Armazenamento",
        confianca=0.95,
        erro=None,
        conteudo_extra=None,
    ):
        self.categoria = categoria
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
            "categoria_sugerida": self.categoria,
        }

        if self.conteudo_extra:
            conteudo.update(self.conteudo_extra)

        return RespostaProvedorInteligenciaAI(
            conteudo=conteudo,
            confianca=self.confianca,
            provedor="fake",
            modelo="fake-v19c",
        )


def _oferta(
    nome,
):
    return Oferta(
        nome=nome,
        loja="Teste",
        preco=999.90,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace="teste",
    )


def test_categoria_clara_nao_aciona_gate_ai():
    provedor = ProvedorFake()

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("AMD Ryzen 7 5700X"))

    assert resultado.classificacao_final.categoria == "Processador"

    assert resultado.diagnostico.ambiguo is False

    assert resultado.diagnostico.motivo == "categoria_deterministica_sem_empate"

    assert resultado.diagnostico.identidade_principal_explicita is False

    assert resultado.gate_ai_acionado is False
    assert resultado.inteligencia_ai is None
    assert provedor.chamadas == 0


def test_identidade_principal_explicita_nao_chama_ai():
    provedor = ProvedorFake()

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(
        _oferta("Notebook Gamer Acer Nitro " "Ryzen 7 RTX 4060 16GB SSD NVMe")
    )

    assert resultado.classificacao_final.categoria == "Notebook"

    assert resultado.diagnostico.identidade_principal_explicita is True

    assert resultado.diagnostico.motivo == "identidade_principal_explicita"

    assert resultado.diagnostico.ambiguo is False
    assert resultado.gate_ai_acionado is False
    assert provedor.chamadas == 0


def test_produto_bloqueado_nao_pode_ser_ressuscitado():
    provedor = ProvedorFake(categoria="Placa de vídeo")

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Camiseta Gamer RTX 5090 NVIDIA"))

    final = resultado.classificacao_final

    assert final.eh_nicho is False
    assert final.categoria is None

    assert resultado.diagnostico.ambiguo is False
    assert resultado.gate_ai_acionado is False
    assert provedor.chamadas == 0


def test_produto_nao_identificado_nao_pode_ser_ressuscitado():
    provedor = ProvedorFake(categoria="Processador")

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Produto Misterioso XPTO 123"))

    final = resultado.classificacao_final

    assert final.eh_nicho is False
    assert final.categoria is None
    assert final.relevancia == 0

    assert resultado.gate_ai_acionado is False
    assert provedor.chamadas == 0


def test_empate_real_e_detectado():
    classificador = ClassificadorProdutoAssistidoAI()

    resultado = classificador.classificar(_oferta("Ryzen NVMe"))

    diagnostico = resultado.diagnostico

    assert diagnostico.ambiguo is True

    assert diagnostico.motivo == "empate_real_categorias_topo"

    assert set(diagnostico.categorias_topo) == {
        "Processador",
        "Armazenamento",
    }

    assert resultado.classificacao_deterministica.categoria == "Processador"


def test_ai_desambiguadora_pode_escolher_apenas_candidata():
    provedor = ProvedorFake(
        categoria="Armazenamento",
        confianca=0.95,
    )

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Ryzen NVMe"))

    assert provedor.chamadas == 1
    assert resultado.gate_ai_acionado is True

    assert resultado.inteligencia_ai.status == "sugestao_ai_validada"

    assert resultado.classificacao_deterministica.categoria == "Processador"

    assert resultado.classificacao_final.categoria == "Armazenamento"


def test_ai_nao_altera_eh_nicho_nem_relevancia():
    provedor = ProvedorFake(
        categoria="Armazenamento",
    )

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Ryzen NVMe"))

    base = resultado.classificacao_deterministica
    final = resultado.classificacao_final

    assert final.eh_nicho == base.eh_nicho

    assert final.relevancia == base.relevancia

    assert final.termos_encontrados == base.termos_encontrados


def test_categoria_inventada_e_rejeitada():
    provedor = ProvedorFake(categoria="Categoria Inventada")

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Ryzen NVMe"))

    assert resultado.inteligencia_ai.status == "rejeitado_validacao_deterministica"

    assert resultado.classificacao_final == resultado.classificacao_deterministica


def test_payload_com_campo_extra_e_rejeitado():
    provedor = ProvedorFake(
        categoria="Armazenamento",
        conteudo_extra={
            "publicar": True,
        },
    )

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Ryzen NVMe"))

    assert resultado.inteligencia_ai.status == "rejeitado_validacao_deterministica"

    assert resultado.classificacao_final == resultado.classificacao_deterministica


def test_confianca_baixa_preserva_deterministico():
    provedor = ProvedorFake(
        categoria="Armazenamento",
        confianca=(CONFIANCA_MINIMA_PADRAO - 0.01),
    )

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Ryzen NVMe"))

    assert resultado.inteligencia_ai.status == "confianca_insuficiente"

    assert resultado.classificacao_final == resultado.classificacao_deterministica


def test_erro_provedor_preserva_deterministico():
    provedor = ProvedorFake(erro=RuntimeError("provedor fora"))

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Ryzen NVMe"))

    assert resultado.inteligencia_ai.status == "erro_provedor"

    assert resultado.classificacao_final == resultado.classificacao_deterministica


def test_ai_desabilitada_preserva_deterministico_sem_chamar_provider():
    provedor = ProvedorFake(categoria="Armazenamento")

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=False,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Ryzen NVMe"))

    assert resultado.diagnostico.ambiguo is True
    assert resultado.gate_ai_acionado is True

    assert resultado.inteligencia_ai.status == "desabilitado"

    assert provedor.chamadas == 0

    assert resultado.classificacao_final == resultado.classificacao_deterministica


def test_duas_categorias_sem_empate_nao_chamam_ai():
    provedor = ProvedorFake(categoria="Processador")

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Kingston SSD NVMe Ryzen"))

    assert resultado.classificacao_deterministica.categoria == "Armazenamento"

    assert resultado.diagnostico.identidade_principal_explicita is False

    assert resultado.diagnostico.ambiguo is False

    assert resultado.diagnostico.motivo == "categoria_deterministica_sem_empate"

    assert resultado.diagnostico.categorias_topo == ("Armazenamento",)

    assert provedor.chamadas == 0


def test_contexto_ai_nao_envia_preco_link_ou_autoridade():
    provedor = ProvedorFake(categoria="Armazenamento")

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    classificador.classificar(_oferta("Ryzen NVMe"))

    assert provedor.chamadas == 1

    contexto = provedor.solicitacoes[0].contexto

    assert set(contexto.keys()) == {
        "titulo",
        "categoria_deterministica",
        "categorias_candidatas",
        "termos_por_categoria",
        "regra",
    }

    for proibido in (
        "preco",
        "link",
        "publicar",
        "budget",
        "desconto",
    ):
        assert proibido not in contexto


def test_aplicar_classificacao_escreve_somente_resultado_final_validado():
    provedor = ProvedorFake(categoria="Armazenamento")

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    oferta = _oferta("Ryzen NVMe")

    resultado = classificador.aplicar_classificacao(oferta)

    assert resultado.classificacao_final.categoria == "Armazenamento"

    assert oferta.eh_nicho is True
    assert oferta.categoria == "Armazenamento"

    assert oferta.relevancia_nicho == resultado.classificacao_deterministica.relevancia


def test_ai_escolhendo_categoria_deterministica_nao_muda_objeto_base():
    provedor = ProvedorFake(categoria="Processador")

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=True,
        provedor=provedor,
    )

    resultado = classificador.classificar(_oferta("Ryzen NVMe"))

    assert resultado.inteligencia_ai.status == "sugestao_ai_validada"

    assert resultado.classificacao_final == resultado.classificacao_deterministica
