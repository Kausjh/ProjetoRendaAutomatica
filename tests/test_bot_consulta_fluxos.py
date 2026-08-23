from bot_consulta import (
    ResumoProduto,
    canonizar_categoria,
    escolher_representante_comparacao,
    formatar_moeda,
)


def criar_resumo(
    titulo: str,
    preco_atual: float,
    menor_preco: float,
    registros: int,
) -> ResumoProduto:
    return ResumoProduto(
        chave=titulo,
        titulo=titulo,
        link="https://exemplo.com",
        categoria="Placa de vídeo",
        preco_atual=preco_atual,
        menor_preco=menor_preco,
        maior_preco=max(preco_atual, menor_preco),
        preco_medio=(preco_atual + menor_preco) / 2,
        quantidade_registros=registros,
        primeiro_registro_em="2026-07-01T12:00:00",
        esta_no_menor_preco=preco_atual <= menor_preco,
        dias_de_acompanhamento=40,
    )


def test_formatar_moeda_padrao_brasileiro():
    assert formatar_moeda(1122) == "R$ 1.122,00"
    assert formatar_moeda(5999.5) == "R$ 5.999,50"


def test_canonizar_categorias_sobrepostas():
    assert canonizar_categoria("Fonte") == "Fonte e energia"
    assert canonizar_categoria("Fonte e energia") == "Fonte e energia"
    assert canonizar_categoria("Notebook gamer") == "Notebook"
    assert canonizar_categoria("Mouse") == "Mouse e mousepad"


def test_comparacao_ignora_outlier_grosseiramente_caro():
    resultados = [
        criar_resumo("RTX 4060 anúncio absurdo", 5999, 5099, 12),
        criar_resumo("RTX 4060 normal A", 2199, 1999, 8),
        criar_resumo("RTX 4060 normal B", 2299, 2099, 10),
        criar_resumo("RTX 4060 normal C", 2099, 1999, 7),
    ]

    escolhido = escolher_representante_comparacao(resultados)

    assert escolhido is not None
    assert escolhido.preco_atual != 5999
    assert escolhido.titulo == "RTX 4060 normal B"


def test_comparacao_funciona_com_um_unico_resultado():
    unico = criar_resumo("RTX 4060 único", 2199, 1999, 3)

    assert escolher_representante_comparacao([unico]) == unico
