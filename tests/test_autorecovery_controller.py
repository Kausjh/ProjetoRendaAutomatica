from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "scripts" / "autorecovery_renda_automatica.ps1"
SUPERVISOR = ROOT / "scripts" / "supervisor_renda_automatica.ps1"
MONITOR = ROOT / "scripts" / "monitor_saude_renda_automatica.ps1"
POLICY = ROOT / "config" / "autorecovery_policy.json"


def _engine() -> str:
    return ENGINE.read_text(encoding="utf-8-sig")


def _supervisor() -> str:
    return SUPERVISOR.read_text(encoding="utf-8-sig")


def _monitor() -> str:
    return MONITOR.read_text(encoding="utf-8-sig")


def test_policy_v1c_continua_desarmada_ate_prova_real():
    data = json.loads(POLICY.read_text(encoding="utf-8-sig"))
    assert data["enabled"] is True
    assert data["mode"] == "active_supervisor_recovery"
    assert data["supervisor_restart_enabled"] is True
    assert data["auto_reboot_enabled"] is False
    assert data["reboot_cooldown_hours"] == 6
    assert data["max_auto_reboots_per_cooldown"] == 1


def test_engine_modela_escalonamento():
    texto = _engine()
    for item in (
        "LOCAL_RECOVERY",
        "WOULD_RESTART_SUPERVISOR",
        "RESTART_SUPERVISOR_PENDING",
        "WAITING_NETWORK",
        "REBOOT_BLOCKED_NETWORK_AUTONOMY",
        "REBOOT_LOCKOUT",
        "WOULD_REBOOT",
        "REBOOT_PENDING",
    ):
        assert item in texto


def test_engine_persiste_estado_atomicamente():
    texto = _engine()
    assert "function Save-AutoRecoveryState" in texto
    assert "ConvertTo-Json -Depth 6" in texto
    assert "-Destination $StatePath" in texto


def test_engine_tem_travas():
    texto = _engine()
    assert "Test-NetworkAutonomyProof" in texto
    assert "if (-not $NetworkOnline)" in texto
    assert "reboot_cooldown_hours" in texto
    assert "last_auto_reboot_at" in texto
    assert "REBOOT_LOCKOUT" in texto


def test_supervisor_v1c_modela_restart_e_reboot_real():
    texto = _supervisor()

    assert "$AutoRecoveryLibrary =" in texto
    assert ". $AutoRecoveryLibrary" in texto
    assert "Update-AutoRecoveryController" in texto
    assert "Register-AutoRecoveryAction" in texto
    assert '"RESTART_SUPERVISOR"' in texto
    assert '"RESTART_SUPERVISOR_PENDING"' in texto
    assert "exit 1" in texto

    assert '"REBOOT_PENDING"' in texto
    assert 'recommended_action -eq "REBOOT"' in texto
    assert "function Invoke-WindowsAutoReboot" in texto
    assert "shutdown.exe" in texto
    assert '"/r"' in texto
    assert '"/t"' in texto
    assert '-Action "REBOOT"' in texto
    assert "$AutoRebootDelaySeconds = 60" in texto
    assert "Restart-Computer" not in texto


def test_monitor_exibe_autorecovery():
    texto = _monitor()
    for item in (
        "autorecovery_state.json",
        '"AUTO-RECOVERY"',
        '"Ciclos degradados:',
        '"Restarts supervisor:',
        '"Acao recomendada:',
        '"Lockout reboot ate:',
        '"Rede autonoma provada:',
    ):
        assert item in texto


def test_monitor_continua_observador():
    texto = _monitor().lower()
    for item in (
        "start-scheduledtask",
        "stop-scheduledtask",
        "register-scheduledtask",
        "unregister-scheduledtask",
        "taskkill.exe",
        "stop-process",
        "shutdown.exe",
        "restart-computer",
    ):
        assert item not in texto
