from __future__ import annotations

import time
from datetime import datetime

from playwright.sync_api import sync_playwright

from scrapers.mercado_livre.categorias import (
    CATEGORIAS_ALVO,
    FiltroCategoriasMercadoLivre,
    criar_slug_categoria,
)
from scrapers.mercado_livre.coletor_produtos import (
    ColetorProdutosMercadoLivre,
)
from scrapers.mercado_livre.navegador import (
    conectar_ao_chrome,
)


def main() -> None:
    resultados: dict[str, int] = {}

    with sync_playwright() as playwright:
        _, _, pagina = conectar_ao_chrome(
            playwright
        )

        print("Conectado ao Chrome.")
        print(f"Página encontrada: {pagina.url}")

        filtro = FiltroCategoriasMercadoLivre(
            pagina=pagina,
            tempo_espera_atualizacao=3.0,
        )

        for numero, categoria in enumerate(
            CATEGORIAS_ALVO,
            start=1,
        ):
            print("\n")
            print("#" * 70)
            print(
                f"CATEGORIA {numero}/"
                f"{len(CATEGORIAS_ALVO)}"
            )
            print("#" * 70)

            filtro.selecionar_categoria(
                categoria
            )

            coletor = (
                ColetorProdutosMercadoLivre(
                    pagina=pagina,
                    categoria=categoria,
                    tempo_espera_scroll=2.5,
                    tentativas_sem_crescimento=5,
                    limite_scrolls=150,
                )
            )

            produtos = coletor.coletar()

            slug = criar_slug_categoria(
                categoria
            )

            nome_arquivo = (
                "mercado_livre/"
                f"{slug}.json"
            )

            coletor.salvar_json(
                produtos=produtos,
                nome_arquivo=nome_arquivo,
            )

            resultados[categoria] = len(
                produtos
            )

            print(
                f"\nCategoria concluída: "
                f"{categoria}"
            )

            print(
                f"Produtos únicos: "
                f"{len(produtos)}"
            )

            time.sleep(3.0)

    print("\n")
    print("=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)

    total = 0

    for categoria, quantidade in (
        resultados.items()
    ):
        total += quantidade

        print(
            f"{categoria}: "
            f"{quantidade} produtos"
        )

    print("-" * 70)
    print(
        f"Total coletado: "
        f"{total} produtos"
    )

    print(
        "Execução concluída em: "
        + datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )


if __name__ == "__main__":
    main()