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


from services.infra.node_trend_analysis import (  # noqa: E402
    JANELA_BASELINE_MINUTOS_PADRAO,
    JANELA_RECENTE_MINUTOS_PADRAO,
    analisar_tendencia_node,
    salvar_tendencia_node,
)


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Compara janela recente " "do Node Health contra baseline.")
    )

    parser.add_argument(
        "--recente-minutos",
        type=int,
        default=(JANELA_RECENTE_MINUTOS_PADRAO),
    )

    parser.add_argument(
        "--baseline-minutos",
        type=int,
        default=(JANELA_BASELINE_MINUTOS_PADRAO),
    )

    return parser.parse_args()


def main() -> int:
    argumentos = _argumentos()

    try:
        analise = analisar_tendencia_node(
            janela_recente_minutos=(argumentos.recente_minutos),
            janela_baseline_minutos=(argumentos.baseline_minutos),
        )
    except ValueError as erro:
        print(
            f"ERRO={erro}",
            file=sys.stderr,
        )
        return 2

    caminho = salvar_tendencia_node(analise)

    print(
        json.dumps(
            analise.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print(f"TENDENCIA_SALVA={caminho}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
