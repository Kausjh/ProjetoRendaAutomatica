$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class HealthMonitorNative {
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern bool DestroyIcon(IntPtr handle);
}
"@

[System.Windows.Forms.Application]::EnableVisualStyles()

$ProjectRoot = "C:\Projetos\ProjetoRendaAutomatica"

$HeartbeatPath = Join-Path `
    $env:ProgramData `
    "ProjetoRendaAutomatica\health\heartbeat.json"

$AutoRecoveryStatePath = Join-Path `
    $env:ProgramData `
    "ProjetoRendaAutomatica\health\autorecovery_state.json"


$SupervisorLogDirectory = Join-Path `
    $ProjectRoot `
    "logs\supervisor"

$FreshnessSeconds = 90

$mutexName = (
    "Local\ProjetoRendaAutomaticaHealthMonitor"
)

$createdNew = $false

$mutex = New-Object `
    System.Threading.Mutex(
        $true,
        $mutexName,
        [ref]$createdNew
    )

if (-not $createdNew) {
    [System.Windows.Forms.MessageBox]::Show(
        "A Central de Saude ja esta em execucao.",
        "Renda Automatica",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null

    exit 0
}

function New-StatusIcon {
    param(
        [string]$Status
    )

    switch ($Status) {
        "ONLINE" {
            $color = [System.Drawing.Color]::LimeGreen
        }
        "DEGRADED" {
            $color = [System.Drawing.Color]::Goldenrod
        }
        "OFFLINE" {
            $color = [System.Drawing.Color]::Crimson
        }
        default {
            $color = [System.Drawing.Color]::Gray
        }
    }

    $bitmap = New-Object `
        System.Drawing.Bitmap(32, 32)

    $graphics = [System.Drawing.Graphics]::FromImage(
        $bitmap
    )

    try {
        $graphics.SmoothingMode = (
            [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        )

        $brush = New-Object `
            System.Drawing.SolidBrush($color)

        try {
            $graphics.FillEllipse(
                $brush,
                3,
                3,
                26,
                26
            )
        }
        finally {
            $brush.Dispose()
        }

        $pen = New-Object `
            System.Drawing.Pen(
                [System.Drawing.Color]::White,
                2
            )

        try {
            $graphics.DrawEllipse(
                $pen,
                3,
                3,
                26,
                26
            )
        }
        finally {
            $pen.Dispose()
        }
    }
    finally {
        $graphics.Dispose()
    }

    $handle = $bitmap.GetHicon()

    try {
        $icon = (
            [System.Drawing.Icon]::FromHandle(
                $handle
            )
        ).Clone()
    }
    finally {
        [HealthMonitorNative]::DestroyIcon(
            $handle
        ) | Out-Null

        $bitmap.Dispose()
    }

    return $icon
}

function Get-HeartbeatView {
    $now = [DateTimeOffset]::Now

    $view = [ordered]@{
        status = "OFFLINE"
        reason = "Heartbeat ainda nao encontrado."
        generated_at = $null
        age_seconds = $null
        supervisor_started_at = $null
        identity = "-"
        session_id = "-"
        boot_time = $null
        network_online = $false
        network_checked_at = $null
        network_first_online_at = $null
        network_source = "-"
        autorecovery_status = "INITIALIZING"
        autorecovery_mode = "-"
        autorecovery_incident_started_at = $null
        autorecovery_cycles = 0
        autorecovery_supervisor_restarts = 0
        autorecovery_degraded_components = @()
        autorecovery_recommended_action = "NONE"
        autorecovery_last_action = "NONE"
        autorecovery_last_action_at = $null
        autorecovery_last_recovered_at = $null
        autorecovery_reboot_lockout_until = $null
        autorecovery_network_autonomy_proven = $false
        components = [ordered]@{
            node_agent = "UNKNOWN"
            partner_scout = "UNKNOWN"
            social_scout = "UNKNOWN"
            chrome_cdp = "UNKNOWN"
            runtime = "UNKNOWN"
        }
    }

    if (-not (Test-Path $HeartbeatPath)) {
        return [pscustomobject]$view
    }

    try {
        $data = Get-Content `
            -LiteralPath $HeartbeatPath `
            -Raw |
            ConvertFrom-Json

        $generatedAt = (
            [DateTimeOffset]::Parse(
                [string]$data.generated_at
            )
        )

        $age = (
            $now -
            $generatedAt
        ).TotalSeconds

        $view.generated_at = $generatedAt
        $view.age_seconds = [math]::Max(
            0,
            [math]::Round($age)
        )

        $view.supervisor_started_at = (
            [DateTimeOffset]::Parse(
                [string]$data.supervisor.started_at
            )
        )

        $view.identity = (
            [string]$data.supervisor.identity
        )

        $view.session_id = (
            [string]$data.supervisor.session_id
        )

        $view.boot_time = (
            [DateTimeOffset]::Parse(
                [string]$data.supervisor.boot_time
            )
        )

        $view.network_online = [bool]$data.network.online

        if ($data.network.checked_at) {
            $view.network_checked_at = (
                [DateTimeOffset]::Parse(
                    [string]$data.network.checked_at
                )
            )
        }

        if ($data.network.first_online_at) {
            $view.network_first_online_at = (
                [DateTimeOffset]::Parse(
                    [string]$data.network.first_online_at
                )
            )
        }

        $view.network_source = (
            [string]$data.network.source
        )


        if (Test-Path $AutoRecoveryStatePath) {
            try {
                $recovery = Get-Content `
                    -LiteralPath $AutoRecoveryStatePath `
                    -Raw |
                    ConvertFrom-Json

                $view.autorecovery_status = [string]$recovery.status
                $view.autorecovery_mode = [string]$recovery.execution_mode
                $view.autorecovery_cycles = [int]$recovery.consecutive_degraded_cycles
                $view.autorecovery_supervisor_restarts = [int]$recovery.supervisor_restarts_this_incident
                $view.autorecovery_degraded_components = @($recovery.degraded_components)
                $view.autorecovery_recommended_action = [string]$recovery.recommended_action
                $view.autorecovery_last_action = [string]$recovery.last_action
                $view.autorecovery_network_autonomy_proven = [bool]$recovery.network_autonomy_proven

                if ($recovery.incident_started_at) {
                    $view.autorecovery_incident_started_at = [DateTimeOffset]::Parse([string]$recovery.incident_started_at)
                }

                if ($recovery.last_action_at) {
                    $view.autorecovery_last_action_at = [DateTimeOffset]::Parse([string]$recovery.last_action_at)
                }

                if ($recovery.last_recovered_at) {
                    $view.autorecovery_last_recovered_at = [DateTimeOffset]::Parse([string]$recovery.last_recovered_at)
                }

                if ($recovery.reboot_lockout_until) {
                    $view.autorecovery_reboot_lockout_until = [DateTimeOffset]::Parse([string]$recovery.reboot_lockout_until)
                }
            }
            catch {
                $view.autorecovery_status = "STATE_INVALID"
            }
        }
        foreach ($name in @(
            "node_agent",
            "partner_scout",
            "social_scout",
            "chrome_cdp",
            "runtime"
        )) {
            $view.components[$name] = (
                [string]$data.components.$name
            )
        }

        if ($age -gt $FreshnessSeconds) {
            $view.status = "OFFLINE"
            $view.reason = (
                "Heartbeat parado ha {0}s." -f
                [math]::Round($age)
            )
        }
        elseif (
            [string]$data.overall -eq "ONLINE"
        ) {
            $view.status = "ONLINE"
            $view.reason = "Todos os componentes estao saudaveis."
        }
        else {
            $view.status = "DEGRADED"
            $view.reason = "Supervisor vivo, mas ha componente degradado."
        }
    }
    catch {
        $view.status = "OFFLINE"
        $view.reason = (
            "Heartbeat invalido: " +
            $_.Exception.Message
        )
    }

    return [pscustomobject]$view
}

