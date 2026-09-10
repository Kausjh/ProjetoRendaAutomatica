# 63.8738, -149.7525

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path
from typing import Final

DIRETORIO_PROJETO: Final = Path(__file__).resolve().parents[2]

CAMINHO_IDENTIDADE_PADRAO: Final = DIRETORIO_PROJETO / "data" / "node" / "node_identity.json"

PADRAO_NODE_ID: Final = re.compile(r"^node-[a-f0-9]{12}$")


def _validar_node_id(node_id: object) -> str:
    if not isinstance(node_id, str):
        raise ValueError("Identidade do node invalida.")

    node_id = node_id.strip().lower()

    if not PADRAO_NODE_ID.fullmatch(node_id):
        raise ValueError("Identidade do node possui formato invalido.")

    return node_id


def _ler_node_id(caminho: Path) -> str:
    try:
        dados = json.loads(
            caminho.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as erro:
        raise ValueError("Nao foi possivel ler a identidade " "persistente do node.") from erro

    if not isinstance(dados, dict):
        raise ValueError("Arquivo de identidade do node invalido.")

    return _validar_node_id(dados.get("node_id"))


def obter_ou_criar_node_id(
    caminho: str | Path = CAMINHO_IDENTIDADE_PADRAO,
) -> str:
    caminho = Path(caminho)

    if caminho.exists():
        return _ler_node_id(caminho)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    node_id = "node-" + secrets.token_hex(6)

    dados = {
        "versao_schema": 1,
        "node_id": node_id,
    }

    try:
        with caminho.open(
            "x",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                dados,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )
            arquivo.write("\n")

    except FileExistsError:
        # Outra instancia pode ter criado a identidade
        # exatamente entre exists() e open("x").
        return _ler_node_id(caminho)

    return node_id
