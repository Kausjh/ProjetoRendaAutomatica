$ErrorActionPreference = "Stop"

function New-DefaultAutoRecoveryPolicy {
    return [pscustomobject]@{
        schema_version = 1
        enabled = $false
        mode = "observe_only"
        consecutive_degraded_cycles_before_supervisor_restart = 3
        supervisor_restart_limit_per_incident = 1
        reboot_cooldown_hours = 6
        max_auto_reboots_per_cooldown = 1
        auto_reboot_enabled = $false
    }
}

function Get-AutoRecoveryPolicy {
    param(
        [string]$PolicyPath
    )

    if (-not (Test-Path $PolicyPath)) {
        return (New-DefaultAutoRecoveryPolicy)
    }

    try {
        $policy = Get-Content `
            -LiteralPath $PolicyPath `
            -Raw |
            ConvertFrom-Json
    }
    catch {
        return (New-DefaultAutoRecoveryPolicy)
    }

    if ($null -eq $policy) {
        return (New-DefaultAutoRecoveryPolicy)
    }

    return $policy
}

function New-AutoRecoveryState {
    return [ordered]@{
        schema_version = 1
        updated_at = $null
        status = "INITIALIZING"
        execution_mode = "observe_only"
        incident_started_at = $null
        consecutive_degraded_cycles = 0
        supervisor_restarts_this_incident = 0
        degraded_components = @()
        network_online = $false
        network_autonomy_proven = $false
        recommended_action = "NONE"
        last_action = "NONE"
        last_action_at = $null
        last_reason = $null
        last_recovered_at = $null
        last_auto_reboot_at = $null
        reboot_lockout_until = $null
    }
}

function Get-AutoRecoveryState {
    param(
        [string]$StatePath
    )

    $default = New-AutoRecoveryState

    if (-not (Test-Path $StatePath)) {
        return $default
    }

    try {
        $raw = Get-Content `
            -LiteralPath $StatePath `
            -Raw |
            ConvertFrom-Json
    }
    catch {
        return $default
    }

    foreach ($name in @(
        "updated_at",
        "status",
        "execution_mode",
        "incident_started_at",
        "consecutive_degraded_cycles",
        "supervisor_restarts_this_incident",
        "degraded_components",
        "network_online",
        "network_autonomy_proven",
        "recommended_action",
        "last_action",
        "last_action_at",
        "last_reason",
        "last_recovered_at",
        "last_auto_reboot_at",
        "reboot_lockout_until"
    )) {
        if ($raw.PSObject.Properties.Name -contains $name) {
            $default[$name] = $raw.$name
        }
    }

    return $default
}