function Format-Time {
    param(
        [object]$Value
    )

    if ($null -eq $Value) {
        return "-"
    }

    return (
        ([DateTimeOffset]$Value).
            ToLocalTime().
            ToString("dd/MM/yyyy HH:mm:ss")
    )
}

function Format-Component {
    param(
        [string]$Name,
        [string]$State
    )

    switch ($State) {
        "HEALTHY" {
            $marker = "[OK]"
        }
        "DEGRADED" {
            $marker = "[!!]"
        }
        default {
            $marker = "[--]"
        }
    }

    return (
        "{0,-18} {1} {2}" -f
        $Name,
        $marker,
        $State
    )
}

function Get-ExplorerStart {
    try {
        $explorer = Get-Process explorer `
            -ErrorAction Stop |
            Sort-Object StartTime |
            Select-Object -First 1

        return $explorer.StartTime
    }
    catch {
        return $null
    }
}

function Get-UptimeText {
    try {
        $os = Get-CimInstance Win32_OperatingSystem
        $span = (
            Get-Date
        ) - $os.LastBootUpTime

        return (
            "{0}d {1}h {2}min" -f
            $span.Days,
            $span.Hours,
            $span.Minutes
        )
    }
    catch {
        return "-"
    }
}

# ============================================================
# CENTRAL DE SAUDE V2 - DASHBOARD
# Camada visual. A logica de heartbeat permanece independente.
# ============================================================

$UiBackground = (
    [System.Drawing.Color]::FromArgb(
        9,
        13,
        18
    )
)

$UiSurface = (
    [System.Drawing.Color]::FromArgb(
        16,
        22,
        29
    )
)

$UiSurface2 = (
    [System.Drawing.Color]::FromArgb(
        21,
        28,
        36
    )
)

$UiBorder = (
    [System.Drawing.Color]::FromArgb(
        42,
        52,
        64
    )
)

$UiText = (
    [System.Drawing.Color]::FromArgb(
        232,
        237,
        243
    )
)

$UiMuted = (
    [System.Drawing.Color]::FromArgb(
        145,
        157,
        171
    )
)

$UiGreen = (
    [System.Drawing.Color]::FromArgb(
        45,
        200,
        115
    )
)

$UiAmber = (
    [System.Drawing.Color]::FromArgb(
        236,
        179,
        62
    )
)

$UiRed = (
    [System.Drawing.Color]::FromArgb(
        235,
        87,
        87
    )
)

$UiBlue = (
    [System.Drawing.Color]::FromArgb(
        76,
        145,
        255
    )
)


function New-StatusCard {
    param(
        [string]$Title,
        [int]$X,
        [int]$Y
    )

    $panel = New-Object `
        System.Windows.Forms.Panel

    $panel.Location = (
        New-Object `
            System.Drawing.Point(
                $X,
                $Y
            )
    )

    $panel.Size = (
        New-Object `
            System.Drawing.Size(
                286,
                92
            )
    )

    $panel.BackColor = $UiSurface
    $panel.BorderStyle = (
        [System.Windows.Forms.BorderStyle]::FixedSingle
    )

    $accent = New-Object `
        System.Windows.Forms.Panel

    $accent.Location = (
        New-Object `
            System.Drawing.Point(
                0,
                0
            )
    )

    $accent.Size = (
        New-Object `
            System.Drawing.Size(
                4,
                92
            )
    )

    $accent.BackColor = $UiMuted

    $titleLabel = New-Object `
        System.Windows.Forms.Label

    $titleLabel.Text = $Title
    $titleLabel.Location = (
        New-Object `
            System.Drawing.Point(
                18,
                13
            )
    )

    $titleLabel.Size = (
        New-Object `
            System.Drawing.Size(
                245,
                18
            )
    )

    $titleLabel.ForeColor = $UiMuted

    $titleLabel.Font = (
        New-Object `
            System.Drawing.Font(
                "Segoe UI",
                9,
                [System.Drawing.FontStyle]::Bold
            )
    )

    $stateLabel = New-Object `
        System.Windows.Forms.Label

    $stateLabel.Text = "AGUARDANDO"
    $stateLabel.Location = (
        New-Object `
            System.Drawing.Point(
                18,
                34
            )
    )

    $stateLabel.Size = (
        New-Object `
            System.Drawing.Size(
                245,
                25
            )
    )

    $stateLabel.ForeColor = $UiMuted

    $stateLabel.Font = (
        New-Object `
            System.Drawing.Font(
                "Segoe UI",
                13,
                [System.Drawing.FontStyle]::Bold
            )
    )

    $detailLabel = New-Object `
        System.Windows.Forms.Label

    $detailLabel.Text = "-"
    $detailLabel.Location = (
        New-Object `
            System.Drawing.Point(
                18,
                63
            )
    )

    $detailLabel.Size = (
        New-Object `
            System.Drawing.Size(
                245,
                17
            )
    )

    $detailLabel.ForeColor = $UiMuted
    $detailLabel.AutoEllipsis = $true

    $panel.Controls.Add($accent)
    $panel.Controls.Add($titleLabel)
    $panel.Controls.Add($stateLabel)
    $panel.Controls.Add($detailLabel)

    return [pscustomobject]@{
        Panel = $panel
        Accent = $accent
        State = $stateLabel
        Detail = $detailLabel
    }
}


function Set-StatusCard {
    param(
        $Card,
        [string]$State,
        [string]$Detail = ""
    )

    $normalizado = (
        [string]$State
    ).Trim().ToUpperInvariant()

    $display = $normalizado
    $color = $UiMuted

    switch ($normalizado) {
        "HEALTHY" {
            $display = "ONLINE"
            $color = $UiGreen
        }

        "ONLINE" {
            $display = "ONLINE"
            $color = $UiGreen
        }

        "ATIVO" {
            $display = "ATIVO"
            $color = $UiGreen
        }

        "DEGRADED" {
            $display = "ATENCAO"
            $color = $UiAmber
        }

        "PAUSADO" {
            $display = "PAUSADO"
            $color = $UiAmber
        }

        "PARADO" {
            $display = "PARADO"
            $color = $UiAmber
        }

        "OFFLINE" {
            $display = "OFFLINE"
            $color = $UiRed
        }

        default {
            if (-not $display) {
                $display = "DESCONHECIDO"
            }
        }
    }

    $Card.State.Text = $display
    $Card.State.ForeColor = $color
    $Card.Accent.BackColor = $color
    $Card.Detail.Text = $Detail
}


function Get-PublicadorProcessState {

    $processos = @(
        Get-CimInstance `
            Win32_Process `
            -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -in @(
                    "python.exe",
                    "pythonw.exe"
                ) -and
                $_.CommandLine -and
                $_.CommandLine -like
                    "*ProjetoRendaAutomatica*" -and
                $_.CommandLine -like
                    "*publicador_fila.py*"
            }
    )

    if ($processos.Count -gt 0) {
        return "ATIVO"
    }

    return "PARADO"
}


function Get-PublicadorAdminState {

    $fallback = [pscustomobject]@{
        Disponivel = $false
        RuntimeDisponivel = $false
        Ativo = $false
        Pausado = $false
        Modo = "desconhecido"
        Pendentes = -1
    }

    $pythonExe = Join-Path `
        $ProjectRoot `
        ".venv\Scripts\python.exe"

    if (
        -not (
            Test-Path `
                -LiteralPath $pythonExe
        )
    ) {
        return $fallback
    }

    $codigo = @'
from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


root = Path(
    sys.argv[1]
)

admin_db = (
    root
    / "database"
    / "controle_administrativo.sqlite3"
)

fila_db = (
    root
    / "database"
    / "fila_publicacao.sqlite3"
)


def conectar(
    path: Path,
) -> sqlite3.Connection:

    uri = (
        path.resolve().as_uri()
        + "?mode=ro"
    )

    con = sqlite3.connect(
        uri,
        uri=True,
        timeout=2.0,
    )

    con.execute(
        "PRAGMA query_only = ON"
    )

    return con


with conectar(
    admin_db
) as con:

    rows = con.execute(
        """
        SELECT chave, valor
        FROM estado_operacional
        WHERE chave IN (
            'publicador_pausado',
            'modo_operacao'
        )
        """
    ).fetchall()

    estados = {
        str(chave): str(valor)
        for chave, valor in rows
    }


pausado = (
    estados.get(
        "publicador_pausado",
        "0",
    )
    .strip()
    .casefold()
    in {
        "1",
        "true",
        "sim",
        "on",
        "yes",
    }
)

modo = estados.get(
    "modo_operacao",
    "desconhecido",
)


with conectar(
    fila_db
) as con:

    pendentes = int(
        con.execute(
            """
            SELECT COUNT(*)
            FROM fila_publicacao
            WHERE LOWER(
                CAST(status AS TEXT)
            ) = 'pendente'
            """
        ).fetchone()[0]
    )


runtime_disponivel = False
publicador_ativo = False

try:

    load_dotenv(
        dotenv_path=root / ".env",
        override=False,
    )

    token = os.getenv(
        "RADAR_ADMIN_TOKEN",
        "",
    ).strip()

    if token:

        req = urllib.request.Request(
            "http://127.0.0.1:8765/operacao",
            method="GET",
            headers={
                "Authorization": (
                    "Bearer " + token
                ),
                "X-Radar-Device": (
                    "HEALTH_MONITOR_READ_ONLY"
                ),
            },
        )

        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({})
        )

        with opener.open(
            req,
            timeout=2.0,
        ) as response:

            if int(response.status) == 200:

                dados_runtime = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

                runtime_disponivel = True

                publicador_ativo = bool(
                    dados_runtime.get(
                        "publicador_ativo",
                        False,
                    )
                )

                pausado = bool(
                    dados_runtime.get(
                        "publicador_pausado",
                        pausado,
                    )
                )

                modo = str(
                    dados_runtime.get(
                        "modo_operacao",
                        modo,
                    )
                )

except Exception:

    # A consulta WMI continua existindo como fallback
    # visual caso a API administrativa esteja indisponivel.
    runtime_disponivel = False
    publicador_ativo = False


print(
    "RUNTIME_DISPONIVEL="
    + (
        "SIM"
        if runtime_disponivel
        else "NAO"
    )
)

print(
    "PUBLICADOR_ATIVO="
    + (
        "SIM"
        if publicador_ativo
        else "NAO"
    )
)

print(
    "PAUSADO="
    + (
        "SIM"
        if pausado
        else "NAO"
    )
)

print(
    f"MODO={modo}"
)

print(
    f"PENDENTES={pendentes}"
)
'@

    try {
        $saida = @(
            $codigo |
                & $pythonExe `
                    - `
                    $ProjectRoot `
                    2>$null
        )

        if ($LASTEXITCODE -ne 0) {
            return $fallback
        }

        $dados = @{}

        foreach ($linha in $saida) {

            $textoLinha = (
                [string]$linha
            ).Trim()

            $pos = (
                $textoLinha.IndexOf("=")
            )

            if ($pos -le 0) {
                continue
            }

            $chave = (
                $textoLinha.Substring(
                    0,
                    $pos
                )
            ).Trim()

            $valor = (
                $textoLinha.Substring(
                    $pos + 1
                )
            ).Trim()

            $dados[$chave] = $valor
        }

        if (
            -not $dados.ContainsKey(
                "PAUSADO"
            )
        ) {
            return $fallback
        }

        $pendentes = -1

        if (
            $dados.ContainsKey(
                "PENDENTES"
            )
        ) {
            [void][int]::TryParse(
                [string]$dados["PENDENTES"],
                [ref]$pendentes
            )
        }

        return [pscustomobject]@{
            Disponivel = $true
            RuntimeDisponivel = (
                $dados.ContainsKey(
                    "RUNTIME_DISPONIVEL"
                ) -and
                (
                    [string]$dados[
                        "RUNTIME_DISPONIVEL"
                    ]
                ) -eq "SIM"
            )
            Ativo = (
                $dados.ContainsKey(
                    "PUBLICADOR_ATIVO"
                ) -and
                (
                    [string]$dados[
                        "PUBLICADOR_ATIVO"
                    ]
                ) -eq "SIM"
            )
            Pausado = (
                [string]$dados["PAUSADO"]
            ) -eq "SIM"
            Modo = (
                [string]$dados["MODO"]
            )
            Pendentes = $pendentes
        }
    }
    catch {
        return $fallback
    }
}


$form = New-Object `
    System.Windows.Forms.Form

$form.Text = (
    "Radar de Ofertas - Central de Saude"
)

$form.ClientSize = (
    New-Object `
        System.Drawing.Size(
            960,
            700
        )
)

$form.StartPosition = (
    [System.Windows.Forms.FormStartPosition]::CenterScreen
)

$form.FormBorderStyle = (
    [System.Windows.Forms.FormBorderStyle]::FixedSingle
)

$form.MaximizeBox = $false
$form.MinimizeBox = $true
$form.BackColor = $UiBackground
$form.ForeColor = $UiText
$form.ShowInTaskbar = $true

$form.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            9
        )
)


