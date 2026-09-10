from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SUPERVISOR = ROOT / "scripts" / "supervisor_renda_automatica.ps1"


def carregar_supervisor() -> str:
    return SUPERVISOR.read_text(
        encoding="utf-8-sig",
    )


def extrair_regex_processos_gerenciados(
    conteudo: str,
) -> str:
    inicio = conteudo.index("$ManagedScriptRegex = (")

    fim = conteudo.index(
        "\n)",
        inicio,
    )

    return conteudo[inicio:fim]


def test_supervisor_tem_limpeza_de_arvores_orfas_antes_do_loop():
    conteudo = carregar_supervisor()

    chamada = conteudo.index("Stop-StaleManagedProjectTrees")

    # A primeira ocorrência é a definição da função.
    chamada = conteudo.index(
        "Stop-StaleManagedProjectTrees",
        chamada + 1,
    )

    loop = conteudo.index("while ($true)")

    assert chamada < loop


def test_supervisor_limpa_toda_arvore_operacional_relevante():
    conteudo = carregar_supervisor()

    trecho = extrair_regex_processos_gerenciados(
        conteudo,
    )

    for script in (
        "runtime",
        "bot_consulta",
        "publicador_fila",
        "chrome_launcher",
        "main",
    ):
        assert script in trecho


def test_supervisor_nao_inclui_social_scout_na_limpeza_de_startup():
    conteudo = carregar_supervisor()

    trecho = extrair_regex_processos_gerenciados(
        conteudo,
    )

    assert "social_scout_telegram" not in trecho


def test_supervisor_nao_depende_do_executable_path_da_venv():
    conteudo = carregar_supervisor()

    assert "ExecutablePath -eq $Python" not in conteudo
    assert '$_.Name -match "^python(w)?\\.exe$"' in conteudo


def test_supervisor_identifica_raiz_logica_por_parent_process_id():
    conteudo = carregar_supervisor()

    assert "$_.ParentProcessId -notin $ids" in conteudo


def test_supervisor_encerra_arvores_com_taskkill_recursivo():
    conteudo = carregar_supervisor()

    assert "& taskkill.exe" in conteudo

    bloco = re.search(
        r"function Stop-ProjectProcessTree \{" r".+?" r"\n\}",
        conteudo,
        flags=re.DOTALL,
    )

    assert bloco is not None

    texto_bloco = bloco.group(0)

    assert "/PID $ProcessId" in texto_bloco
    assert "/T" in texto_bloco
    assert "/F" in texto_bloco


@pytest.mark.skipif(
    os.name != "nt",
    reason="Validacao sintatica usa Windows PowerShell.",
)
def test_supervisor_e_sintaticamente_valido_no_powershell():
    powershell = shutil.which(
        "powershell.exe",
    )

    if powershell is None:
        pytest.skip(
            "Windows PowerShell nao encontrado.",
        )

    comando = (
        "$tokens = $null; "
        "$erros = $null; "
        "[System.Management.Automation.Language.Parser]::"
        "ParseFile("
        f"'{SUPERVISOR}', "
        "[ref]$tokens, "
        "[ref]$erros"
        ") | Out-Null; "
        "if ($erros.Count -gt 0) { "
        "$erros | ForEach-Object { "
        "Write-Error $_.Message "
        "}; "
        "exit 1 "
        "}; "
        "exit 0"
    )

    resultado = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            comando,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=15,
    )

    assert resultado.returncode == 0, resultado.stdout + "\n" + resultado.stderr


def test_supervisor_mantem_node_health_agent_fora_da_limpeza_de_startup():
    conteudo = carregar_supervisor()

    trecho = extrair_regex_processos_gerenciados(
        conteudo,
    )

    assert "node_agent" not in trecho


def test_supervisor_garante_node_health_agent_no_loop():
    conteudo = carregar_supervisor()

    assert "$NodeAgentScript = Join-Path" in conteudo
    assert '"node_agent.py"' in conteudo
    assert "Test-Path $NodeAgentScript" in conteudo

    loop = conteudo[conteudo.index("while ($true)") :]

    assert '-ScriptName "node_agent.py"' in loop
    assert "-ScriptPath $NodeAgentScript" in loop


def test_supervisor_identifica_servicos_pelo_caminho_absoluto_do_script():
    conteudo = carregar_supervisor()

    assert 'CommandLine -like "*$ScriptPath*"' in conteudo

    assert "-ScriptPath $ScriptPath" in conteudo
