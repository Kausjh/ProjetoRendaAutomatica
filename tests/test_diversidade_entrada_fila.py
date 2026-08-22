from models.oferta import Oferta
from services.executor_pipeline import ExecutorPipeline


def criar_item(nome: str, categoria: str, score: float, tipo: str = "normal"):
    oferta = Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=100.0,
        preco_antigo=None,
        link=f"https://mercadolivre.com.br/{nome}",
        imagem=None,
    )
    oferta.categoria = categoria
    oferta.tipo_oportunidade = tipo

    return (oferta, score, None, False)


def test_entrada_fila_faz_rodadas_por_categoria():
    candidatos = [
        criar_item("Monitor 1", "Monitor", 99),
        criar_item("Monitor 2", "Monitor", 98),
        criar_item("Monitor 3", "Monitor", 97),
        criar_item("SSD 1", "Armazenamento", 90),
        criar_item("GPU 1", "Placa de vídeo", 89),
        criar_item("Mouse 1", "Mouse", 88),
    ]

    selecionados = ExecutorPipeline._selecionar_candidatos_diversos(
        candidatos=candidatos,
        limite_total=6,
        limite_por_categoria=2,
    )

    categorias = [item[0].categoria for item in selecionados]

    assert categorias[:4] == [
        "Monitor",
        "Armazenamento",
        "Placa de vídeo",
        "Mouse",
    ]
    assert categorias.count("Monitor") == 2


def test_entrada_fila_nao_deixa_categoria_dominar():
    candidatos = [
        criar_item("Monitor 1", "Monitor", 99),
        criar_item("Monitor 2", "Monitor", 98),
        criar_item("Monitor 3", "Monitor", 97),
        criar_item("Monitor 4", "Monitor", 96),
        criar_item("SSD 1", "Armazenamento", 80),
    ]

    selecionados = ExecutorPipeline._selecionar_candidatos_diversos(
        candidatos=candidatos,
        limite_total=12,
        limite_por_categoria=2,
    )

    categorias = [item[0].categoria for item in selecionados]

    assert categorias.count("Monitor") == 2
    assert categorias.count("Armazenamento") == 1
    assert len(selecionados) == 3


def test_urgencia_fura_balanceamento_de_entrada():
    candidatos = [
        criar_item("Bug 1", "Monitor", 100, "possivel_preco_bugado"),
        criar_item("Bug 2", "Monitor", 99, "anomalia_forte"),
        criar_item("Monitor comum", "Monitor", 98),
        criar_item("SSD", "Armazenamento", 90),
    ]

    selecionados = ExecutorPipeline._selecionar_candidatos_diversos(
        candidatos=candidatos,
        limite_total=4,
        limite_por_categoria=1,
    )

    nomes = [item[0].nome for item in selecionados]

    assert "Bug 1" in nomes
    assert "Bug 2" in nomes
    assert "SSD" in nomes
