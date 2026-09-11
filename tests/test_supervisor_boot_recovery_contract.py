from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "scripts" / "supervisor_renda_automatica.ps1"


def _texto() -> str:
    return SUPERVISOR.read_text(
        encoding="utf-8-sig",
    )


def test_supervisor_mantem_componentes_em_passos_isolados():
    texto = _texto()

    for nome in (
        'Name "node_agent"',
        'Name "partner_scout"',
        'Name "social_scout"',
        'Name "chrome_cdp"',
        'Name "runtime"',
    ):
        assert nome in texto

    assert "function Invoke-SupervisorStep" in texto


def test_cdp_nao_e_gate_global_do_loop():
    texto = _texto()

    pos_cdp = texto.index('Name "chrome_cdp"')
    pos_runtime = texto.index('Name "runtime"', pos_cdp)

    assert pos_runtime > pos_cdp
    assert "Ensure-Cdp" in texto[pos_cdp:pos_runtime]


def test_supervisor_possui_log_operacional_persistente():
    texto = _texto()

    assert "logs\\supervisor" in texto
    assert "function Write-SupervisorLog" in texto
    assert "Supervisor iniciado" in texto
    assert "DEGRADED" in texto
    assert "HEALTHY" in texto


def test_supervisor_gerencia_todas_as_raizes_operacionais():
    texto = _texto()

    loop = texto[texto.index("while ($true)") :]

    for script in (
        "runtime.py",
        "social_scout_telegram.py",
        "node_agent.py",
        "partner_scout.py",
    ):
        assert script in loop


def test_supervisor_nao_muda_configuracao_da_task_windows():
    texto = _texto()

    proibidos = (
        "Register-ScheduledTask",
        "Set-ScheduledTask",
        "Unregister-ScheduledTask",
        "New-ScheduledTaskTrigger",
        "New-ScheduledTaskPrincipal",
    )

    for proibido in proibidos:
        assert proibido not in texto


def test_componentes_independentes_ficam_fora_da_limpeza_destrutiva():
    texto = _texto()

    inicio = texto.index("$ManagedScriptRegex = (")
    fim = texto.index(
        "\n)",
        inicio,
    )
    trecho = texto[inicio:fim]

    assert "social_scout_telegram" not in trecho
    assert "node_agent" not in trecho
    assert "partner_scout" not in trecho

    for esperado in (
        "runtime",
        "bot_consulta",
        "publicador_fila",
        "chrome_launcher",
        "main",
    ):
        assert esperado in trecho


def test_componentes_independentes_validam_script_no_proprio_passo():
    texto = _texto()

    loop = texto[texto.index("while ($true)") :]

    for verificacao in (
        "Test-Path $NodeAgentScript",
        "Test-Path $PartnerScoutScript",
        "Test-Path $ListenerScript",
        "Test-Path $RuntimeScript",
    ):
        assert verificacao in loop
