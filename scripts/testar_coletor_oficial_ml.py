from __future__ import annotations

from playwright.sync_api import sync_playwright

from scrapers.mercado_livre.coletor_produtos import (
    ColetorProdutosMercadoLivre,
)
from scrapers.mercado_livre.navegador import conectar_ao_chrome


def main() -> None:
    with sync_playwright() as playwright:
        _, _, pagina = conectar_ao_chrome(playwright)

        print("Conectado ao Chrome.")
        print(f"Página encontrada: {pagina.url}")

        coletor = ColetorProdutosMercadoLivre(
            pagina=pagina,
            categoria="Categoria atualmente selecionada",
            tempo_espera_scroll=2.5,
            tentativas_sem_crescimento=5,
            limite_scrolls=150,
        )

        produtos = coletor.coletar()

        caminho = coletor.salvar_json(
            produtos=produtos,
            nome_arquivo="produtos_categoria_atual.json",
        )

        print("\nResumo:")
        print(f"Produtos únicos: {len(produtos)}")
        print(f"Resultado: {caminho}")


if __name__ == "__main__":
    main()