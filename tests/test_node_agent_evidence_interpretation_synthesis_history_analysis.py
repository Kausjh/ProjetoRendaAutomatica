from pathlib import Path

import services.infra.node_agent as node_agent_module
from services.infra.node_agent import NodeHealthAgent


def _agente(
    tmp_path,
):
    agente = object.__new__(NodeHealthAgent)

    agente.caminho_estado = tmp_path / "estado_atual.json"

    return agente


def _preparar(
    monkeypatch,
    *,
    persistir=None,
    analisar=None,
    salvar_analise=None,
):
    monkeypatch.setattr(
        node_agent_module,
        "persistir_sintese_evidencias_interpretacoes_node",
        (persistir if persistir is not None else lambda *args: "PERSISTIDO"),
    )

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinteses_interpretacoes_node",
        (analisar if analisar is not None else lambda *args: "ANALISE"),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_analise_historico_sinteses_interpretacoes_node",
        (salvar_analise if salvar_analise is not None else lambda analise, caminho: Path(caminho)),
    )


def test_v134_analise_roda_depois_do_historico_persistido(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def persistir(
        *args,
    ):
        del args

        chamadas.append("persistir")

        return "PERSISTIDO"

    def analisar(
        *args,
    ):
        del args

        chamadas.append("analisar")

        return "ANALISE"

    def salvar(
        analise,
        caminho,
    ):
        del analise
        del caminho

        chamadas.append("salvar")

        return Path("analise.json")

    _preparar(
        monkeypatch,
        persistir=persistir,
        analisar=analisar,
        salvar_analise=salvar,
    )

    _agente(tmp_path)._persistir_historico_sintese_evidencias_interpretacoes(
        tmp_path / "sintese_evidencias_interpretacoes_atual.json"
    )

    assert chamadas == [
        "persistir",
        "analisar",
        "salvar",
    ]


def test_v134_caminhos_sao_corretos(
    tmp_path,
    monkeypatch,
):
    recebido = {}

    def persistir(
        caminho_sintese,
        diretorio_historico,
    ):
        recebido["sintese"] = Path(caminho_sintese)

        recebido["historico_persistencia"] = Path(diretorio_historico)

        return "PERSISTIDO"

    def analisar(
        diretorio_historico,
    ):
        recebido["historico_analise"] = Path(diretorio_historico)

        return "ANALISE"

    def salvar(
        analise,
        caminho,
    ):
        del analise

        recebido["saida_analise"] = Path(caminho)

        return Path(caminho)

    _preparar(
        monkeypatch,
        persistir=persistir,
        analisar=analisar,
        salvar_analise=salvar,
    )

    _agente(tmp_path)._persistir_historico_sintese_evidencias_interpretacoes(
        tmp_path / "sintese_evidencias_interpretacoes_atual.json"
    )

    esperado_historico = tmp_path / "historico_sinteses_interpretacoes"

    assert recebido == {
        "sintese": (tmp_path / "sintese_evidencias_interpretacoes_atual.json"),
        "historico_persistencia": esperado_historico,
        "historico_analise": esperado_historico,
        "saida_analise": (tmp_path / "analise_historico_sinteses_interpretacoes_atual.json"),
    }


def test_v134_falha_persistencia_suprime_analise(
    tmp_path,
    monkeypatch,
):
    def persistir_falha(
        *args,
    ):
        del args

        raise RuntimeError("falha proposital")

    def analise_proibida(
        *args,
    ):
        del args

        raise AssertionError("Analise nao deveria rodar.")

    _preparar(
        monkeypatch,
        persistir=persistir_falha,
        analisar=analise_proibida,
    )

    _agente(tmp_path)._persistir_historico_sintese_evidencias_interpretacoes(
        tmp_path / "sintese_evidencias_interpretacoes_atual.json"
    )


def test_v134_falha_analisar_historico_e_isolada(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def analisar_falha(
        *args,
    ):
        del args

        chamadas.append("analisar")

        raise RuntimeError("falha proposital")

    _preparar(
        monkeypatch,
        analisar=analisar_falha,
    )

    _agente(tmp_path)._persistir_historico_sintese_evidencias_interpretacoes(
        tmp_path / "sintese_evidencias_interpretacoes_atual.json"
    )

    assert chamadas == ["analisar"]


def test_v134_falha_salvar_analise_e_isolada(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def salvar_falha(
        analise,
        caminho,
    ):
        del analise
        del caminho

        chamadas.append("salvar")

        raise RuntimeError("falha proposital")

    _preparar(
        monkeypatch,
        salvar_analise=salvar_falha,
    )

    _agente(tmp_path)._persistir_historico_sintese_evidencias_interpretacoes(
        tmp_path / "sintese_evidencias_interpretacoes_atual.json"
    )

    assert chamadas == ["salvar"]


def test_v134_analise_so_roda_depois_da_persistencia(
    tmp_path,
    monkeypatch,
):
    persistido = {"valor": False}

    def persistir(
        *args,
    ):
        del args

        persistido["valor"] = True

        return "PERSISTIDO"

    def analisar(
        *args,
    ):
        del args

        assert persistido["valor"] is True

        return "ANALISE"

    _preparar(
        monkeypatch,
        persistir=persistir,
        analisar=analisar,
    )

    _agente(tmp_path)._persistir_historico_sintese_evidencias_interpretacoes(
        tmp_path / "sintese_evidencias_interpretacoes_atual.json"
    )


def test_v134_integracao_retorna_none(
    tmp_path,
    monkeypatch,
):
    _preparar(
        monkeypatch,
    )

    resultado = _agente(tmp_path)._persistir_historico_sintese_evidencias_interpretacoes(
        tmp_path / "sintese_evidencias_interpretacoes_atual.json"
    )

    assert resultado is None
