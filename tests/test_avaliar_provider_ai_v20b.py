from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.avaliar_provider_ai as harness
from models.inteligencia_ai import (
    RespostaProvedorInteligenciaAI,
)


class ProvedorContador:
    def __init__(self) -> None:
        self.chamadas = 0

    def interpretar(self, solicitacao):
        self.chamadas += 1

        return RespostaProvedorInteligenciaAI(
            conteudo={
                "resultado": "ok",
            },
            confianca=0.99,
            provedor="fake-real",
            modelo="fake",
        )


class ConfigKillSwitchAtivo:
    ai_provedor_endpoint = "https://example.invalid/ai"
    ai_provedor_nome = "fake-real"
    ai_provedor_modelo = "fake"
    ai_provedor_auth_header_nome = None
    ai_provedor_auth_header_valor = None
    ai_kill_switch_ativo = True
    ai_limite_tokens_total = 1000
    ai_limite_custo_estimado_usd = 0.1


def test_parser_default_e_mock() -> None:
    parser = harness.criar_parser()

    args = parser.parse_args([])

    assert args.modo == "mock"
    assert args.permitir_rede_real is False


def test_mock_executa_sem_rede_real_e_gera_relatorio(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "relatorio.json"

    resultado = harness.executar_avaliacao(
        modo="mock",
        caminho_relatorio=destino,
    )

    assert destino.exists()

    arquivo = json.loads(destino.read_text(encoding="utf-8"))

    assert resultado["modo"] == "mock"
    assert resultado["resultado"]["status"] == "sugestao_ai_validada"
    assert resultado["resultado"]["fallback_usado"] is False
    assert resultado["resultado"]["validada_deterministicamente"] is True
    assert resultado["resultado"]["autoriza_publicacao"] is False
    assert resultado["resultado"]["autoriza_alteracao_budget"] is False
    assert resultado["resultado"]["substitui_regras_deterministicas"] is False
    assert arquivo["controle_operacional"]["observabilidade"]["chamadas_externas_total"] == 1


def test_mock_preserva_telemetria_de_usage(
    tmp_path: Path,
) -> None:
    resultado = harness.executar_avaliacao(
        modo="mock",
        caminho_relatorio=(tmp_path / "usage.json"),
    )

    obs = resultado["controle_operacional"]["observabilidade"]

    assert obs["tokens_total"] == 16
    assert obs["chamadas_com_tokens_total_conhecido"] == 1
    assert obs["custo_estimado_usd_total"] == pytest.approx(0.0001)
    assert obs["chamadas_com_custo_conhecido"] == 1


def test_modo_real_sem_flag_falha_antes_de_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def configuracoes_nao_deveria_ser_criada():
        raise AssertionError("Configuracoes nao deveria ser criada")

    monkeypatch.setattr(
        harness,
        "Configuracoes",
        configuracoes_nao_deveria_ser_criada,
    )

    with pytest.raises(
        RuntimeError,
        match="--permitir-rede-real",
    ):
        harness.executar_avaliacao(
            modo="real",
            permitir_rede_real=False,
            caminho_relatorio=(tmp_path / "real.json"),
        )


def test_modo_real_respeita_kill_switch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provedor = ProvedorContador()

    monkeypatch.setattr(
        harness,
        "Configuracoes",
        ConfigKillSwitchAtivo,
    )

    monkeypatch.setattr(
        harness,
        "criar_provedor_http_inteligencia_ai",
        lambda **kwargs: provedor,
    )

    resultado = harness.executar_avaliacao(
        modo="real",
        permitir_rede_real=True,
        caminho_relatorio=(tmp_path / "real-kill.json"),
    )

    assert resultado["resultado"]["status"] == "kill_switch_bloqueado"
    assert resultado["resultado"]["fallback_usado"] is True
    assert provedor.chamadas == 0
    assert resultado["controle_operacional"]["observabilidade"]["chamadas_externas_total"] == 0


def test_modo_real_tem_limite_local_de_uma_chamada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provedor = ProvedorContador()

    class ConfigLiberada(ConfigKillSwitchAtivo):
        ai_kill_switch_ativo = False

    monkeypatch.setattr(
        harness,
        "Configuracoes",
        ConfigLiberada,
    )

    monkeypatch.setattr(
        harness,
        "criar_provedor_http_inteligencia_ai",
        lambda **kwargs: provedor,
    )

    provider, controle = harness._criar_provider_real(
        permitir_rede_real=True,
    )

    assert provider is provedor
    assert controle.limite_chamadas_externas == 1


def test_cli_modulo_mock_funciona(
    tmp_path: Path,
) -> None:
    import subprocess
    import sys

    destino = tmp_path / "cli.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.avaliar_provider_ai",
            "--modo",
            "mock",
            "--relatorio",
            str(destino),
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert proc.returncode == 0, proc.stdout
    assert "AVALIACAO_PROVIDER_AI_OK=True" in proc.stdout
    assert "MODO=mock" in proc.stdout
    assert destino.exists()


def test_main_pipeline_permanece_fora_do_harness() -> None:
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    assert "avaliar_provider_ai" not in texto

    assert texto.count("habilitado=False") >= 2
