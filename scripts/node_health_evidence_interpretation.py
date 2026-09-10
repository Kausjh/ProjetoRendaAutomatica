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


from services.infra.node_evidence_interpretation import (  # noqa: E402
    interpretar_evidencias_node,
    salvar_interpretacao_evidencias_node,
)


def main() -> int:
    try:
        interpretacao = interpretar_evidencias_node()

    except ValueError as erro:
        print(
            f"ERRO={erro}",
            file=sys.stderr,
        )

        return 2

    caminho = salvar_interpretacao_evidencias_node(interpretacao)

    print(
        json.dumps(
            interpretacao.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print("INTERPRETACAO_EVIDENCIAS_SALVA=" f"{caminho}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
