import json

import pytest

from models.estado_node import (
    EstadoNode,
)
from services.infra.node_agent import (
    NodeHealthAgent,
)


def _estado(
    *,
    coletado_em=("2026-09-10T00:00:00+00:00"),
):
    return EstadoNode(
        versao_schema=1,
        node_id="node-a1b2c3d4e5f6",
        coletado_em=coletado_em,
        sistema="Windows",
        versao_sistema="10",
        arquitetura="AMD64",
        uptime_segundos=100.0,
        cpu_percentual=20.0,
        memoria_total_bytes=1000,
        memoria_disponivel_bytes=500,
        memoria_uso_percentual=50.0,
        disco_total_bytes=2000,
        disco_livre_bytes=1000,
        disco_uso_percentual=50.0,
        quantidade_processos_projeto=3,
        servicos=(),
    )


def test_executar_ciclo_salva_estado_e_historico(
    tmp_path,
):
    salvo = []

    estado = _estado()

    agente = NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado_atual.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=(lambda *, node_id: estado),
        salvar_estado=(lambda valor, caminho: (salvo.append((valor, caminho)) or caminho)),
    )

    resultado = agente.executar_ciclo()

    assert resultado is estado

    assert salvo == [
        (
            estado,
            tmp_path / "estado_atual.json",
        )
    ]

    historico = tmp_path / "historico" / "2026-09-10.jsonl"

    assert historico.exists()

    linhas = historico.read_text(encoding="utf-8").splitlines()

    assert len(linhas) == 1

    dados = json.loads(linhas[0])

    assert dados["node_id"] == ("node-a1b2c3d4e5f6")

    assert dados["memoria_uso_percentual"] == 50.0


def test_historico_acumula_amostras(
    tmp_path,
):
    estados = iter(
        (
            _estado(coletado_em=("2026-09-10" "T00:00:00+00:00")),
            _estado(coletado_em=("2026-09-10" "T00:05:00+00:00")),
        )
    )

    agente = NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=(lambda *, node_id: next(estados)),
        salvar_estado=(lambda estado, caminho: caminho),
    )

    agente.executar_ciclo()
    agente.executar_ciclo()

    historico = tmp_path / "historico" / "2026-09-10.jsonl"

    linhas = historico.read_text(encoding="utf-8").splitlines()

    assert len(linhas) == 2


def test_historico_separa_dias(
    tmp_path,
):
    estados = iter(
        (
            _estado(coletado_em=("2026-09-10" "T23:59:00+00:00")),
            _estado(coletado_em=("2026-09-11" "T00:04:00+00:00")),
        )
    )

    agente = NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=(lambda *, node_id: next(estados)),
        salvar_estado=(lambda estado, caminho: caminho),
    )

    agente.executar_ciclo()
    agente.executar_ciclo()

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()

    assert (tmp_path / "historico" / "2026-09-11.jsonl").exists()


def test_agente_pode_executar_numero_finito_de_ciclos(
    tmp_path,
):
    contador = {
        "valor": 0,
    }

    def capturar(*, node_id):
        contador["valor"] += 1
        return _estado()

    agente = NodeHealthAgent(
        intervalo_segundos=0.001,
        caminho_estado=(tmp_path / "estado.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=capturar,
        salvar_estado=(lambda estado, caminho: caminho),
    )

    ciclos = agente.executar(maximo_ciclos=2)

    assert ciclos == 2
    assert contador["valor"] == 2


def test_intervalo_invalido_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="maior que zero",
    ):
        NodeHealthAgent(
            intervalo_segundos=0,
            caminho_estado=(tmp_path / "estado.json"),
            diretorio_historico=(tmp_path / "historico"),
        )


def test_maximo_ciclos_invalido_e_rejeitado(
    tmp_path,
):
    agente = NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado.json"),
        diretorio_historico=(tmp_path / "historico"),
    )

    with pytest.raises(
        ValueError,
        match="maior que zero",
    ):
        agente.executar(maximo_ciclos=0)
