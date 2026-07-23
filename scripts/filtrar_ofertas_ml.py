from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from filters.filtro_qualidade import (
    FiltroQualidade,
)
from services.carregador_produtos import (
    CarregadorProdutos,
)


PASTA_RAIZ = Path(__file__).resolve().parents[1]

PASTA_PROCESSADOS = (
    PASTA_RAIZ
    / "data"
    / "processado"
)

ARQUIVO_RANKING = (
    PASTA_PROCESSADOS
    / "ranking_completo_ml.json"
)

ARQUIVO_APROVADOS = (
    PASTA_PROCESSADOS
    / "ofertas_aprovadas_ml.json"
)


def salvar_json(
    caminho: Path,
    conteudo: list[dict[str, Any]],
) -> None:
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with caminho.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            conteudo,
            arquivo,
            ensure_ascii=False,
            indent=4,
        )


def exibir_top_ofertas(
    ofertas: list[dict[str, Any]],
    limite: int = 20,
) -> None:
    print("\n")
    print("=" * 70)
    print("MELHORES OFERTAS")
    print("=" * 70)

    if not ofertas:
        print(
            "Nenhum produto atingiu a nota mínima."
        )
        return

    for posicao, produto in enumerate(
        ofertas[:limite],
        start=1,
    ):
        titulo = produto.get(
            "titulo",
            "Sem título",
        )

        preco = produto.get("preco")
        desconto = produto.get("desconto")
        nota = produto.get("nota", 0)
        categoria = produto.get(
            "categoria",
            "Não informada",
        )

        print(
            f"\n{posicao:02d}. {titulo}"
        )

        print(f"Nota: {nota}")

        if isinstance(preco, (int, float)):
            print(
                "Preço: "
                f"R$ {preco:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        else:
            print("Preço: não informado")

        if isinstance(desconto, (int, float)):
            print(
                f"Desconto: {desconto:.0f}%"
            )
        else:
            print("Desconto: não informado")

        print(f"Categoria: {categoria}")

        print("Motivos:")

        for motivo in produto.get(
            "motivos",
            [],
        ):
            print(f"  {motivo}")


def main() -> None:
    print("=" * 70)
    print("FILTRO DE OFERTAS - MERCADO LIVRE")
    print("=" * 70)

    carregador = CarregadorProdutos()

    produtos, resumo_arquivos = (
        carregador.carregar_todos()
    )

    print("\nArquivos encontrados:")

    for arquivo, quantidade in (
        resumo_arquivos.items()
    ):
        print(
            f"- {arquivo}: "
            f"{quantidade} produtos"
        )

    print(
        "\nProdutos únicos após juntar "
        f"os arquivos: {len(produtos)}"
    )

    filtro = FiltroQualidade()

    ranking = filtro.analisar_produtos(
        produtos
    )

    aprovados = filtro.obter_aprovados(
        ranking
    )

    salvar_json(
        ARQUIVO_RANKING,
        ranking,
    )

    salvar_json(
        ARQUIVO_APROVADOS,
        aprovados,
    )

    total_reprovados = (
        len(ranking) - len(
            [
                produto
                for produto in ranking
                if produto.get("aprovado")
            ]
        )
    )

    total_aprovados_sem_limite = len(
        [
            produto
            for produto in ranking
            if produto.get("aprovado")
        ]
    )

    print("\n")
    print("=" * 70)
    print("RESUMO")
    print("=" * 70)

    print(
        f"Produtos analisados: {len(ranking)}"
    )

    print(
        "Produtos que atingiram a nota: "
        f"{total_aprovados_sem_limite}"
    )

    print(
        f"Produtos reprovados: {total_reprovados}"
    )

    print(
        "Produtos selecionados para publicação: "
        f"{len(aprovados)}"
    )

    exibir_top_ofertas(
        aprovados,
        limite=20,
    )

    print("\n")
    print("=" * 70)
    print("ARQUIVOS SALVOS")
    print("=" * 70)

    print(
        "\nRanking completo:\n"
        f"{ARQUIVO_RANKING}"
    )

    print(
        "\nOfertas aprovadas:\n"
        f"{ARQUIVO_APROVADOS}"
    )


if __name__ == "__main__":
    main()