# 63.8738, -149.7525

from __future__ import annotations

import json
import sys
from pathlib import Path

DIRETORIO_PROJETO = Path(__file__).resolve().parents[1]

if str(DIRETORIO_PROJETO) not in sys.path:
    sys.path.insert(
        0,
        str(DIRETORIO_PROJETO),
    )


from services.infra.node_health import (  # noqa: E402
    capturar_estado_node,
    salvar_estado_node,
)
from services.infra.node_identity import (  # noqa: E402
    obter_ou_criar_node_id,
)


def main() -> int:
    node_id = obter_ou_criar_node_id()

    estado = capturar_estado_node(
        node_id=node_id,
    )

    caminho = salvar_estado_node(estado)

    print(
        json.dumps(
            estado.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(f"SNAPSHOT_SALVO={caminho}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