# ============================================================
# CABECALHO
# ============================================================

$brandLabel = New-Object `
    System.Windows.Forms.Label

$brandLabel.Text = "RADAR DE OFERTAS"

$brandLabel.Location = (
    New-Object `
        System.Drawing.Point(
            24,
            18
        )
)

$brandLabel.Size = (
    New-Object `
        System.Drawing.Size(
            500,
            32
        )
)

$brandLabel.ForeColor = $UiText

$brandLabel.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            18,
            [System.Drawing.FontStyle]::Bold
        )
)


$centralLabel = New-Object `
    System.Windows.Forms.Label

$centralLabel.Text = "Central de Saude"

$centralLabel.Location = (
    New-Object `
        System.Drawing.Point(
            27,
            52
        )
)

$centralLabel.Size = (
    New-Object `
        System.Drawing.Size(
            300,
            21
        )
)

$centralLabel.ForeColor = $UiMuted

$centralLabel.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            10
        )
)


$summaryLabel = New-Object `
    System.Windows.Forms.Label

$summaryLabel.Text = (
    "Carregando estado do supervisor..."
)

$summaryLabel.Location = (
    New-Object `
        System.Drawing.Point(
            27,
            78
        )
)

$summaryLabel.Size = (
    New-Object `
        System.Drawing.Size(
            650,
            22
        )
)

$summaryLabel.ForeColor = $UiMuted


$overallPanel = New-Object `
    System.Windows.Forms.Panel

$overallPanel.Location = (
    New-Object `
        System.Drawing.Point(
            714,
            18
        )
)

$overallPanel.Size = (
    New-Object `
        System.Drawing.Size(
            222,
            72
        )
)

$overallPanel.BackColor = $UiSurface
$overallPanel.BorderStyle = (
    [System.Windows.Forms.BorderStyle]::FixedSingle
)


$overallCaption = New-Object `
    System.Windows.Forms.Label

$overallCaption.Text = "SAUDE GERAL"

$overallCaption.Location = (
    New-Object `
        System.Drawing.Point(
            14,
            10
        )
)

