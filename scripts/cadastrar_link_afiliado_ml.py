import argparse
import sys

from repositories.links_afiliados_mercado_livre_repository import (
    LinksAfiliadosMercadoLivreRepository
)


def criar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Cadastra um link afiliado do Mercado Livre "
            "no catálogo privado do projeto."
        )
    )

    parser.add_argument(
        "link_original",
        help=(
            "Link original do anúncio do Mercado Livre."
        )
    )

    parser.add_argument(
        "link_afiliado",
        help=(
            "Link meli.la gerado na Central "
            "de Afiliados."
        )
    )

    return parser.parse_args()


def executar() -> int:
    argumentos = criar_argumentos()

    repository = (
        LinksAfiliadosMercadoLivreRepository()
    )

    try:
        registro = repository.cadastrar(
            link_original=argumentos.link_original,
            link_afiliado=argumentos.link_afiliado
        )

    except ValueError as erro:
        print("=" * 80)
        print("CADASTRO NÃO REALIZADO")
        print(str(erro))
        print("=" * 80)

        return 1

    print("=" * 80)
    print("LINK AFILIADO CADASTRADO")
    print(f"Anúncio: {registro.item_id}")
    print(f"Link original: {registro.link_original}")
    print(f"Link afiliado: {registro.link_afiliado}")
    print(f"Atualizado em: {registro.atualizado_em}")
    print(
        "Total de links cadastrados: "
        f"{repository.quantidade()}"
    )
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(
        executar()
    )