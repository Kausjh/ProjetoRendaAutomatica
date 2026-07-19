import argparse
import sys

from repositories.links_afiliados_mercado_livre_repository import (
    LinksAfiliadosMercadoLivreRepository
)


def criar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Consulta o catálogo privado de links "
            "afiliados do Mercado Livre."
        )
    )

    parser.add_argument(
        "consulta",
        help=(
            "Link original do produto ou código "
            "do anúncio, como MLB4577516683."
        )
    )

    return parser.parse_args()


def executar() -> int:
    argumentos = criar_argumentos()

    repository = (
        LinksAfiliadosMercadoLivreRepository()
    )

    consulta = argumentos.consulta.strip()

    try:
        if consulta.upper().startswith("MLB"):
            registro = repository.buscar_por_item_id(
                consulta
            )

        else:
            registro = repository.buscar_por_link(
                consulta
            )

    except ValueError as erro:
        print("=" * 80)
        print("CONSULTA INVÁLIDA")
        print(str(erro))
        print("=" * 80)

        return 1

    print("=" * 80)

    if registro is None:
        print("LINK AFILIADO NÃO ENCONTRADO")
        print(f"Consulta: {consulta}")
        print(
            "Este anúncio ainda não está "
            "pronto para monetização."
        )
        print("=" * 80)

        return 2

    print("LINK AFILIADO ENCONTRADO")
    print(f"Anúncio: {registro.item_id}")
    print(f"Link original: {registro.link_original}")
    print(f"Link afiliado: {registro.link_afiliado}")
    print(f"Atualizado em: {registro.atualizado_em}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(
        executar()
    )