$overallCaption.Size = (
    New-Object `
        System.Drawing.Size(
            190,
            17
        )
)

$overallCaption.ForeColor = $UiMuted

$overallCaption.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            8,
            [System.Drawing.FontStyle]::Bold
        )
)


$statusLabel = New-Object `
    System.Windows.Forms.Label

$statusLabel.Text = "AGUARDANDO"

$statusLabel.Location = (
    New-Object `
        System.Drawing.Point(
            14,
            30
        )
)

$statusLabel.Size = (
    New-Object `
        System.Drawing.Size(
            190,
            28
        )
)

$statusLabel.ForeColor = $UiMuted

$statusLabel.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            15,
            [System.Drawing.FontStyle]::Bold
        )
)


$overallDetailLabel = New-Object `
    System.Windows.Forms.Label

$overallDetailLabel.Text = "0% saudavel"

$overallDetailLabel.Location = (
    New-Object `
        System.Drawing.Point(
            14,
            54
        )
)

$overallDetailLabel.Size = (
    New-Object `
        System.Drawing.Size(
            190,
            14
        )
)

$overallDetailLabel.ForeColor = $UiMuted

$overallDetailLabel.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            7.5
        )
)


$overallPanel.Controls.Add(
    $overallCaption
)

$overallPanel.Controls.Add(
    $statusLabel
)

$overallPanel.Controls.Add(
    $overallDetailLabel
)


# ============================================================
# DASHBOARD
# ============================================================

$dashboardPanel = New-Object `
    System.Windows.Forms.Panel

$dashboardPanel.Location = (
    New-Object `
        System.Drawing.Point(
            24,
            116
        )
)

$dashboardPanel.Size = (
    New-Object `
        System.Drawing.Size(
            912,
            500
        )
)

$dashboardPanel.BackColor = $UiBackground


$runtimeCard = New-StatusCard `
    -Title "RUNTIME" `
    -X 0 `
    -Y 0

$chromeCard = New-StatusCard `
    -Title "CHROME / CDP" `
    -X 304 `
    -Y 0

$internetCard = New-StatusCard `
    -Title "INTERNET" `
    -X 608 `
    -Y 0

$nodeCard = New-StatusCard `
    -Title "NODE AGENT" `
    -X 0 `
    -Y 104

$socialCard = New-StatusCard `
    -Title "SOCIAL SCOUT" `
    -X 304 `
    -Y 104

$partnerCard = New-StatusCard `
    -Title "PARTNER SCOUT" `
    -X 608 `
    -Y 104


$dashboardPanel.Controls.Add(
    $runtimeCard.Panel
)

$dashboardPanel.Controls.Add(
    $chromeCard.Panel
)

$dashboardPanel.Controls.Add(
    $internetCard.Panel
)

$dashboardPanel.Controls.Add(
    $nodeCard.Panel
)

$dashboardPanel.Controls.Add(
    $socialCard.Panel
)

$dashboardPanel.Controls.Add(
    $partnerCard.Panel
)


# ============================================================
# BARRA DE SAUDE
# ============================================================

$healthPanel = New-Object `
    System.Windows.Forms.Panel

$healthPanel.Location = (
    New-Object `
        System.Drawing.Point(
            0,
            214
        )
)

$healthPanel.Size = (
    New-Object `
        System.Drawing.Size(
            912,
            48
        )
)

$healthPanel.BackColor = $UiSurface


$healthCaption = New-Object `
    System.Windows.Forms.Label

$healthCaption.Text = "SAUDE DOS COMPONENTES"

$healthCaption.Location = (
    New-Object `
        System.Drawing.Point(
            14,
            8
        )
)

$healthCaption.Size = (
    New-Object `
        System.Drawing.Size(
            190,
            18
        )
)

$healthCaption.ForeColor = $UiMuted

$healthCaption.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            8,
            [System.Drawing.FontStyle]::Bold
        )
)


$healthPercentLabel = New-Object `
    System.Windows.Forms.Label

$healthPercentLabel.Text = "0%"

$healthPercentLabel.Location = (
    New-Object `
        System.Drawing.Point(
            830,
            7
        )
)

