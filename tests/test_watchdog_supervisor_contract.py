from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHDOG = ROOT / "scripts" / "watchdog_supervisor_renda_automatica.ps1"


def _text() -> str:
    return WATCHDOG.read_text(encoding="utf-8-sig")


def test_watchdog_mira_apenas_supervisor_e_task_principal():
    texto = _text()

    assert '$MainTaskName = "RendaAutomatica"' in texto
    assert "supervisor_renda_automatica.ps1" in texto
    assert "Start-ScheduledTask" in texto


def test_watchdog_tem_graca_antes_de_recuperar():
    texto = _text()

    assert "$MissingCyclesBeforeRecovery = 2" in texto
    assert "$CheckIntervalSeconds = 15" in texto
    assert '"WAITING_GRACE"' in texto


def test_watchdog_tem_single_instance_mutex():
    texto = _text()

    assert "Global\\ProjetoRendaAutomaticaSupervisorWatchdog" in texto
    assert "System.Threading.Mutex" in texto


def test_watchdog_persiste_health_state_e_logs():
    texto = _text()

    assert "supervisor_watchdog_state.json" in texto
    assert "watchdog_" in texto
    assert "ConvertTo-Json -Depth 6" in texto
    assert "Move-Item" in texto


def test_watchdog_tem_reset_controlado_para_task_zumbi():
    texto = _text()

    assert "Stop-ScheduledTask" in texto
    assert '"RESET_TASK"' in texto
    assert '"RESET_TASK_FAILED"' in texto


def test_watchdog_nao_reinicia_windows():
    texto = _text().lower()

    assert "shutdown.exe" not in texto
    assert "restart-computer" not in texto


def test_watchdog_nao_muta_codigo_do_projeto():
    texto = _text().lower()

    proibidos = (
        "git checkout",
        "git restore",
        "git reset",
        "set-content $projectroot",
        "remove-item $projectroot",
    )

    for item in proibidos:
        assert item not in texto


def test_watchdog_nao_confunde_o_proprio_nome_com_supervisor():
    texto = _text()

    assert "[regex]::Escape(" in texto
    assert "$supervisorPattern" in texto
    assert "$_ .CommandLine -match $supervisorPattern".replace("$_ ", "$_") in texto
    assert '"*supervisor_renda_automatica.ps1*"' not in texto


def test_watchdog_match_exige_argumento_file_do_supervisor():
    texto = _text()

    assert "(?:^|\\s)-File\\s+" in texto
    assert "supervisor_renda_automatica.ps1" in texto
