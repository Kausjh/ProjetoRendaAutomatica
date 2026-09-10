import json

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
    sinais = tuple(
        SinalNode(
            codigo=codigo,
            origem="teste",
            titulo=codigo,
            descricao="teste",
            evidencias={
                "valor": codigo,
            },
        )
        for codigo in codigos
    )

    return AnaliseSinaisNode(
        versao_schema=1,
        node_id=node_id,
        referencia_temporal=referencia,
        servicos_continuos=(),
        dependencias_persistentes=(),
        workloads_intermitentes=(),
        sinais=sinais,
        supressoes=(),
    )


def _obter(
    estado,
    codigo,
):
    return next(sinal for sinal in estado.sinais if sinal.codigo == codigo)


def test_sinal_novo():
    estado = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        )
    )

    sinal = _obter(
        estado,
        "sinal-a",
    )

    assert sinal.observado_agora is True
    assert sinal.observacoes_consecutivas == 1
    assert sinal.observacoes_totais == 1
    assert sinal.ciclos_ausente_consecutivos == 0
    assert sinal.transicao_ultimo_ciclo == "novo"


def test_sinal_continua():
    primeiro = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        )
    )

    segundo = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:05:00+00:00",
            ["sinal-a"],
        ),
        primeiro,
    )

    sinal = _obter(
        segundo,
        "sinal-a",
    )

    assert sinal.observacoes_consecutivas == 2
    assert sinal.observacoes_totais == 2
    assert sinal.inicio_sequencia_atual == "2026-09-10T10:00:00+00:00"
    assert sinal.transicao_ultimo_ciclo == "continua_observado"


def test_sinal_desaparece_sem_ser_apagado():
    primeiro = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        )
    )

    segundo = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:05:00+00:00",
            [],
        ),
        primeiro,
    )

    sinal = _obter(
        segundo,
        "sinal-a",
    )

    assert sinal.observado_agora is False
    assert sinal.observacoes_consecutivas == 0
    assert sinal.observacoes_totais == 1
    assert sinal.ciclos_ausente_consecutivos == 1

    assert sinal.deixou_de_ser_observado_em == "2026-09-10T10:05:00+00:00"

    assert sinal.transicao_ultimo_ciclo == "deixou_de_ser_observado"


def test_sinal_reaparece():
    primeiro = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        )
    )

    segundo = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:05:00+00:00",
            [],
        ),
        primeiro,
    )

    terceiro = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:10:00+00:00",
            ["sinal-a"],
        ),
        segundo,
    )

    sinal = _obter(
        terceiro,
        "sinal-a",
    )

    assert sinal.observado_agora is True
    assert sinal.observacoes_consecutivas == 1
    assert sinal.observacoes_totais == 2

    assert sinal.primeira_observacao == "2026-09-10T10:00:00+00:00"

    assert sinal.inicio_sequencia_atual == "2026-09-10T10:10:00+00:00"

    assert sinal.transicao_ultimo_ciclo == "reapareceu"


def test_node_id_diferente_reinicia_estado():
    antigo = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
            node_id="node-antigo",
        )
    )

    novo = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:05:00+00:00",
            ["sinal-a"],
            node_id="node-novo",
        ),
        antigo,
    )

    sinal = _obter(
        novo,
        "sinal-a",
    )

    assert novo.node_id == "node-novo"
    assert sinal.observacoes_totais == 1
    assert sinal.transicao_ultimo_ciclo == "novo"


def test_persistencia_salva_estado_e_historico(
    tmp_path,
):
    caminho_estado = tmp_path / "sinais_estado_atual.json"

    diretorio = tmp_path / "historico_sinais"

    resultado = persistir_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        ),
        caminho_estado=caminho_estado,
        diretorio_historico=diretorio,
    )

    assert resultado.sinais
    assert caminho_estado.exists()

    historico = diretorio / "2026-09-10.jsonl"

    assert historico.exists()

    linhas = historico.read_text(encoding="utf-8").splitlines()

    assert len(linhas) == 1

    registro = json.loads(linhas[0])

    assert registro["sinais"][0]["transicao_ultimo_ciclo"] == "novo"


def test_sem_politica_operacional():
    estado = atualizar_estado_temporal_sinais(
        _analise(
            "2026-09-10T10:00:00+00:00",
            ["sinal-a"],
        )
    )

    texto = json.dumps(estado.para_dict())

    for termo in (
        "status_saude",
        "precisa_reiniciar",
        "reboot_recomendado",
        "acao_recomendada",
        "saudavel",
        "degradado",
        "critico",
    ):
        assert termo not in texto
