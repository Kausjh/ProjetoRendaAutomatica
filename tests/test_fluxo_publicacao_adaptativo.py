from models.oferta import Oferta
from services.executor_pipeline import ExecutorPipeline


def criar_item(
    nome: str,
    score: float,
    tipo: str = "normal",
):
    oferta = Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=100.0,
        preco_antigo=None,
        link=f"https://mercadolivre.com.br/{nome}",
        imagem=None,
    )
    oferta.tipo_oportunidade = tipo

    return (oferta, score, None, False)


def test_reposicao_adaptativa_completa_fila_vazia_com_melhores_candidatos():
    candidatos = [
        criar_item("A", 70),
        criar_item("B", 64),
        criar_item("C", 58),
        criar_item("D", 54),
    ]

    selecionados, reposicao = ExecutorPipeline._selecionar_candidatos_para_fila(
        candidatos=candidatos,
        pontuacao_minima_principal=72,
        reposicao_adaptativa_ativa=True,
        pontuacao_minima_reposicao=55,
        alvo_minimo_pendentes=3,
        quantidade_pendente=0,
    )

    assert [item[0].nome for item in selecionados] == ["A", "B", "C"]
    assert reposicao == 3


def test_reposicao_adaptativa_nao_abaixa_piso_quando_fila_ja_tem_alvo():
    candidatos = [
        criar_item("Forte", 80),
        criar_item("Reserva", 65),
    ]

    selecionados, reposicao = ExecutorPipeline._selecionar_candidatos_para_fila(
        candidatos=candidatos,
        pontuacao_minima_principal=72,
        reposicao_adaptativa_ativa=True,
        pontuacao_minima_reposicao=55,
        alvo_minimo_pendentes=3,
        quantidade_pendente=3,
    )

    assert [item[0].nome for item in selecionados] == ["Forte"]
    assert reposicao == 0


def test_reposicao_considera_candidatos_fortes_antes_de_completar_alvo():
    candidatos = [
        criar_item("Forte", 90),
        criar_item("Reserva 1", 68),
        criar_item("Reserva 2", 60),
        criar_item("Fraca", 40),
    ]

    selecionados, reposicao = ExecutorPipeline._selecionar_candidatos_para_fila(
        candidatos=candidatos,
        pontuacao_minima_principal=72,
        reposicao_adaptativa_ativa=True,
        pontuacao_minima_reposicao=55,
        alvo_minimo_pendentes=3,
        quantidade_pendente=0,
    )

    assert [item[0].nome for item in selecionados] == [
        "Forte",
        "Reserva 1",
        "Reserva 2",
    ]
    assert reposicao == 2


def test_urgencia_continua_furando_piso_principal():
    candidatos = [
        criar_item("Urgente", 20, "anomalia_forte"),
        criar_item("Comum", 50),
    ]

    selecionados, reposicao = ExecutorPipeline._selecionar_candidatos_para_fila(
        candidatos=candidatos,
        pontuacao_minima_principal=72,
        reposicao_adaptativa_ativa=False,
        pontuacao_minima_reposicao=55,
        alvo_minimo_pendentes=3,
        quantidade_pendente=0,
    )

    assert [item[0].nome for item in selecionados] == ["Urgente"]
    assert reposicao == 0
