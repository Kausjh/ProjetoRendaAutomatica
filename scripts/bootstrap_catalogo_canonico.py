from __future__ import annotations

import argparse
import json

from services.bootstrap_catalogo_canonico_service import (
    BootstrapCatalogoCanonicoService,
)


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap explicito do Canonical Catalog " "a partir da fila e do historico da fila."
        )
    )

    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument(
        "--simular",
        action="store_true",
        help=(
            "Executa o bootstrap em uma copia temporaria " "do catalogo, sem alterar o banco real."
        ),
    )
    modo.add_argument(
        "--executar",
        action="store_true",
        help=("Executa o bootstrap no Canonical Catalog real."),
    )

    parser.add_argument(
        "--fila",
        default="database/fila_publicacao.sqlite3",
    )
    parser.add_argument(
        "--catalogo",
        default="database/catalogo_canonico.sqlite3",
    )
    parser.add_argument(
        "--confianca-minima",
        type=float,
        default=90.0,
    )

    return parser


def main() -> int:
    args = criar_parser().parse_args()

    service = BootstrapCatalogoCanonicoService(
        caminho_fila=args.fila,
        caminho_catalogo=args.catalogo,
        confianca_minima=args.confianca_minima,
    )

    if args.simular:
        resultado = service.simular()
    else:
        resultado = service.executar()

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
