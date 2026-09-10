from pathlib import Path

from models.estado_node import EstadoNode
from services.infra.node_agent import (
    NodeHealthAgent,
)


def _estado():
    return EstadoNode(
        versao_schema=1,
        node_id="node-a1b2c3d4e5f6",
        coletado_em=("2026-09-10T10:00:00+00:00"),
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
        memoria_processos_projeto_bytes=100,
    )


def test_v110_agente_persiste_estado_temporal(
    tmp_path,
):
    estado = _estado()
    chamadas = []

    def persistir(
        sinais,
        *,
        caminho_estado,
        diretorio_historico,
    ):
        chamadas.append(
            (
                sinais,
                Path(caminho_estado),
                Path(diretorio_historico),
            )
        )

        return object()

    agente = NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado_atual.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=(lambda *, node_id: estado),
        analisar_historico=(lambda diretorio: "ANALISE"),
        salvar_analise=(lambda valor, caminho: Path(caminho)),
        analisar_tendencia=(lambda diretorio: "TENDENCIA"),
        salvar_tendencia=(lambda valor, caminho: Path(caminho)),
        analisar_qualidade=(lambda diretorio, *, cadencia_nominal_segundos: ("QUALIDADE")),
        salvar_qualidade=(lambda valor, caminho: Path(caminho)),
        analisar_sinais=(lambda *args: "SINAIS"),
        salvar_sinais=(lambda valor, caminho: Path(caminho)),
        persistir_estado_sinais=persistir,
    )

    resultado = agente.executar_ciclo()

    assert resultado is estado

    assert chamadas == [
        (
            "SINAIS",
            tmp_path / "sinais_estado_atual.json",
            tmp_path / "historico_sinais",
        )
    ]


def test_v110_falha_temporal_nao_quebra_coleta(
    tmp_path,
):
    estado = _estado()

    def persistir_falha(
        sinais,
        *,
        caminho_estado,
        diretorio_historico,
    ):
        del sinais
        del caminho_estado
        del diretorio_historico

        raise RuntimeError("falha proposital")

    agente = NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado_atual.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=(lambda *, node_id: estado),
        analisar_historico=(lambda diretorio: "ANALISE"),
        salvar_analise=(lambda valor, caminho: Path(caminho)),
        analisar_tendencia=(lambda diretorio: "TENDENCIA"),
        salvar_tendencia=(lambda valor, caminho: Path(caminho)),
        analisar_qualidade=(lambda diretorio, *, cadencia_nominal_segundos: ("QUALIDADE")),
        salvar_qualidade=(lambda valor, caminho: Path(caminho)),
        analisar_sinais=(lambda *args: "SINAIS"),
        salvar_sinais=(lambda valor, caminho: Path(caminho)),
        persistir_estado_sinais=(persistir_falha),
    )

    resultado = agente.executar_ciclo()

    assert resultado is estado

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()
