import json

import pytest

from models.sinais_node import (
    AnaliseSinaisNode,
    SinalNode,
)
from services.infra.node_signal_state import (
    atualizar_estado_temporal_sinais,
    persistir_estado_temporal_sinais,
)


def _analise(
    referencia,
    codigos,
    *,
    node_id="node-a1b2c3d4e5f6",
):
    return AnaliseSinaisNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=referencia,
        servicos_continuos=(),
        dependencias_persistentes=(),
        workloads_intermitentes=(),
        sinais=tuple(
            SinalNode(
                codigo=codigo,
                origem="teste",
                titulo=codigo,
                descricao="teste",
                evidencias={
                    "codigo": codigo,
                },
            )
            for codigo in codigos
        ),
        supressoes=(),
    )


def _sinal(
    estado,
    codigo="sinal-a",
):
    return next(item for item in estado.sinais if item.codigo == codigo)


def test_retry_mesma_referencia_nao_incrementa():
    primeira = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        )
    )

    retry = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        ),
        primeira,
    )

    assert retry is primeira
    assert _sinal(retry).observacoes_consecutivas == 1
    assert _sinal(retry).observacoes_totais == 1


def test_retry_equivalente_com_offset_nao_incrementa():
    primeira = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        )
    )

    retry = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T07:00:00-03:00",
            ["sinal-a"],
        ),
        primeira,
    )

    assert retry is primeira
    assert _sinal(retry).observacoes_totais == 1


def test_retry_mesma_referencia_com_sinais_diferentes_falha():
    primeira = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        )
    )

    with pytest.raises(
        ValueError,
        match="conjunto de sinais diferente",
    ):
        atualizar_estado_temporal_sinais(
            _analise(
                "2026-09-10T10:00:00+00:00",
                ["sinal-b"],
            ),
            primeira,
        )


def test_referencia_mais_antiga_e_rejeitada():
    atual = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:05:00+00:00",
            ["sinal-a"],
        )
    )

    with pytest.raises(
        ValueError,
        match="fora de ordem",
    ):
        atualizar_estado_temporal_sinais(
            _analise(
                "2026-09-10T10:00:00+00:00",
                ["sinal-a"],
            ),
            atual,
        )


def test_retry_persistido_nao_duplica_historico(
    tmp_path,
):
    caminho_estado = tmp_path / "estado.json"

    diretorio = tmp_path / "historico"

    analise = _analise(
        "2026-09-10T10:00:00+00:00",
        ["sinal-a"],
    )

    primeiro = persistir_estado_temporal_sinais(
        analise,
        caminho_estado=caminho_estado,
        diretorio_historico=diretorio,
    )

    segundo = persistir_estado_temporal_sinais(
        analise,
        caminho_estado=caminho_estado,
        diretorio_historico=diretorio,
    )

    historico = diretorio / "2026-09-10.jsonl"

    linhas = historico.read_text(encoding="utf-8").splitlines()

    assert len(linhas) == 1
    assert _sinal(primeiro).observacoes_totais == 1
    assert _sinal(segundo).observacoes_totais == 1


def test_referencia_antiga_nao_muta_estado_ou_historico(
    tmp_path,
):
    caminho_estado = tmp_path / "estado.json"

    diretorio = tmp_path / "historico"

    persistir_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:05:00+00:00",
            ["sinal-a"],
        ),
        caminho_estado=caminho_estado,
        diretorio_historico=diretorio,
    )

    estado_antes = caminho_estado.read_bytes()

    historico = diretorio / "2026-09-10.jsonl"

    historico_antes = historico.read_bytes()

    with pytest.raises(
        ValueError,
        match="fora de ordem",
    ):
        persistir_estado_temporal_sinais(
            _analise(
                "2026-09-10T10:00:00+00:00",
                ["sinal-a"],
            ),
            caminho_estado=caminho_estado,
            diretorio_historico=diretorio,
        )

    assert caminho_estado.read_bytes() == estado_antes
    assert historico.read_bytes() == historico_antes


def test_referencia_nova_continua_incrementando(
    tmp_path,
):
    caminho_estado = tmp_path / "estado.json"

    diretorio = tmp_path / "historico"

    persistir_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        ),
        caminho_estado=caminho_estado,
        diretorio_historico=diretorio,
    )

    resultado = persistir_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:05:00+00:00",
            ["sinal-a"],
        ),
        caminho_estado=caminho_estado,
        diretorio_historico=diretorio,
    )

    sinal = _sinal(resultado)

    assert sinal.observacoes_consecutivas == 2
    assert sinal.observacoes_totais == 2

    historico = diretorio / "2026-09-10.jsonl"

    linhas = historico.read_text(encoding="utf-8").splitlines()

    assert len(linhas) == 2

    referencias = [json.loads(linha)["referencia_temporal"] for linha in linhas]

    assert referencias == [
        "2026-09-10T10:00:00+00:00",
        "2026-09-10T10:05:00+00:00",
    ]