function Save-AutoRecoveryState {
    param(
        [System.Collections.IDictionary]$State,
        [string]$StatePath
    )

    $directory = Split-Path `
        -Parent `
        $StatePath

    if (-not (Test-Path $directory)) {
        New-Item `
            -ItemType Directory `
            -Path $directory `
            -Force |
            Out-Null
    }

    $temp = (
        $StatePath +
        ".tmp." +
        $PID
    )

    $State |
        ConvertTo-Json -Depth 6 |
        Set-Content `
            -LiteralPath $temp `
            -Encoding UTF8

    Move-Item `
        -LiteralPath $temp `
        -Destination $StatePath `
        -Force
}

function Test-NetworkAutonomyProof {
    param(
        [string]$ProofPath
    )

    if (-not (Test-Path $ProofPath)) {
        return $false
    }

    try {
        $proof = Get-Content `
            -LiteralPath $ProofPath `
            -Raw |
            ConvertFrom-Json

        return (
            ([bool]$proof.proven) -and
            [string]$proof.method -eq "pre_login_boot_test"
        )
    }
    catch {
        return $false
    }
}

function Get-AutoRecoveryDegradedComponents {
    param(
        [System.Collections.IDictionary]$ComponentStates
    )

    return @(
        $ComponentStates.Keys |
            Where-Object {
                [string]$ComponentStates[$_] -ne "HEALTHY"
            } |
            Sort-Object
    )
}

function Update-AutoRecoveryController {
    param(
        [System.Collections.IDictionary]$ComponentStates,
        [bool]$NetworkOnline,
        [string]$PolicyPath,
        [string]$StatePath,
        [string]$ProofPath
    )

    $now = [DateTimeOffset]::Now

    $policy = Get-AutoRecoveryPolicy `
        -PolicyPath $PolicyPath

    $state = Get-AutoRecoveryState `
        -StatePath $StatePath

    $degraded = @(
        Get-AutoRecoveryDegradedComponents `
            -ComponentStates $ComponentStates
    )

    $state["updated_at"] = $now.ToString("o")
    $state["execution_mode"] = [string]$policy.mode
    $state["network_online"] = $NetworkOnline
    $state["network_autonomy_proven"] = (
        Test-NetworkAutonomyProof `
            -ProofPath $ProofPath
    )
    $state["degraded_components"] = $degraded

    if (-not ([bool]$policy.enabled)) {
        $state["status"] = "DISABLED"
        $state["recommended_action"] = "NONE"
        $state["last_reason"] = "Auto-Recovery desabilitado pela policy."

        Save-AutoRecoveryState `
            -State $state `
            -StatePath $StatePath

        return [pscustomobject]$state
    }

    if ($degraded.Count -eq 0) {
        if ($state["incident_started_at"]) {
            $state["last_recovered_at"] = $now.ToString("o")
        }

        $state["status"] = "HEALTHY"
        $state["incident_started_at"] = $null
        $state["consecutive_degraded_cycles"] = 0
        $state["supervisor_restarts_this_incident"] = 0
        $state["recommended_action"] = "NONE"
        $state["last_reason"] = $null
        $state["reboot_lockout_until"] = $null

        Save-AutoRecoveryState `
            -State $state `
            -StatePath $StatePath

        return [pscustomobject]$state
    }

    if (-not $state["incident_started_at"]) {
        $state["incident_started_at"] = $now.ToString("o")
    }

    $cycles = (
        [int]$state["consecutive_degraded_cycles"] +
        1
    )

    $state["consecutive_degraded_cycles"] = $cycles
    $state["last_reason"] = (
        "Componentes degradados: " +
        ($degraded -join ", ")
    )

    $threshold = [int](
        $policy.consecutive_degraded_cycles_before_supervisor_restart
    )

    if ($threshold -lt 1) {
        $threshold = 1
    }

    if ($cycles -lt $threshold) {
        $state["status"] = "LOCAL_RECOVERY"
        $state["recommended_action"] = "LOCAL_RECOVERY"

        Save-AutoRecoveryState `
            -State $state `
            -StatePath $StatePath

        return [pscustomobject]$state
    }

    $restartLimit = [int](
        $policy.supervisor_restart_limit_per_incident
    )

    if (
        [int]$state["supervisor_restarts_this_incident"] -lt
        $restartLimit
    ) {
        if ([string]$policy.mode -eq "observe_only") {
            $state["status"] = "WOULD_RESTART_SUPERVISOR"
        }
        else {
            $state["status"] = "RESTART_SUPERVISOR_PENDING"
        }

        $state["recommended_action"] = "RESTART_SUPERVISOR"

        Save-AutoRecoveryState `
            -State $state `
            -StatePath $StatePath

        return [pscustomobject]$state
    }

    if (-not $NetworkOnline) {
        $state["status"] = "WAITING_NETWORK"
        $state["recommended_action"] = "WAIT"
        $state["last_reason"] = (
            "Falha persistente, mas a rede esta offline. " +
            "Reboot agressivo bloqueado."
        )

        Save-AutoRecoveryState `
            -State $state `
            -StatePath $StatePath

        return [pscustomobject]$state
    }

    if (-not ([bool]$state["network_autonomy_proven"])) {
        $state["status"] = "REBOOT_BLOCKED_NETWORK_AUTONOMY"
        $state["recommended_action"] = "WAIT"
        $state["last_reason"] = (
            "Reboot bloqueado: autonomia de rede " +
            "pos-boot nao esta comprovada."
        )

        Save-AutoRecoveryState `
            -State $state `
            -StatePath $StatePath

        return [pscustomobject]$state
    }

    $cooldownHours = [double](
        $policy.reboot_cooldown_hours
    )

    if ($cooldownHours -lt 1) {
        $cooldownHours = 1
    }

    if ($state["last_auto_reboot_at"]) {
        try {
            $lastReboot = [DateTimeOffset]::Parse(
                [string]$state["last_auto_reboot_at"]
            )

            $lockoutUntil = $lastReboot.AddHours(
                $cooldownHours
            )

            if ($now -lt $lockoutUntil) {
                $state["status"] = "REBOOT_LOCKOUT"
                $state["recommended_action"] = "WAIT"
                $state["reboot_lockout_until"] = (
                    $lockoutUntil.ToString("o")
                )
                $state["last_reason"] = (
                    "Novo reboot bloqueado pelo cooldown anti-loop."
                )

                Save-AutoRecoveryState `
                    -State $state `
                    -StatePath $StatePath

                return [pscustomobject]$state
            }
        }
        catch {
            $state["last_auto_reboot_at"] = $null
        }
    }

    if (
        [string]$policy.mode -eq "observe_only" -or
        -not ([bool]$policy.auto_reboot_enabled)
    ) {
        $state["status"] = "WOULD_REBOOT"
    }
    else {
        $state["status"] = "REBOOT_PENDING"
    }

    $state["recommended_action"] = "REBOOT"

    Save-AutoRecoveryState `
        -State $state `
        -StatePath $StatePath

    return [pscustomobject]$state
}

function Register-AutoRecoveryAction {
    param(
        [ValidateSet(
            "RESTART_SUPERVISOR",
            "REBOOT"
        )]
        [string]$Action,
        [string]$StatePath
    )

    $now = [DateTimeOffset]::Now

    $state = Get-AutoRecoveryState `
        -StatePath $StatePath

    $state["last_action"] = $Action
    $state["last_action_at"] = $now.ToString("o")
    $state["consecutive_degraded_cycles"] = 0

    if ($Action -eq "RESTART_SUPERVISOR") {
        $state["supervisor_restarts_this_incident"] = (
            [int]$state["supervisor_restarts_this_incident"] +
            1
        )
        $state["status"] = "SUPERVISOR_RESTART_RECORDED"
    }

    if ($Action -eq "REBOOT") {
        $state["last_auto_reboot_at"] = $now.ToString("o")
        $state["status"] = "AUTO_REBOOT_RECORDED"
    }

    $state["updated_at"] = $now.ToString("o")

    Save-AutoRecoveryState `
        -State $state `
        -StatePath $StatePath

    return [pscustomobject]$state
}
