import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parent.parent

if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))


from affiliates.registro_afiliadores import criar_gerador_link_afiliado  # noqa: E402
from config.configuracoes import Configuracoes  # noqa: E402

LINKS_PADRAO = [
    ("https://books.toscrape.com/" "catalogue/teste/index.html"),
    "https://exemplo.com/produto",
]


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Testa quais afiliadores processam uma lista " "de links sem publicar no Telegram."
        )
    )

    parser.add_argument(
        "links",
        nargs="*",
        help=("Links que devem ser processados. " "Quando omitidos, links de exemplo são usados."),
    )

    return parser


def exibir_resultado(
    indice: int, link_original: str, afiliador: str, link_publicacao: str, foi_transformado: bool
) -> None:
    print("=" * 80)

    print(f"Teste {indice}")

    print(f"Link original: {link_original}")

    print(f"Afiliador: {afiliador}")

    print("Transformado: " + ("sim" if foi_transformado else "não"))

    print(f"Link de publicação: {link_publicacao}")


def main() -> None:
    load_dotenv(dotenv_path=RAIZ_PROJETO / ".env")

    argumentos = criar_parser().parse_args()

    links = argumentos.links if argumentos.links else LINKS_PADRAO

    configuracoes = Configuracoes()

    gerador = criar_gerador_link_afiliado(configuracoes)

    quantidade_transformada = 0
    quantidade_fallback = 0

    for indice, link in enumerate(links, start=1):
        resultado = gerador.gerar(link)

        if resultado.foi_transformado:
            quantidade_transformada += 1

        if resultado.afiliador_utilizado == "Fallback":
            quantidade_fallback += 1

        exibir_resultado(
            indice=indice,
            link_original=resultado.link_original,
            afiliador=resultado.afiliador_utilizado,
            link_publicacao=resultado.link_publicacao,
            foi_transformado=resultado.foi_transformado,
        )

    print("=" * 80)

    print("Resumo da auditoria")

    print(f"Links processados: {len(links)}")

    print(f"Links transformados: {quantidade_transformada}")

    print(f"Links no fallback: {quantidade_fallback}")

    print("=" * 80)


if __name__ == "__main__":
    main()
