import json

import pytest

from services.infra.node_evidence_interpretation_state import (
    persistir_estado_interpretacao_evidencias_node,
)

NODE = "node-v121"


def _gravar(
    caminho,
    dados,
):
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho.write_text(
        json.dumps(dados),
        encoding="utf-8",
    )


def _interpretacao(
    referencia,
    codigos,
    *,
    node_id=NODE,
):
    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "quantidade_observacoes": len(codigos),
        "observacoes": [
            {
                "codigo": codigo,
                "categoria": "teste",
                "sujeito": codigo,
                "descricao": (f"Descricao {codigo}"),
                "dados": {
                    "valor": codigo,
                },
                "fontes": ["fonte.json"],
            }
            for codigo in codigos
        ],
    }


def _persistir(
    tmp_path,
    interpretacao,
):
    caminho_interpretacao = tmp_path / "interpretacao.json"

    _gravar(
        caminho_interpretacao,
        interpretacao,
    )

    return persistir_estado_interpretacao_evidencias_node(
        caminho_interpretacao,
        caminho_estado=(tmp_path / "estado.json"),
        diretorio_historico=(tmp_path / "historico"),
    )


def _por_codigo(
    estado,
):
    return {item.codigo: item for item in estado.observacoes}


def test_primeira_observacao_e_nova(
    tmp_path,
):
    estado = _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:00:00+00:00",
            ["a"],
        ),
    )

    item = _por_codigo(estado)["a"]

    assert item.observado_agora is True
    assert item.transicao_ultimo_ciclo == "novo"
    assert item.observacoes_consecutivas == 1
    assert item.observacoes_totais == 1


def test_observacao_continua_incrementa_contadores(
    tmp_path,
):
    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:00:00+00:00",
            ["a"],
        ),
    )

    estado = _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:05:00+00:00",
            ["a"],
        ),
    )

    item = _por_codigo(estado)["a"]

    assert item.transicao_ultimo_ciclo == "continua_observado"

    assert item.observacoes_consecutivas == 2
    assert item.observacoes_totais == 2


def test_observacao_pode_deixar_de_ser_observada(
    tmp_path,
):
    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:00:00+00:00",
            ["a"],
        ),
    )

    estado = _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:05:00+00:00",
            [],
        ),
    )

    item = _por_codigo(estado)["a"]

    assert item.observado_agora is False

    assert item.transicao_ultimo_ciclo == "deixou_de_ser_observado"

    assert item.ciclos_ausente_consecutivos == 1

    assert item.deixou_de_ser_observado_em == "2026-09-10T16:05:00+00:00"


def test_observacao_pode_continuar_ausente(
    tmp_path,
):
    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:00:00+00:00",
            ["a"],
        ),
    )

    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:05:00+00:00",
            [],
        ),
    )

    estado = _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:10:00+00:00",
            [],
        ),
    )

    item = _por_codigo(estado)["a"]

    assert item.transicao_ultimo_ciclo == "continua_nao_observado"

    assert item.ciclos_ausente_consecutivos == 2


def test_observacao_pode_reaparecer(
    tmp_path,
):
    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:00:00+00:00",
            ["a"],
        ),
    )

    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:05:00+00:00",
            [],
        ),
    )

    estado = _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:10:00+00:00",
            ["a"],
        ),
    )

    item = _por_codigo(estado)["a"]

    assert item.transicao_ultimo_ciclo == "reapareceu"
    assert item.observacoes_consecutivas == 1
    assert item.observacoes_totais == 2

    assert item.inicio_sequencia_atual == "2026-09-10T16:10:00+00:00"


def test_retry_mesma_referencia_e_idempotente(
    tmp_path,
):
    interpretacao = _interpretacao(
        "2026-09-10T16:00:00+00:00",
        ["a"],
    )

    primeiro = _persistir(
        tmp_path,
        interpretacao,
    )

    segundo = _persistir(
        tmp_path,
        interpretacao,
    )

    assert primeiro.para_dict() == segundo.para_dict()

    historico = tmp_path / "historico" / "2026-09-10.jsonl"

    linhas = historico.read_text(encoding="utf-8").splitlines()

    assert len(linhas) == 1


def test_mesmo_instante_com_offset_e_idempotente(
    tmp_path,
):
    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:00:00+00:00",
            ["a"],
        ),
    )

    estado = _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T13:00:00-03:00",
            ["a"],
        ),
    )

    item = _por_codigo(estado)["a"]

    assert item.observacoes_totais == 1

    historico = tmp_path / "historico" / "2026-09-10.jsonl"

    assert len(historico.read_text(encoding="utf-8").splitlines()) == 1


def test_mesmo_instante_com_conteudo_diferente_e_rejeitado(
    tmp_path,
):
    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:00:00+00:00",
            ["a"],
        ),
    )

    with pytest.raises(
        ValueError,
        match="mesmo instante",
    ):
        _persistir(
            tmp_path,
            _interpretacao(
                "2026-09-10T16:00:00+00:00",
                ["b"],
            ),
        )


def test_referencia_antiga_e_rejeitada(
    tmp_path,
):
    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:05:00+00:00",
            ["a"],
        ),
    )

    with pytest.raises(
        ValueError,
        match="mais antiga",
    ):
        _persistir(
            tmp_path,
            _interpretacao(
                "2026-09-10T16:00:00+00:00",
                ["a"],
            ),
        )


def test_mudanca_de_node_reinicia_estado_temporal(
    tmp_path,
):
    _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:00:00+00:00",
            ["a"],
            node_id="node-antigo",
        ),
    )

    estado = _persistir(
        tmp_path,
        _interpretacao(
            "2026-09-10T16:05:00+00:00",
            ["b"],
            node_id="node-novo",
        ),
    )

    assert estado.node_id == "node-novo"

    assert {item.codigo for item in estado.observacoes} == {"b"}

    assert estado.observacoes[0].transicao_ultimo_ciclo == "novo"