$healthPercentLabel.Size = (
    New-Object `
        System.Drawing.Size(
            65,
            18
        )
)

$healthPercentLabel.TextAlign = (
    [System.Drawing.ContentAlignment]::MiddleRight
)

$healthPercentLabel.ForeColor = $UiText


$healthTrack = New-Object `
    System.Windows.Forms.Panel

$healthTrack.Location = (
    New-Object `
        System.Drawing.Point(
            14,
            30
        )
)

$healthTrack.Size = (
    New-Object `
        System.Drawing.Size(
            884,
            6
        )
)

$healthTrack.BackColor = $UiBorder


$healthFill = New-Object `
    System.Windows.Forms.Panel

$healthFill.Location = (
    New-Object `
        System.Drawing.Point(
            0,
            0
        )
)

$healthFill.Size = (
    New-Object `
        System.Drawing.Size(
            0,
            6
        )
)

$healthFill.BackColor = $UiGreen

$healthTrack.Controls.Add(
    $healthFill
)

$healthPanel.Controls.Add(
    $healthCaption
)

$healthPanel.Controls.Add(
    $healthPercentLabel
)

$healthPanel.Controls.Add(
    $healthTrack
)

$dashboardPanel.Controls.Add(
    $healthPanel
)


# ============================================================
# RESUMO OPERACIONAL
# ============================================================

$opsPanel = New-Object `
    System.Windows.Forms.Panel

$opsPanel.Location = (
    New-Object `
        System.Drawing.Point(
            0,
            276
        )
)

$opsPanel.Size = (
    New-Object `
        System.Drawing.Size(
            590,
            208
        )
)

$opsPanel.BackColor = $UiSurface
$opsPanel.BorderStyle = (
    [System.Windows.Forms.BorderStyle]::FixedSingle
)


$opsTitle = New-Object `
    System.Windows.Forms.Label

$opsTitle.Text = "RESUMO OPERACIONAL"

$opsTitle.Location = (
    New-Object `
        System.Drawing.Point(
            16,
            14
        )
)

$opsTitle.Size = (
    New-Object `
        System.Drawing.Size(
            300,
            20
        )
)

$opsTitle.ForeColor = $UiText

$opsTitle.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            10,
            [System.Drawing.FontStyle]::Bold
        )
)


function New-InfoRow {
    param(
        [System.Windows.Forms.Control]$Parent,
        [string]$Caption,
        [int]$Y
    )

    $captionLabel = New-Object `
        System.Windows.Forms.Label

    $captionLabel.Text = $Caption

    $captionLabel.Location = (
        New-Object `
            System.Drawing.Point(
                16,
                $Y
            )
    )

    $captionLabel.Size = (
        New-Object `
            System.Drawing.Size(
                185,
                22
            )
    )

    $captionLabel.ForeColor = $UiMuted


    $valueLabel = New-Object `
        System.Windows.Forms.Label

    $valueLabel.Text = "-"

    $valueLabel.Location = (
        New-Object `
            System.Drawing.Point(
                205,
                $Y
            )
    )

    $valueLabel.Size = (
        New-Object `
            System.Drawing.Size(
                360,
                22
            )
    )

    $valueLabel.ForeColor = $UiText
    $valueLabel.AutoEllipsis = $true

    $Parent.Controls.Add(
        $captionLabel
    )

    $Parent.Controls.Add(
        $valueLabel
    )

    return $valueLabel
}


$opsPanel.Controls.Add(
    $opsTitle
)

$uptimeValue = New-InfoRow `
    -Parent $opsPanel `
    -Caption "Uptime Windows" `
    -Y 48

$heartbeatValue = New-InfoRow `
    -Parent $opsPanel `
    -Caption "Ultimo heartbeat" `
    -Y 78

$supervisorValue = New-InfoRow `
    -Parent $opsPanel `
    -Caption "Supervisor iniciou" `
    -Y 108

$recoveryValue = New-InfoRow `
    -Parent $opsPanel `
    -Caption "Auto-Recovery" `
    -Y 138

$networkProofValue = New-InfoRow `
    -Parent $opsPanel `
    -Caption "Rede autonoma" `
    -Y 168


$dashboardPanel.Controls.Add(
    $opsPanel
)


# ============================================================
# PUBLICADOR
# ============================================================

$publisherPanel = New-Object `
    System.Windows.Forms.Panel

$publisherPanel.Location = (
    New-Object `
        System.Drawing.Point(
            608,
            276
        )
)

$publisherPanel.Size = (
    New-Object `
        System.Drawing.Size(
            304,
            208
        )
)

$publisherPanel.BackColor = $UiSurface
$publisherPanel.BorderStyle = (
    [System.Windows.Forms.BorderStyle]::FixedSingle
)


$publisherAccent = New-Object `
    System.Windows.Forms.Panel

$publisherAccent.Location = (
    New-Object `
        System.Drawing.Point(
            0,
            0
        )
)

$publisherAccent.Size = (
    New-Object `
        System.Drawing.Size(
            4,
            208
        )
)

$publisherAccent.BackColor = $UiAmber


$publisherCaption = New-Object `
    System.Windows.Forms.Label

$publisherCaption.Text = "PUBLICADOR"

$publisherCaption.Location = (
    New-Object `
        System.Drawing.Point(
            18,
            15
        )
)

$publisherCaption.Size = (
    New-Object `
        System.Drawing.Size(
            250,
            20
        )
)

$publisherCaption.ForeColor = $UiMuted

$publisherCaption.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            9,
            [System.Drawing.FontStyle]::Bold
        )
)


$publisherStateLabel = New-Object `
    System.Windows.Forms.Label

$publisherStateLabel.Text = "PARADO"

$publisherStateLabel.Location = (
    New-Object `
        System.Drawing.Point(
            18,
            44
        )
)

$publisherStateLabel.Size = (
    New-Object `
        System.Drawing.Size(
            250,
            32
        )
)

$publisherStateLabel.ForeColor = $UiAmber

$publisherStateLabel.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            17,
            [System.Drawing.FontStyle]::Bold
        )
)


$publisherDetailLabel = New-Object `
    System.Windows.Forms.Label

$publisherDetailLabel.Text = (
    "Processo de publicacao nao esta em execucao."
)

$publisherDetailLabel.Location = (
    New-Object `
        System.Drawing.Point(
            18,
            86
        )
)

$publisherDetailLabel.Size = (
    New-Object `
        System.Drawing.Size(
            260,
            48
        )
)

$publisherDetailLabel.ForeColor = $UiMuted


$publisherSafetyLabel = New-Object `
    System.Windows.Forms.Label

$publisherSafetyLabel.Text = (
    "O estado administrativo continua separado " +
    "do monitor de saude."
)

$publisherSafetyLabel.Location = (
    New-Object `
        System.Drawing.Point(
            18,
            145
        )
)

$publisherSafetyLabel.Size = (
    New-Object `
        System.Drawing.Size(
            260,
            45
        )
)

$publisherSafetyLabel.ForeColor = $UiMuted


$publisherPanel.Controls.Add(
    $publisherAccent
)

$publisherPanel.Controls.Add(
    $publisherCaption
)

$publisherPanel.Controls.Add(
    $publisherStateLabel
)

$publisherPanel.Controls.Add(
    $publisherDetailLabel
)

$publisherPanel.Controls.Add(
    $publisherSafetyLabel
)

$dashboardPanel.Controls.Add(
    $publisherPanel
)


# ============================================================
# DETALHES TECNICOS
# ============================================================

$detailsPanel = New-Object `
    System.Windows.Forms.Panel

$detailsPanel.Location = (
    New-Object `
        System.Drawing.Point(
            24,
            116
        )
)

