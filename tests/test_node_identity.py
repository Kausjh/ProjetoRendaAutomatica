import json

import pytest

from services.infra import node_identity


def test_cria_identidade_anonima_persistente(
    monkeypatch,
    tmp_path,
):
    caminho = tmp_path / "node_identity.json"

    monkeypatch.setattr(
        node_identity.secrets,
        "token_hex",
        lambda quantidade: "a1b2c3d4e5f6",
    )

    primeiro = node_identity.obter_ou_criar_node_id(caminho)

    segundo = node_identity.obter_ou_criar_node_id(caminho)

    assert primeiro == ("node-a1b2c3d4e5f6")

    assert segundo == primeiro

    dados = json.loads(caminho.read_text(encoding="utf-8"))

    assert dados == {
        "versao_schema": 1,
        "node_id": primeiro,
    }


def test_identidade_existente_invalida_nao_e_trocada_silenciosamente(
    tmp_path,
):
    caminho = tmp_path / "node_identity.json"

    caminho.write_text(
        json.dumps(
            {
                "versao_schema": 1,
                "node_id": ("nome-pessoal-do-pc"),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="formato invalido",
    ):
        (node_identity.obter_ou_criar_node_id(caminho))
