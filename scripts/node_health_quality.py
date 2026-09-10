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


from services.infra.node_data_quality import (  # noqa: E402
    CADENCIA_NOMINAL_SEGUNDOS_PADRAO,
    analisar_qualidade_dados_node,
    salvar_qualidade_dados_node,
)
from services.infra.node_trend_analysis import (  # noqa: E402
    JANELA_BASELINE_MINUTOS_PADRAO,
    JANELA_RECENTE_MINUTOS_PADRAO,
)


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Analisa cobertura e qualidade " "dos dados do Node Health.")
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

    parser.add_argument(
        "--cadencia-segundos",
        type=float,
        default=(CADENCIA_NOMINAL_SEGUNDOS_PADRAO),
    )

    return parser.parse_args()


def main() -> int:
    argumentos = _argumentos()

    try:
        analise = analisar_qualidade_dados_node(
            janela_recente_minutos=(argumentos.recente_minutos),
            janela_baseline_minutos=(argumentos.baseline_minutos),
            cadencia_nominal_segundos=(argumentos.cadencia_segundos),
        )
    except ValueError as erro:
        print(
            f"ERRO={erro}",
            file=sys.stderr,
        )
        return 2

    caminho = salvar_qualidade_dados_node(analise)

    print(
        json.dumps(
            analise.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print(f"QUALIDADE_SALVA={caminho}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