$detailsPanel.Size = (
    New-Object `
        System.Drawing.Size(
            912,
            500
        )
)

$detailsPanel.BackColor = $UiSurface
$detailsPanel.Visible = $false


$detailsTitle = New-Object `
    System.Windows.Forms.Label

$detailsTitle.Text = "DETALHES TECNICOS"

$detailsTitle.Location = (
    New-Object `
        System.Drawing.Point(
            16,
            14
        )
)

$detailsTitle.Size = (
    New-Object `
        System.Drawing.Size(
            400,
            24
        )
)

$detailsTitle.ForeColor = $UiText

$detailsTitle.Font = (
    New-Object `
        System.Drawing.Font(
            "Segoe UI",
            11,
            [System.Drawing.FontStyle]::Bold
        )
)


$detailsBox = New-Object `
    System.Windows.Forms.TextBox

$detailsBox.Location = (
    New-Object `
        System.Drawing.Point(
            16,
            50
        )
)

$detailsBox.Size = (
    New-Object `
        System.Drawing.Size(
            880,
            430
        )
)

$detailsBox.Multiline = $true
$detailsBox.ReadOnly = $true
$detailsBox.ScrollBars = (
    [System.Windows.Forms.ScrollBars]::Vertical
)

$detailsBox.WordWrap = $false
$detailsBox.BackColor = $UiBackground
$detailsBox.ForeColor = $UiText
$detailsBox.BorderStyle = (
    [System.Windows.Forms.BorderStyle]::FixedSingle
)

$detailsBox.Font = (
    New-Object `
        System.Drawing.Font(
            "Consolas",
            9
        )
)

$detailsPanel.Controls.Add(
    $detailsTitle
)

$detailsPanel.Controls.Add(
    $detailsBox
)


# ============================================================
# BOTOES
# ============================================================

function Initialize-DashboardButton {
    param(
        [System.Windows.Forms.Button]$Button,
        [int]$X,
        [int]$Width
    )

    $Button.Location = (
        New-Object `
            System.Drawing.Point(
                $X,
                642
            )
    )

    $Button.Size = (
        New-Object `
            System.Drawing.Size(
                $Width,
                36
            )
    )

    $Button.FlatStyle = (
        [System.Windows.Forms.FlatStyle]::Flat
    )

    $Button.FlatAppearance.BorderColor = $UiBorder
    $Button.FlatAppearance.BorderSize = 1
    $Button.BackColor = $UiSurface2
    $Button.ForeColor = $UiText
}


$refreshButton = New-Object `
    System.Windows.Forms.Button

$refreshButton.Text = "Atualizar agora"

Initialize-DashboardButton `
    -Button $refreshButton `
    -X 24 `
    -Width 140

$refreshButton.BackColor = $UiBlue
$refreshButton.FlatAppearance.BorderColor = $UiBlue


$logButton = New-Object `
    System.Windows.Forms.Button

$logButton.Text = "Abrir log"

Initialize-DashboardButton `
    -Button $logButton `
    -X 176 `
    -Width 130


$heartbeatButton = New-Object `
    System.Windows.Forms.Button

$heartbeatButton.Text = "Abrir heartbeat"

Initialize-DashboardButton `
    -Button $heartbeatButton `
    -X 318 `
    -Width 145


$detailsButton = New-Object `
    System.Windows.Forms.Button

$detailsButton.Text = "Detalhes tecnicos"

Initialize-DashboardButton `
    -Button $detailsButton `
    -X 475 `
    -Width 155


$hideButton = New-Object `
    System.Windows.Forms.Button

$hideButton.Text = "Ocultar"

Initialize-DashboardButton `
    -Button $hideButton `
    -X 800 `
    -Width 136

$hideButton.ForeColor = $UiMuted


$detailsButton.Add_Click({

    if ($detailsPanel.Visible) {
        $detailsPanel.Visible = $false
        $dashboardPanel.Visible = $true
        $detailsButton.Text = "Detalhes tecnicos"
    }
    else {
        $dashboardPanel.Visible = $false
        $detailsPanel.Visible = $true
        $detailsButton.Text = "Visao geral"
    }
})


$form.Controls.Add(
    $brandLabel
)

$form.Controls.Add(
    $centralLabel
)

$form.Controls.Add(
    $summaryLabel
)

$form.Controls.Add(
    $overallPanel
)

$form.Controls.Add(
    $dashboardPanel
)

$form.Controls.Add(
    $detailsPanel
)

$form.Controls.Add(
    $refreshButton
)

$form.Controls.Add(
    $logButton
)

$form.Controls.Add(
    $heartbeatButton
)

$form.Controls.Add(
    $detailsButton
)

$form.Controls.Add(
    $hideButton
)


function Update-DashboardV2 {

    $view = Get-HeartbeatView

    switch ($view.status) {
        "ONLINE" {
            $statusLabel.Text = "ONLINE"
            $statusLabel.ForeColor = $UiGreen
        }

        "DEGRADED" {
            $statusLabel.Text = "ATENCAO"
            $statusLabel.ForeColor = $UiAmber
        }

        default {
            $statusLabel.Text = "OFFLINE"
            $statusLabel.ForeColor = $UiRed
        }
    }

    $summaryLabel.Text = $view.reason


    Set-StatusCard `
        -Card $runtimeCard `
        -State $view.components.runtime `
        -Detail "Executor principal"

    Set-StatusCard `
        -Card $chromeCard `
        -State $view.components.chrome_cdp `
        -Detail "CDP 127.0.0.1:9222"

    $internetState = "OFFLINE"

    if ($view.network_online) {
        $internetState = "HEALTHY"
    }

    Set-StatusCard `
        -Card $internetCard `
        -State $internetState `
        -Detail (
            "Fonte: " +
            [string]$view.network_source
        )

    Set-StatusCard `
        -Card $nodeCard `
        -State $view.components.node_agent `
        -Detail "Telemetria local"

    Set-StatusCard `
        -Card $socialCard `
        -State $view.components.social_scout `
        -Detail "Descoberta social"

    Set-StatusCard `
        -Card $partnerCard `
        -State $view.components.partner_scout `
        -Detail "Fontes parceiras"


    $states = @(
        $view.components.runtime,
        $view.components.chrome_cdp,
        $view.components.node_agent,
        $view.components.social_scout,
        $view.components.partner_scout
    )

    $healthy = @(
        $states |
            Where-Object {
                [string]$_ -eq "HEALTHY"
            }
    ).Count

    if ($view.network_online) {
        $healthy++
    }

    $total = 6

    $percent = [int][Math]::Round(
        (
            $healthy /
            $total
        ) * 100
    )

    $healthPercentLabel.Text = (
        "$percent%"
    )

    $overallDetailLabel.Text = (
        "$percent% saudavel"
    )

    $fillWidth = [int][Math]::Round(
        $healthTrack.Width *
        (
            $percent /
            100
        )
    )

    if ($fillWidth -lt 0) {
        $fillWidth = 0
    }

    if (
        $fillWidth -gt
        $healthTrack.Width
    ) {
        $fillWidth = (
            $healthTrack.Width
        )
    }

    $healthFill.Width = $fillWidth

    if ($percent -ge 100) {
        $healthFill.BackColor = $UiGreen
    }
    elseif ($percent -ge 70) {
        $healthFill.BackColor = $UiAmber
    }
    else {
        $healthFill.BackColor = $UiRed
    }


    $uptimeValue.Text = (
        Get-UptimeText
    )

    $heartbeatValue.Text = (
        Format-Time `
            $view.generated_at
    )

    $supervisorValue.Text = (
        Format-Time `
            $view.supervisor_started_at
    )

    $recoveryValue.Text = (
        (
            [string]$view.autorecovery_mode
        ).ToUpperInvariant()
    )

    if (
        $view.autorecovery_network_autonomy_proven
    ) {
        $networkProofValue.Text = (
            "COMPROVADA"
        )

        $networkProofValue.ForeColor = (
            $UiGreen
        )
    }
    else {
        $networkProofValue.Text = (
            "NAO COMPROVADA"
        )

        $networkProofValue.ForeColor = (
            $UiAmber
        )
    }


    $publisherAdmin = (
        Get-PublicadorAdminState
    )

    $publisherState = (
        Get-PublicadorProcessState
    )

    if (
        $publisherAdmin.RuntimeDisponivel
    ) {
        if (
            $publisherAdmin.Ativo
        ) {
            $publisherState = "ATIVO"
        }
        else {
            $publisherState = "PARADO"
        }
    }

    if (
        $publisherAdmin.Disponivel -and
        $publisherAdmin.Pausado -and
        $publisherState -eq "ATIVO"
    ) {
        $publisherStateLabel.Text = "ATENCAO"
        $publisherStateLabel.ForeColor = $UiRed
        $publisherAccent.BackColor = $UiRed

        $publisherDetailLabel.Text = (
            "Trava administrativa ativa, " +
            "mas o processo ainda esta rodando."
        )
    }
    elseif (
        $publisherAdmin.Disponivel -and
        $publisherAdmin.Pausado
    ) {
        $publisherStateLabel.Text = "PAUSADO"
        $publisherStateLabel.ForeColor = $UiAmber
        $publisherAccent.BackColor = $UiAmber

        $publisherDetailLabel.Text = (
            "Publicacao bloqueada por " +
            "trava administrativa."
        )
    }
    elseif ($publisherState -eq "ATIVO") {
        $publisherStateLabel.Text = "ATIVO"
        $publisherStateLabel.ForeColor = $UiGreen
        $publisherAccent.BackColor = $UiGreen

        $publisherDetailLabel.Text = (
            "Processo de publicacao esta em execucao."
        )
    }
    elseif ($publisherAdmin.Disponivel) {
        $publisherStateLabel.Text = "PARADO"
        $publisherStateLabel.ForeColor = $UiRed
        $publisherAccent.BackColor = $UiRed

        $publisherDetailLabel.Text = (
            "Publicador liberado, mas processo ausente."
        )
    }
    else {
        $publisherStateLabel.Text = "DESCONHECIDO"
        $publisherStateLabel.ForeColor = $UiMuted
        $publisherAccent.BackColor = $UiMuted

        $publisherDetailLabel.Text = (
            "Estado administrativo indisponivel."
        )
    }

    if ($publisherAdmin.Disponivel) {

        $modoTexto = (
            [string]$publisherAdmin.Modo
        ).ToUpperInvariant()

        $filaTexto = "?"

        if (
            $publisherAdmin.Pendentes -ge 0
        ) {
            $filaTexto = (
                [string]$publisherAdmin.Pendentes
            )
        }

        $publisherSafetyLabel.Text = (
            "Modo: " +
            $modoTexto +
            "  |  Fila: " +
            $filaTexto +
            " pendente(s)"
        )
    }
    else {
        $publisherSafetyLabel.Text = (
            "Estado administrativo indisponivel."
        )
    }
}


function Update-Central {
    Update-CentralLegacy
    Update-DashboardV2
}

$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Visible = $true

$menu = New-Object System.Windows.Forms.ContextMenuStrip

$openItem = $menu.Items.Add(
    "Abrir Central de Saude"
)

$menu.Items.Add(
    "-"
) | Out-Null

$heartbeatItem = $menu.Items.Add(
    "Abrir heartbeat"
)

$logItem = $menu.Items.Add(
    "Abrir log do supervisor"
)

$menu.Items.Add(
    "-"
) | Out-Null

$exitItem = $menu.Items.Add(
    "Sair do monitor"
)

$notify.ContextMenuStrip = $menu

$script:CurrentStatus = ""
$script:CurrentIcon = $null
$script:AllowExit = $false

function Show-Central {
    if (-not $form.Visible) {
        $form.Show()
    }

    $form.WindowState = (
        [System.Windows.Forms.FormWindowState]::Normal
    )

    $form.Activate()
}

function Open-Heartbeat {
    if (Test-Path $HeartbeatPath) {
        Start-Process `
            -FilePath "notepad.exe" `
            -ArgumentList "`"$HeartbeatPath`""
    }
    else {
        [System.Windows.Forms.MessageBox]::Show(
            "O heartbeat ainda nao existe.",
            "Renda Automatica",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        ) | Out-Null
    }
}

function Open-SupervisorLog {
    $path = Join-Path `
        $SupervisorLogDirectory `
        (
            "supervisor_{0}.log" -f
            (Get-Date -Format "yyyy-MM-dd")
        )

    if (Test-Path $path) {
        Start-Process `
            -FilePath "notepad.exe" `
            -ArgumentList "`"$path`""
    }
    else {
        [System.Windows.Forms.MessageBox]::Show(
            "O log de hoje ainda nao existe.",
            "Renda Automatica",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        ) | Out-Null
    }
}

function Update-CentralLegacy {
    $view = Get-HeartbeatView

    switch ($view.status) {
        "ONLINE" {
            $statusText = "ONLINE"
        }
        "DEGRADED" {
            $statusText = "DEGRADADO"
        }
        default {
            $statusText = "OFFLINE"
        }
    }

    $statusLabel.Text = (
        "Renda Automatica - {0}" -f
        $statusText
    )

    $summaryLabel.Text = $view.reason

    $explorerStart = Get-ExplorerStart

    $proof = "indisponivel"

    if (
        $null -ne $view.supervisor_started_at -and
        $null -ne $explorerStart
    ) {
        $supervisorLocal = (
            [DateTimeOffset]$view.supervisor_started_at
        ).LocalDateTime

        if ($supervisorLocal -le $explorerStart) {
            $proof = "SIM - supervisor iniciou antes do Explorer"
        }
        else {
            $proof = "NAO - supervisor iniciou depois do Explorer"
        }
    }

    $internetProof = "NAO COMPROVADA"
    $futureRecoveryPolicy = (
        "JANELA SEGURA - horario ainda nao definido"
    )

    if (
        $null -ne $view.network_first_online_at -and
        $null -ne $explorerStart
    ) {
        $networkLocal = (
            [DateTimeOffset]$view.network_first_online_at
        ).LocalDateTime

        if ($networkLocal -le $explorerStart) {
            $internetProof = (
                "SIM - internet ficou online antes do Explorer"
            )

            $futureRecoveryPolicy = (
                "SEM RESTRICAO - rede autonoma comprovada"
            )
        }
        else {
            $internetProof = (
                "NAO - internet ficou online depois do Explorer"
            )
        }
    }

    $internetStatus = "OFFLINE"

    if ($view.network_online) {
        $internetStatus = "ONLINE"
    }

    $heartbeatAge = "-"

    if ($null -ne $view.age_seconds) {
        $heartbeatAge = (
            "{0}s" -f
            $view.age_seconds
        )
    }

    $supervisorState = "UNKNOWN"

    if ($view.status -ne "OFFLINE") {
        $supervisorState = "HEALTHY"
    }

    $explorerText = "-"

    if ($explorerStart) {
        $explorerText = (
            $explorerStart.ToString(
                "dd/MM/yyyy HH:mm:ss"
            )
        )
    }

    $lines = @(
        "Status geral:          $statusText"
        "Uptime Windows:        $(Get-UptimeText)"
        "Supervisor iniciou:    $(Format-Time $view.supervisor_started_at)"
        "Explorer iniciou:      $explorerText"
        "Antes do login GUI:    $proof"
        "Identidade:            $($view.identity)"
        "Session ID:            $($view.session_id)"
        "Ultimo heartbeat:      $(Format-Time $view.generated_at)"
        "Idade heartbeat:       $heartbeatAge"
        ""
        "REDE / RECUPERACAO"
        "--------------------------------------------------"
        "Internet atual:        $internetStatus"
        "Rede verificada em:    $(Format-Time $view.network_checked_at)"
        "1a conexao pos-boot:   $(Format-Time $view.network_first_online_at)"
        "Antes do login GUI:    $internetProof"
        "Fonte:                 $($view.network_source)"
        "Politica futura:       $futureRecoveryPolicy"
        ""
        "AUTO-RECOVERY"
        "--------------------------------------------------"
        "Modo:                  $($view.autorecovery_mode)"
        "Estado:                $($view.autorecovery_status)"
        "Ciclos degradados:     $($view.autorecovery_cycles)"
        "Restarts supervisor:   $($view.autorecovery_supervisor_restarts)"
        "Acao recomendada:      $($view.autorecovery_recommended_action)"
        "Degradados:            $(@($view.autorecovery_degraded_components) -join ', ')"
        "Incidente iniciou:     $(Format-Time $view.autorecovery_incident_started_at)"
        "Ultima acao:           $($view.autorecovery_last_action)"
        "Ultima acao em:        $(Format-Time $view.autorecovery_last_action_at)"
        "Ultima recuperacao:    $(Format-Time $view.autorecovery_last_recovered_at)"
        "Lockout reboot ate:    $(Format-Time $view.autorecovery_reboot_lockout_until)"
        "Rede autonoma provada: $($view.autorecovery_network_autonomy_proven)"
        ""
        "COMPONENTES"
        "--------------------------------------------------"
        (Format-Component "Supervisor" $supervisorState)
        (Format-Component "Runtime" $view.components.runtime)
        (Format-Component "Social Scout" $view.components.social_scout)
        (Format-Component "Partner Scout" $view.components.partner_scout)
        (Format-Component "Node Agent" $view.components.node_agent)
        (Format-Component "Chrome/CDP" $view.components.chrome_cdp)
        ""
        "Heartbeat:"
        $HeartbeatPath
    )

    $detailsBox.Text = (
        $lines -join [Environment]::NewLine
    )

    $notify.Text = (
        "Renda Automatica - {0}" -f
        $statusText
    )

    if ($script:CurrentStatus -ne $view.status) {
        $newIcon = New-StatusIcon `
            -Status $view.status

        $oldIcon = $script:CurrentIcon

        $script:CurrentIcon = $newIcon
        $notify.Icon = $newIcon

        if ($null -ne $oldIcon) {
            $oldIcon.Dispose()
        }

        if ($script:CurrentStatus -ne "") {
            $notify.BalloonTipTitle = (
                "Renda Automatica - " +
                $statusText
            )

            $notify.BalloonTipText = $view.reason
            $notify.ShowBalloonTip(3000)
        }

        $script:CurrentStatus = $view.status
    }
}

$refreshButton.Add_Click({
    Update-Central
})

$logButton.Add_Click({
    Open-SupervisorLog
})

$heartbeatButton.Add_Click({
    Open-Heartbeat
})

$hideButton.Add_Click({
    $form.Hide()
})

$openItem.Add_Click({
    Show-Central
})

$heartbeatItem.Add_Click({
    Open-Heartbeat
})

$logItem.Add_Click({
    Open-SupervisorLog
})

$exitItem.Add_Click({
    $script:AllowExit = $true
    $form.Close()
    $notify.Visible = $false
    [System.Windows.Forms.Application]::Exit()
})

$notify.Add_DoubleClick({
    Show-Central
})

$form.Add_FormClosing({
    param(
        $sender,
        $eventArgs
    )

    if (-not $script:AllowExit) {
        $eventArgs.Cancel = $true
        $form.Hide()
    }
})

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 5000

$timer.Add_Tick({
    Update-Central
})

try {
    $script:CurrentIcon = New-StatusIcon `
        -Status "UNKNOWN"

    $notify.Icon = $script:CurrentIcon
    $notify.Text = "Renda Automatica - verificando"

    Update-Central

    $timer.Start()

    $notify.BalloonTipTitle = (
        "Renda Automatica"
    )

    $notify.BalloonTipText = (
        "Central de Saude iniciada."
    )

    $notify.ShowBalloonTip(2500)

    [System.Windows.Forms.Application]::Run()
}
finally {
    $timer.Stop()
    $timer.Dispose()

    $notify.Visible = $false
    $notify.Dispose()

    if ($null -ne $script:CurrentIcon) {
        $script:CurrentIcon.Dispose()
    }

    $form.Dispose()

    if ($null -ne $mutex) {
        $mutex.ReleaseMutex()
        $mutex.Dispose()
    }
}
