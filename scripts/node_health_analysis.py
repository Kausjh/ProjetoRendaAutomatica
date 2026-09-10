# 63.8738, -149.7525

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from services.infra.node_history_analysis import (  # noqa: E402
    CAMINHO_ANALISE_PADRAO,
    MAXIMO_AMOSTRAS_PADRAO,
    MAXIMO_ARQUIVOS_PADRAO,
    analisar_historico_node,
    salvar_analise_node,
)


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=("Analisa o historico local " "do Node Health."))

    parser.add_argument(
        "--dias",
        type=int,
        default=(MAXIMO_ARQUIVOS_PADRAO),
    )

    parser.add_argument(
        "--amostras",
        type=int,
        default=(MAXIMO_AMOSTRAS_PADRAO),
    )

    return parser.parse_args()


def main() -> int:
    argumentos = _argumentos()

    try:
        analise = analisar_historico_node(
            maximo_arquivos=(argumentos.dias),
            maximo_amostras=(argumentos.amostras),
        )
    except ValueError as erro:
        print(
            f"ERRO={erro}",
            file=sys.stderr,
        )
        return 2

    caminho = salvar_analise_node(analise)

    print(
        json.dumps(
            analise.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print(f"ANALISE_SALVA={caminho}")

    assert caminho == (CAMINHO_ANALISE_PADRAO)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
