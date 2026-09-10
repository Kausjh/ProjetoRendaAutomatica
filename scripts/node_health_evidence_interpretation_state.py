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


from services.infra.node_evidence_interpretation_state import (  # noqa: E402
    persistir_estado_interpretacao_evidencias_node,
)


def main() -> int:
    try:
        estado = persistir_estado_interpretacao_evidencias_node()

    except ValueError as erro:
        print(
            f"ERRO={erro}",
            file=sys.stderr,
        )

        return 2

    print(
        json.dumps(
            estado.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
