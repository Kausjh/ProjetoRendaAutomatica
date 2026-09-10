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


def _salvar(
    chamadas,
    nome,
):
    def executar(
        valor,
        caminho,
    ):
        chamadas.append(
            (
                nome,
                valor,
                Path(caminho),
            )
        )

        return Path(caminho)

    return executar


def test_v19_sinais_sao_atualizados_depois_dos_derivados(
    tmp_path,
):
    estado = _estado()
    chamadas = []

    historico = tmp_path / "historico"

    def analisar_historico(
        diretorio,
    ):
        chamadas.append(
            (
                "analisar_historico",
                Path(diretorio),
            )
        )

        return "ANALISE"

    def analisar_tendencia(
        diretorio,
    ):
        chamadas.append(
            (
                "analisar_tendencia",
                Path(diretorio),
            )
        )

        return "TENDENCIA"

    def analisar_qualidade(
        diretorio,
        *,
        cadencia_nominal_segundos,
    ):
        chamadas.append(
            (
                "analisar_qualidade",
                Path(diretorio),
                cadencia_nominal_segundos,
            )
        )

        return "QUALIDADE"

    def analisar_sinais(
        caminho_estado,
        caminho_tendencia,
        caminho_qualidade,
        diretorio,
    ):
        chamadas.append(
            (
                "analisar_sinais",
                Path(caminho_estado),
                Path(caminho_tendencia),
                Path(caminho_qualidade),
                Path(diretorio),
            )
        )

        return "SINAIS"

    agente = NodeHealthAgent(
        intervalo_segundos=123,
        caminho_estado=(tmp_path / "estado_atual.json"),
        diretorio_historico=historico,
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=(lambda *, node_id: estado),
        salvar_estado=(lambda valor, caminho: (Path(caminho))),
        analisar_historico=(analisar_historico),
        salvar_analise=_salvar(
            chamadas,
            "salvar_analise",
        ),
        analisar_tendencia=(analisar_tendencia),
        salvar_tendencia=_salvar(
            chamadas,
            "salvar_tendencia",
        ),
        analisar_qualidade=(analisar_qualidade),
        salvar_qualidade=_salvar(
            chamadas,
            "salvar_qualidade",
        ),
        analisar_sinais=(analisar_sinais),
        salvar_sinais=_salvar(
            chamadas,
            "salvar_sinais",
        ),
    )

    resultado = agente.executar_ciclo()

    assert resultado is estado

    assert agente.caminho_sinais == (tmp_path / "sinais_atual.json")

    assert chamadas == [
        (
            "analisar_historico",
            historico,
        ),
        (
            "salvar_analise",
            "ANALISE",
            tmp_path / "analise_atual.json",
        ),
        (
            "analisar_tendencia",
            historico,
        ),
        (
            "salvar_tendencia",
            "TENDENCIA",
            tmp_path / "tendencia_atual.json",
        ),
        (
            "analisar_qualidade",
            historico,
            123.0,
        ),
        (
            "salvar_qualidade",
            "QUALIDADE",
            tmp_path / "qualidade_atual.json",
        ),
        (
            "analisar_sinais",
            tmp_path / "estado_atual.json",
            tmp_path / "tendencia_atual.json",
            tmp_path / "qualidade_atual.json",
            historico,
        ),
        (
            "salvar_sinais",
            "SINAIS",
            tmp_path / "sinais_atual.json",
        ),
    ]


def test_v19_nao_gera_sinal_com_tendencia_desatualizada(
    tmp_path,
):
    estado = _estado()
    chamadas = []

    def tendencia_falha(
        diretorio,
    ):
        del diretorio

        chamadas.append("tendencia")

        raise RuntimeError("falha proposital")

    def qualidade_ok(
        diretorio,
        *,
        cadencia_nominal_segundos,
    ):
        del diretorio
        del cadencia_nominal_segundos

        chamadas.append("qualidade")

        return "QUALIDADE"

    def sinais_proibidos(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        raise AssertionError("Sinais nao deveriam " "ser analisados.")

    agente = NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=(lambda *, node_id: estado),
        salvar_estado=(lambda valor, caminho: (Path(caminho))),
        analisar_historico=(lambda diretorio: "ANALISE"),
        salvar_analise=(lambda valor, caminho: (Path(caminho))),
        analisar_tendencia=(tendencia_falha),
        salvar_tendencia=(lambda valor, caminho: (Path(caminho))),
        analisar_qualidade=(qualidade_ok),
        salvar_qualidade=(lambda valor, caminho: (Path(caminho))),
        analisar_sinais=(sinais_proibidos),
    )

    resultado = agente.executar_ciclo()

    assert resultado is estado

    assert chamadas == [
        "tendencia",
        "qualidade",
    ]


def test_v19_falha_de_sinais_nao_quebra_coleta(
    tmp_path,
):
    estado = _estado()
    chamadas = []

    def sinais_falham(
        caminho_estado,
        caminho_tendencia,
        caminho_qualidade,
        diretorio_historico,
    ):
        del caminho_estado
        del caminho_tendencia
        del caminho_qualidade
        del diretorio_historico

        chamadas.append("sinais")

        raise RuntimeError("falha proposital")

    agente = NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=(lambda *, node_id: estado),
        salvar_estado=(lambda valor, caminho: (Path(caminho))),
        analisar_historico=(lambda diretorio: "ANALISE"),
        salvar_analise=(lambda valor, caminho: (Path(caminho))),
        analisar_tendencia=(lambda diretorio: "TENDENCIA"),
        salvar_tendencia=(lambda valor, caminho: (Path(caminho))),
        analisar_qualidade=(lambda diretorio, *, cadencia_nominal_segundos: ("QUALIDADE")),
        salvar_qualidade=(lambda valor, caminho: (Path(caminho))),
        analisar_sinais=sinais_falham,
    )

    resultado = agente.executar_ciclo()

    assert resultado is estado

    assert chamadas == ["sinais"]

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()


def test_v19_defaults_geram_cadeia_completa(
    tmp_path,
):
    estado = _estado()

    agente = NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado_atual.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: ("node-a1b2c3d4e5f6"),
        capturar_estado=(lambda *, node_id: estado),
    )

    resultado = agente.executar_ciclo()

    assert resultado is estado

    for nome in (
        "estado_atual.json",
        "analise_atual.json",
        "tendencia_atual.json",
        "qualidade_atual.json",
        "sinais_atual.json",
    ):
        assert (tmp_path / nome).exists()

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()
