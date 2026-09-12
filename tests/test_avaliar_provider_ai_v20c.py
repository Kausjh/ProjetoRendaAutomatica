from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import scripts.avaliar_provider_ai as harness


def test_parser_v20c_preserva_contrato_default() -> None:
    args = harness.criar_parser().parse_args([])

    assert args.modo == "mock"
    assert args.caso == "contrato"
    assert args.permitir_rede_real is False


def test_classificador_mock_exercita_gate_real(
    tmp_path: Path,
) -> None:
    resultado = harness.executar_avaliacao_dominios_mock(
        caso="classificador",
        caminho_relatorio=(tmp_path / "classificador.json"),
    )

    assert resultado["modo"] == "mock"
    assert resultado["rede_real_utilizada"] is False
    assert len(resultado["casos"]) == 1

    caso = resultado["casos"][0]

    assert caso["caso"] == "classificador"
    assert caso["gate_ai_acionado"] is True
    assert caso["diagnostico"]["ambiguo"] is True
    assert caso["diagnostico"]["motivo"] == "empate_real_categorias_topo"
    assert caso["categoria_deterministica"] == "Processador"
    assert caso["categoria_final"] == "Armazenamento"
    assert caso["inteligencia_ai"]["status"] == "sugestao_ai_validada"
    assert caso["inteligencia_ai"]["validada_deterministicamente"] is True
    assert caso["inteligencia_ai"]["autoriza_publicacao"] is False
    assert caso["controle_operacional"]["observabilidade"]["chamadas_externas_total"] == 1


def test_curadoria_mock_exercita_gate_real_sem_mudar_publicavel(
    tmp_path: Path,
) -> None:
    resultado = harness.executar_avaliacao_dominios_mock(
        caso="curadoria",
        caminho_relatorio=(tmp_path / "curadoria.json"),
    )

    caso = resultado["casos"][0]

    assert caso["caso"] == "curadoria"
    assert caso["gate_ai_acionado"] is True
    assert caso["diagnostico"]["motivo"] == "incerteza_editorial_objetiva"
    assert "confianca_normalizacao_abaixo_de_90" in caso["diagnostico"]["sinais"]
    assert caso["publicavel_deterministico"] is True
    assert caso["publicavel_final"] is True
    assert caso["revisao_manual_sugerida"] is True
    assert caso["inteligencia_ai"]["status"] == "sugestao_ai_validada"
    assert caso["inteligencia_ai"]["substitui_regras_deterministicas"] is False
    assert caso["controle_operacional"]["observabilidade"]["chamadas_externas_total"] == 1


def test_dominios_mock_gera_relatorio_separado(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "dominios.json"

    resultado = harness.executar_avaliacao_dominios_mock(
        caso="dominios",
        caminho_relatorio=destino,
    )

    assert destino.exists()
    assert len(resultado["casos"]) == 2
    assert {item["caso"] for item in resultado["casos"]} == {
        "classificador",
        "curadoria",
    }

    arquivo = json.loads(destino.read_text(encoding="utf-8"))

    assert arquivo["rede_real_utilizada"] is False
    assert len(arquivo["casos"]) == 2


def test_cli_dominios_mock_funciona(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "cli-dominios.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.avaliar_provider_ai",
            "--modo",
            "mock",
            "--caso",
            "dominios",
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
    assert "CASO=dominios" in proc.stdout
    assert "CASOS_TOTAL=2" in proc.stdout
    assert "REDE_REAL_UTILIZADA=False" in proc.stdout
    assert "CLASSIFICADOR_GATE_AI_ACIONADO=True" in proc.stdout
    assert "CURADORIA_GATE_AI_ACIONADO=True" in proc.stdout
    assert destino.exists()


def test_dominios_nao_podem_rodar_em_modo_real(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "nao-deve.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.avaliar_provider_ai",
            "--modo",
            "real",
            "--caso",
            "dominios",
            "--permitir-rede-real",
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

    assert proc.returncode == 1
    assert "Casos de dominio V20C" in proc.stdout
    assert not destino.exists()


def test_executar_avaliacao_v20b_permanece_compativel(
    tmp_path: Path,
) -> None:
    resultado = harness.executar_avaliacao(
        modo="mock",
        caminho_relatorio=(tmp_path / "contrato.json"),
    )

    assert resultado["modo"] == "mock"
    assert resultado["tarefa"] == "avaliar_provider_ai"
    assert resultado["resultado"]["status"] == "sugestao_ai_validada"


def test_main_pipeline_continua_intocado() -> None:
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    assert "executar_avaliacao_dominios_mock" not in texto
    assert texto.count("habilitado=False") >= 2
