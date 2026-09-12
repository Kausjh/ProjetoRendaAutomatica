from __future__ import annotations

from pathlib import Path

import pytest

import scripts.avaliar_provider_ai as harness
from services.provedor_openai_responses_ai import (
    MODELO_OPENAI_PADRAO,
    ProvedorOpenAIResponsesAI,
)


class ConfigSegura:
    ai_kill_switch_ativo = True
    ai_limite_tokens_total = 50000
    ai_limite_custo_estimado_usd = 0.5
    ai_provedor_endpoint = None
    ai_provedor_nome = None
    ai_provedor_modelo = None
    ai_provedor_auth_header_nome = None
    ai_provedor_auth_header_valor = None


def test_parser_preserva_provider_generico_por_padrao() -> None:
    args = harness.criar_parser().parse_args([])

    assert args.provider_real == "generico"
    assert args.caso == "contrato"
    assert args.modo == "mock"


def test_openai_real_sem_flag_falha_antes_de_config(
    monkeypatch,
) -> None:
    class ConfigNaoPodeSerInstanciada:
        def __init__(self) -> None:
            raise AssertionError("Configuracoes nao deveria ser instanciada.")

    monkeypatch.setattr(
        harness,
        "Configuracoes",
        ConfigNaoPodeSerInstanciada,
    )

    with pytest.raises(
        RuntimeError,
        match="--permitir-rede-real",
    ):
        harness._criar_provider_real(
            permitir_rede_real=False,
            provider_real="openai",
        )


def test_openai_real_exige_api_key(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        harness,
        "Configuracoes",
        ConfigSegura,
    )
    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="OPENAI_API_KEY",
    ):
        harness._criar_provider_real(
            permitir_rede_real=True,
            provider_real="openai",
        )


def test_openai_real_cria_adapter_sem_chamar_rede(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        harness,
        "Configuracoes",
        ConfigSegura,
    )
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "segredo-teste",
    )
    monkeypatch.setenv(
        "OPENAI_MODEL",
        "gpt-5.6-luna",
    )

    provedor, controle = harness._criar_provider_real(
        permitir_rede_real=True,
        provider_real="openai",
    )

    assert isinstance(
        provedor,
        ProvedorOpenAIResponsesAI,
    )
    assert provedor.modelo == "gpt-5.6-luna"
    assert controle.kill_switch_ativo is True
    assert controle.limite_chamadas_externas == 1


def test_openai_model_default_e_luna(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "OPENAI_MODEL",
        raising=False,
    )

    assert harness._buscar_openai_model_harness() == MODELO_OPENAI_PADRAO == "gpt-5.6-luna"


def test_openai_com_kill_switch_nao_chama_provider(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        harness,
        "Configuracoes",
        ConfigSegura,
    )
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "segredo-teste",
    )

    chamadas = {
        "total": 0,
    }

    def nao_pode_chamar(
        self,
        solicitacao,
    ):
        chamadas["total"] += 1
        raise AssertionError("Provider nao deveria ser chamado.")

    monkeypatch.setattr(
        ProvedorOpenAIResponsesAI,
        "interpretar",
        nao_pode_chamar,
    )

    resultado = harness.executar_avaliacao(
        modo="real",
        permitir_rede_real=True,
        provider_real="openai",
        caminho_relatorio=(tmp_path / "kill-switch.json"),
    )

    assert chamadas["total"] == 0
    assert resultado["resultado"]["status"] == "kill_switch_bloqueado"
    assert resultado["controle_operacional"]["observabilidade"]["chamadas_externas_total"] == 0


def test_dominios_continuam_sem_openai_real() -> None:
    parser = harness.criar_parser()

    args = parser.parse_args(
        [
            "--modo",
            "real",
            "--provider-real",
            "openai",
            "--caso",
            "dominios",
            "--permitir-rede-real",
        ]
    )

    assert args.modo == "real"
    assert args.provider_real == "openai"
    assert args.caso == "dominios"


def test_main_continua_sem_openai() -> None:
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    for proibido in (
        "ProvedorOpenAIResponsesAI",
        "OPENAI_API_KEY",
        "api.openai.com",
    ):
        assert proibido not in texto

    assert texto.count("habilitado=False") >= 2


def test_env_example_documenta_openai_sem_segredo() -> None:
    texto = Path(".env.example").read_text(encoding="utf-8-sig")

    assert "OPENAI_API_KEY=" in texto
    assert "OPENAI_MODEL=gpt-5.6-luna" in texto
    assert "sk-" not in texto
    assert "segredo-teste" not in texto
