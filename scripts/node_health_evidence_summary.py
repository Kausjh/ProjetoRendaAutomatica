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


from services.infra.node_evidence_summary import (  # noqa: E402
    gerar_resumo_evidencias_node,
    salvar_resumo_evidencias_node,
)


def main() -> int:
    try:
        resumo = gerar_resumo_evidencias_node()

    except ValueError as erro:
        print(
            f"ERRO={erro}",
            file=sys.stderr,
        )

        return 2

    caminho = salvar_resumo_evidencias_node(resumo)

    print(
        json.dumps(
            resumo.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print("RESUMO_EVIDENCIAS_SALVO=" f"{caminho}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
