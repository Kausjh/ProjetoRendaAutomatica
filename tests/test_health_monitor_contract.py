from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUPERVISOR = ROOT / "scripts" / "supervisor_renda_automatica.ps1"

MONITOR = ROOT / "scripts" / "monitor_saude_renda_automatica.ps1"


def _supervisor() -> str:
    return SUPERVISOR.read_text(encoding="utf-8-sig")


def _monitor() -> str:
    return MONITOR.read_text(encoding="utf-8-sig")


def test_supervisor_grava_heartbeat_em_programdata():
    texto = _supervisor()

    assert "ProjetoRendaAutomatica\\health" in texto
    assert '"heartbeat.json"' in texto
    assert "function Write-HealthHeartbeat" in texto
    assert "schema_version = 1" in texto
    assert "generated_at = (" in texto
    assert "overall = $overall" in texto


def test_heartbeat_expoe_supervisor_e_componentes():
    texto = _supervisor()

    for item in (
        "started_at",
        "identity",
        "session_id",
        "pid",
        "boot_time",
        "node_agent",
        "partner_scout",
        "social_scout",
        "chrome_cdp",
        "runtime",
    ):
        assert item in texto


def test_heartbeat_e_escrito_atomicamente():
    texto = _supervisor()

    assert "$tempPath = (" in texto
    assert "ConvertTo-Json -Depth 5" in texto
    assert "Move-Item `" in texto
    assert "-Destination $HealthHeartbeatPath" in texto


def test_heartbeat_acontece_no_loop_principal():
    texto = _supervisor()

    loop = texto[texto.index("while ($true)") :]

    assert "Write-HealthHeartbeat" in loop

    assert loop.index("Write-HealthHeartbeat") < loop.rindex("Start-Sleep -Seconds 30")


def test_monitor_tem_notify_icon_e_timer():
    texto = _monitor()

    assert "System.Windows.Forms.NotifyIcon" in texto
    assert "System.Windows.Forms.Timer" in texto
    assert "$timer.Interval = 5000" in texto
    assert "[System.Windows.Forms.Application]::Run()" in texto


def test_monitor_classifica_online_degradado_offline():
    texto = _monitor()

    assert "$FreshnessSeconds = 90" in texto

    for status in (
        '"ONLINE"',
        '"DEGRADED"',
        '"OFFLINE"',
    ):
        assert status in texto


def test_monitor_mostra_componentes_e_prova_pre_login():
    texto = _monitor()

    for item in (
        "Runtime",
        "Social Scout",
        "Partner Scout",
        "Node Agent",
        "Chrome/CDP",
        "Antes do login GUI",
        "supervisor iniciou antes do Explorer",
    ):
        assert item in texto


def test_monitor_e_somente_observador():
    texto = _monitor().lower()

    proibidos = (
        "start-scheduledtask",
        "stop-scheduledtask",
        "register-scheduledtask",
        "unregister-scheduledtask",
        "taskkill.exe",
        "stop-process",
        "shutdown.exe",
    )

    for item in proibidos:
        assert item not in texto


def test_heartbeat_expoe_telemetria_de_rede_pos_boot():
    texto = _supervisor()

    assert "function Update-InternetBootState" in texto
    assert "Get-NetConnectionProfile" in texto
    assert "network_boot_state.json" in texto
    assert "first_online_at" in texto
    assert 'source = "windows_ncsi"' in texto
    assert "network = [ordered]@{" in texto


def test_estado_de_rede_e_persistido_por_boot():
    texto = _supervisor()

    assert '$bootKey = $bootTime.ToString("o")' in texto
    assert "$HealthNetworkStatePath" in texto
    assert "$networkTemp = (" in texto
    assert "-Destination $HealthNetworkStatePath" in texto


def test_monitor_exibe_prova_de_internet_antes_do_login():
    texto = _monitor()

    assert "REDE / RECUPERACAO" in texto
    assert "Internet atual:" in texto
    assert "1a conexao pos-boot:" in texto
    assert "internet ficou online antes do Explorer" in texto
    assert "SEM RESTRICAO - rede autonoma comprovada" in texto
    assert "JANELA SEGURA - horario ainda nao definido" in texto


def test_telemetria_nao_adiciona_reboot_automatico():
    monitor = _monitor().lower()

    assert "shutdown.exe" not in monitor
    assert "restart-computer" not in monitor
