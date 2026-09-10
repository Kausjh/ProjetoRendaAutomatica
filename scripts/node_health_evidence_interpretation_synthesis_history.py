# 63.8738, -149.7525

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from services.infra.node_evidence_interpretation_synthesis_history import (  # noqa: E402
    persistir_sintese_evidencias_interpretacoes_node,
)


def main() -> int:
    try:
        resultado = persistir_sintese_evidencias_interpretacoes_node()

    except ValueError as erro:
        print(
            f"ERRO={erro}",
            file=sys.stderr,
        )

        return 2

    print(f"NODE_ID={resultado.node_id}")

    print("REFERENCIA=" f"{resultado.referencia_temporal}")

    print("REGISTRO_ADICIONADO=" f"{resultado.registro_adicionado}")

    print("REGISTROS_VALIDOS_NODE=" f"{resultado.quantidade_registros_validos_node}")

    print("HISTORICO_SINTESE=" f"{resultado.caminho_historico}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
