from models.oferta import Oferta
from services.classificador_produto import ClassificadorProduto


def criar_oferta(nome: str) -> Oferta:
    return Oferta(
        nome=nome,
        loja="Loja de teste",
        preco=1000,
        preco_antigo=1200,
        link="https://exemplo.com/produto",
        imagem=None,
    )


def executar_teste() -> None:
    classificador = ClassificadorProduto()

    casos = [
        ("Placa de Vídeo RTX 4060 8GB GDDR6", True, "Placa de vídeo"),
        ("Processador AMD Ryzen 7 5700X", True, "Processador"),
        ("SSD NVMe M.2 1TB PCIe 4.0", True, "Armazenamento"),
        ("Memória RAM DDR4 16GB 3200MHz", True, "Memória RAM"),
        ("Fonte ATX 750W 80 Plus Bronze", True, "Fonte"),
        ("Monitor Gamer IPS 180Hz 24 polegadas", True, "Monitor"),
        ("Teclado Mecânico Gamer RGB", True, "Teclado"),
        ("Camiseta Gamer Preta", False, None),
        ("Caneca Gamer Personalizada", False, None),
        ("Livro sobre montagem de computadores", False, None),
        ("Liquidificador 1000W", False, None),
    ]

    quantidade_aprovada = 0
    quantidade_rejeitada = 0

    for indice, caso in enumerate(casos, start=1):
        nome, esperado_nicho, categoria_esperada = caso

        oferta = criar_oferta(nome)

        resultado = classificador.aplicar_classificacao(oferta)

        status = "APROVADO" if resultado.eh_nicho else "REJEITADO"

        print("=" * 80)
        print(f"Teste {indice}")
        print(f"Produto: {nome}")
        print(f"Resultado: {status}")
        print(f"Categoria: {resultado.categoria}")
        print(f"Relevância: {resultado.relevancia}")
        print("Termos encontrados: " f"{resultado.termos_encontrados}")
        print(f"Motivo: {resultado.motivo}")

        assert resultado.eh_nicho == esperado_nicho, (
            f"Falha no produto '{nome}': "
            f"esperado eh_nicho={esperado_nicho}, "
            f"recebido={resultado.eh_nicho}."
        )

        assert resultado.categoria == categoria_esperada, (
            f"Falha no produto '{nome}': "
            f"categoria esperada={categoria_esperada}, "
            f"recebida={resultado.categoria}."
        )

        if resultado.eh_nicho:
            quantidade_aprovada += 1

        else:
            quantidade_rejeitada += 1

    print("=" * 80)
    print("TESTES CONCLUÍDOS COM SUCESSO")
    print(f"Produtos avaliados: {len(casos)}")
    print(f"Produtos aprovados: {quantidade_aprovada}")
    print(f"Produtos rejeitados: {quantidade_rejeitada}")
    print("=" * 80)


if __name__ == "__main__":
    executar_teste()
