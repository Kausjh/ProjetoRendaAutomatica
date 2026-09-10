from pathlib import Path

import services.infra.node_agent as node_agent_module
from services.infra.node_agent import NodeHealthAgent


def _agente(
    tmp_path,
):
    agente = object.__new__(NodeHealthAgent)

    agente.caminho_estado = tmp_path / "estado_atual.json"

    agente.intervalo_segundos = 300

    return agente


def _preparar(
    monkeypatch,
    *,
    gerar_resumo=None,
    salvar_resumo=None,
    analisar_qualidade=None,
    salvar_qualidade=None,
):
    monkeypatch.setattr(
        node_agent_module,
        "gerar_resumo_temporal_interpretacoes_node",
        (gerar_resumo if gerar_resumo is not None else lambda *args: "RESUMO"),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_resumo_temporal_interpretacoes_node",
        (salvar_resumo if salvar_resumo is not None else lambda resumo, caminho: Path(caminho)),
    )

    monkeypatch.setattr(
        node_agent_module,
        "analisar_qualidade_temporal_interpretacoes_node",
        (
            analisar_qualidade
            if analisar_qualidade is not None
            else lambda *args, **kwargs: "QUALIDADE"
        ),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_qualidade_temporal_interpretacoes_node",
        (
            salvar_qualidade
            if salvar_qualidade is not None
            else lambda qualidade, caminho: Path(caminho)
        ),
    )


def test_v128_qualidade_roda_depois_do_resumo_salvo(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def gerar_resumo(
        *args,
    ):
        del args
        chamadas.append("gerar_resumo")
        return "RESUMO"

    def salvar_resumo(
        resumo,
        caminho,
    ):
        del resumo
        del caminho
        chamadas.append("salvar_resumo")
        return Path("resumo.json")

    def analisar_qualidade(
        *args,
        **kwargs,
    ):
        del args
        del kwargs
        chamadas.append("analisar_qualidade")
        return "QUALIDADE"

    def salvar_qualidade(
        qualidade,
        caminho,
    ):
        del qualidade
        del caminho
        chamadas.append("salvar_qualidade")
        return Path("qualidade.json")

    _preparar(
        monkeypatch,
        gerar_resumo=gerar_resumo,
        salvar_resumo=salvar_resumo,
        analisar_qualidade=analisar_qualidade,
        salvar_qualidade=salvar_qualidade,
    )

    _agente(tmp_path)._atualizar_resumo_temporal_interpretacoes(
        tmp_path / "interpretacao_estado_atual.json",
        tmp_path / "analise_historico_interpretacoes_atual.json",
    )

    assert chamadas == [
        "gerar_resumo",
        "salvar_resumo",
        "analisar_qualidade",
        "salvar_qualidade",
    ]


def test_v128_qualidade_recebe_caminhos_e_cadencia_corretos(
    tmp_path,
    monkeypatch,
):
    recebido = {}

    def analisar(
        caminho_resumo,
        diretorio_historico,
        *,
        cadencia_nominal_segundos,
    ):
        recebido["resumo"] = Path(caminho_resumo)

        recebido["historico"] = Path(diretorio_historico)

        recebido["cadencia"] = cadencia_nominal_segundos

        return "QUALIDADE"

    def salvar(
        qualidade,
        caminho,
    ):
        del qualidade

        recebido["saida"] = Path(caminho)

        return Path(caminho)

    _preparar(
        monkeypatch,
        analisar_qualidade=analisar,
        salvar_qualidade=salvar,
    )

    _agente(tmp_path)._atualizar_resumo_temporal_interpretacoes(
        tmp_path / "interpretacao_estado_atual.json",
        tmp_path / "analise_historico_interpretacoes_atual.json",
    )

    assert recebido == {
        "resumo": (tmp_path / "resumo_temporal_interpretacoes_atual.json"),
        "historico": (tmp_path / "historico_interpretacoes"),
        "cadencia": 300,
        "saida": (tmp_path / "qualidade_temporal_interpretacoes_atual.json"),
    }


def test_v128_falha_gerar_resumo_suprime_qualidade(
    tmp_path,
    monkeypatch,
):
    def gerar_falha(
        *args,
    ):
        del args
        raise RuntimeError("falha proposital")

    def qualidade_proibida(
        *args,
        **kwargs,
    ):
        del args
        del kwargs
        raise AssertionError("Qualidade nao deveria rodar.")

    _preparar(
        monkeypatch,
        gerar_resumo=gerar_falha,
        analisar_qualidade=qualidade_proibida,
    )

    _agente(tmp_path)._atualizar_resumo_temporal_interpretacoes(
        tmp_path / "interpretacao_estado_atual.json",
        tmp_path / "analise_historico_interpretacoes_atual.json",
    )


def test_v128_falha_salvar_resumo_suprime_qualidade(
    tmp_path,
    monkeypatch,
):
    def salvar_resumo_falha(
        resumo,
        caminho,
    ):
        del resumo
        del caminho
        raise RuntimeError("falha proposital")

    def qualidade_proibida(
        *args,
        **kwargs,
    ):
        del args
        del kwargs
        raise AssertionError("Qualidade nao deveria rodar.")

    _preparar(
        monkeypatch,
        salvar_resumo=salvar_resumo_falha,
        analisar_qualidade=qualidade_proibida,
    )

    _agente(tmp_path)._atualizar_resumo_temporal_interpretacoes(
        tmp_path / "interpretacao_estado_atual.json",
        tmp_path / "analise_historico_interpretacoes_atual.json",
    )


def test_v128_falha_analisar_qualidade_e_isolada(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def analisar_falha(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        chamadas.append("analisar")

        raise RuntimeError("falha proposital")

    _preparar(
        monkeypatch,
        analisar_qualidade=analisar_falha,
    )

    _agente(tmp_path)._atualizar_resumo_temporal_interpretacoes(
        tmp_path / "interpretacao_estado_atual.json",
        tmp_path / "analise_historico_interpretacoes_atual.json",
    )

    assert chamadas == ["analisar"]


def test_v128_falha_salvar_qualidade_e_isolada(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def salvar_falha(
        qualidade,
        caminho,
    ):
        del qualidade
        del caminho

        chamadas.append("salvar")

        raise RuntimeError("falha proposital")

    _preparar(
        monkeypatch,
        salvar_qualidade=salvar_falha,
    )

    _agente(tmp_path)._atualizar_resumo_temporal_interpretacoes(
        tmp_path / "interpretacao_estado_atual.json",
        tmp_path / "analise_historico_interpretacoes_atual.json",
    )

    assert chamadas == ["salvar"]


def test_v128_qualidade_so_roda_depois_do_resumo_salvo(
    tmp_path,
    monkeypatch,
):
    resumo_salvo = {"valor": False}

    def salvar_resumo(
        resumo,
        caminho,
    ):
        del resumo

        resumo_salvo["valor"] = True

        return Path(caminho)

    def analisar_qualidade(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        assert resumo_salvo["valor"] is True

        return "QUALIDADE"

    _preparar(
        monkeypatch,
        salvar_resumo=salvar_resumo,
        analisar_qualidade=analisar_qualidade,
    )

    _agente(tmp_path)._atualizar_resumo_temporal_interpretacoes(
        tmp_path / "interpretacao_estado_atual.json",
        tmp_path / "analise_historico_interpretacoes_atual.json",
    )
