# 63.8738, -149.7525

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from services.infra.node_signal_history_analysis import (  # noqa: E402
    analisar_historico_sinais_node,
    salvar_analise_historico_sinais_node,
)


def main() -> int:
    try:
        analise = analisar_historico_sinais_node()

    except ValueError as erro:
        print(
            f"ERRO={erro}",
            file=sys.stderr,
        )

        return 2

    caminho = salvar_analise_historico_sinais_node(analise)

    print(
        json.dumps(
            analise.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print("ANALISE_HISTORICO_SINAIS_SALVA=" f"{caminho}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
