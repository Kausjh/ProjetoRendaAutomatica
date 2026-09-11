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

$form = New-Object System.Windows.Forms.Form
$form.Text = "Renda Automatica - Central de Saude"
$form.Size = New-Object System.Drawing.Size(590, 570)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $true
$form.ShowInTaskbar = $false

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(20, 18)
$statusLabel.Size = New-Object System.Drawing.Size(540, 44)
$statusLabel.Font = New-Object System.Drawing.Font(
    "Segoe UI",
    20,
    [System.Drawing.FontStyle]::Bold
)

$summaryLabel = New-Object System.Windows.Forms.Label
$summaryLabel.Location = New-Object System.Drawing.Point(22, 68)
$summaryLabel.Size = New-Object System.Drawing.Size(535, 42)
$summaryLabel.Font = New-Object System.Drawing.Font(
    "Segoe UI",
    10
)

$detailsBox = New-Object System.Windows.Forms.TextBox
$detailsBox.Location = New-Object System.Drawing.Point(22, 120)
$detailsBox.Size = New-Object System.Drawing.Size(535, 340)
$detailsBox.Multiline = $true
$detailsBox.ReadOnly = $true
$detailsBox.ScrollBars = "Vertical"
$detailsBox.Font = New-Object System.Drawing.Font(
    "Consolas",
    10
)
$detailsBox.BackColor = [System.Drawing.Color]::White

$refreshButton = New-Object System.Windows.Forms.Button
$refreshButton.Text = "Atualizar agora"
$refreshButton.Location = New-Object System.Drawing.Point(22, 480)
$refreshButton.Size = New-Object System.Drawing.Size(130, 32)

$logButton = New-Object System.Windows.Forms.Button
$logButton.Text = "Abrir log"
$logButton.Location = New-Object System.Drawing.Point(164, 480)
$logButton.Size = New-Object System.Drawing.Size(110, 32)

$heartbeatButton = New-Object System.Windows.Forms.Button
$heartbeatButton.Text = "Abrir heartbeat"
$heartbeatButton.Location = New-Object System.Drawing.Point(286, 480)
$heartbeatButton.Size = New-Object System.Drawing.Size(130, 32)

$hideButton = New-Object System.Windows.Forms.Button
$hideButton.Text = "Ocultar"
$hideButton.Location = New-Object System.Drawing.Point(428, 480)
$hideButton.Size = New-Object System.Drawing.Size(130, 32)

$form.Controls.AddRange(@(
    $statusLabel,
    $summaryLabel,
    $detailsBox,
    $refreshButton,
    $logButton,
    $heartbeatButton,
    $hideButton
))

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

function Update-Central {
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
