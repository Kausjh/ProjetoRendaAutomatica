$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Projetos\ProjetoRendaAutomatica"
$MainTaskName = "RendaAutomatica"

$HealthDirectory = Join-Path `
    $env:ProgramData `
    "ProjetoRendaAutomatica\health"

$WatchdogStatePath = Join-Path `
    $HealthDirectory `
    "supervisor_watchdog_state.json"

$LogDirectory = Join-Path `
    $env:ProgramData `
    "ProjetoRendaAutomatica\logs\watchdog"

$CheckIntervalSeconds = 15
$MissingCyclesBeforeRecovery = 2
$PostStartWaitSeconds = 8
$ZombieTaskGraceCycles = 2

$MutexName = "Global\ProjetoRendaAutomaticaSupervisorWatchdog"

New-Item `
    -ItemType Directory `
    -Path $HealthDirectory `
    -Force |
    Out-Null

New-Item `
    -ItemType Directory `
    -Path $LogDirectory `
    -Force |
    Out-Null

$mutex = New-Object `
    System.Threading.Mutex(
        $false,
        $MutexName
    )

$ownsMutex = $false

try {
    $ownsMutex = $mutex.WaitOne(
        0,
        $false
    )
}
catch [System.Threading.AbandonedMutexException] {
    $ownsMutex = $true
}

if (-not $ownsMutex) {
    exit 0
}

function Write-WatchdogLog {
    param(
        [ValidateSet(
            "INFO",
            "WARNING",
            "ERROR"
        )]
        [string]$Level,

        [string]$Message
    )

    $logPath = Join-Path `
        $LogDirectory `
        ("watchdog_{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

    $line = "{0} | {1} | {2}" -f `
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), `
        $Level, `
        $Message

    Add-Content `
        -LiteralPath $logPath `
        -Value $line `
        -Encoding UTF8
}

function Write-WatchdogState {
    param(
        [string]$Status,
        [int]$SupervisorCount,
        [string]$TaskState,
        [int]$MissingCycles,
        [int]$RecoveryAttempts,
        [string]$LastAction,
        [AllowNull()]
        [string]$LastRecoveryAt,
        [AllowNull()]
        [string]$LastError
    )

    $payload = [ordered]@{
        schema_version = 1
        generated_at = (Get-Date).ToString("o")
        status = $Status
        supervisor_count = $SupervisorCount
        task_state = $TaskState
        missing_cycles = $MissingCycles
        recovery_attempts = $RecoveryAttempts
        last_action = $LastAction
        last_recovery_at = $LastRecoveryAt
        last_error = $LastError
        watchdog_pid = $PID
        identity = (
            [Security.Principal.WindowsIdentity]::GetCurrent().Name
        )
        session_id = (
            [System.Diagnostics.Process]::GetCurrentProcess().SessionId
        )
    }

    $tempPath = (
        $WatchdogStatePath +
        ".tmp." +
        $PID
    )

    $payload |
        ConvertTo-Json -Depth 6 |
        Set-Content `
            -LiteralPath $tempPath `
            -Encoding UTF8

    Move-Item `
        -LiteralPath $tempPath `
        -Destination $WatchdogStatePath `
        -Force
}

function Get-SupervisorProcesses {
    return @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -match "^(powershell|pwsh)\.exe$" -and
                $_.CommandLine -and
                $_.CommandLine -like (
                    "*supervisor_renda_automatica.ps1*"
                )
            }
    )
}

function Get-MainTaskState {
    try {
        $task = Get-ScheduledTask `
            -TaskName $MainTaskName `
            -ErrorAction Stop

        return [string]$task.State
    }
    catch {
        return "UNKNOWN"
    }
}

function Start-MainTaskRecovery {
    param(
        [int]$RecoveryAttempt
    )

    Write-WatchdogLog `
        -Level "WARNING" `
        -Message (
            "Supervisor ausente. Solicitando Start-ScheduledTask | " +
            "tentativa={0}" -f
            $RecoveryAttempt
        )

    try {
        Start-ScheduledTask `
            -TaskName $MainTaskName `
            -ErrorAction Stop
    }
    catch {
        Write-WatchdogLog `
            -Level "ERROR" `
            -Message (
                "Start-ScheduledTask falhou: " +
                $_.Exception.Message
            )

        return [pscustomobject]@{
            recovered = $false
            action = "START_TASK_FAILED"
            error = $_.Exception.Message
        }
    }

    Start-Sleep -Seconds $PostStartWaitSeconds

    $supervisors = @(Get-SupervisorProcesses)

    if ($supervisors.Count -eq 1) {
        return [pscustomobject]@{
            recovered = $true
            action = "START_TASK"
            error = $null
        }
    }

    $taskState = Get-MainTaskState

    if ($taskState -eq "Running") {
        Write-WatchdogLog `
            -Level "WARNING" `
            -Message (
                "Task reporta Running sem supervisor. " +
                "Aplicando reset controlado da task."
            )

        try {
            Stop-ScheduledTask `
                -TaskName $MainTaskName `
                -ErrorAction Stop

            Start-Sleep -Seconds 2

            Start-ScheduledTask `
                -TaskName $MainTaskName `
                -ErrorAction Stop

            Start-Sleep -Seconds $PostStartWaitSeconds
        }
        catch {
            Write-WatchdogLog `
                -Level "ERROR" `
                -Message (
                    "Reset controlado da task falhou: " +
                    $_.Exception.Message
                )

            return [pscustomobject]@{
                recovered = $false
                action = "RESET_TASK_FAILED"
                error = $_.Exception.Message
            }
        }

        $supervisors = @(Get-SupervisorProcesses)

        if ($supervisors.Count -eq 1) {
            return [pscustomobject]@{
                recovered = $true
                action = "RESET_TASK"
                error = $null
            }
        }
    }

    return [pscustomobject]@{
        recovered = $false
        action = "START_TASK_NO_SUPERVISOR"
        error = $null
    }
}

$missingCycles = 0
$recoveryAttempts = 0
$lastRecoveryAt = $null
$lastAction = "NONE"

Write-WatchdogLog `
    -Level "INFO" `
    -Message (
        "Watchdog iniciado | identidade={0} | sessao={1} | pid={2}" -f
        (
            [Security.Principal.WindowsIdentity]::GetCurrent().Name
        ),
        (
            [System.Diagnostics.Process]::GetCurrentProcess().SessionId
        ),
        $PID
    )

try {
    while ($true) {
        try {
            $supervisors = @(Get-SupervisorProcesses)
            $supervisorCount = $supervisors.Count
            $taskState = Get-MainTaskState

            if ($supervisorCount -eq 1) {
                if ($missingCycles -gt 0) {
                    Write-WatchdogLog `
                        -Level "INFO" `
                        -Message "Supervisor voltou a ficar disponivel."
                }

                $missingCycles = 0
                $recoveryAttempts = 0
                $lastAction = "NONE"

                Write-WatchdogState `
                    -Status "HEALTHY" `
                    -SupervisorCount 1 `
                    -TaskState $taskState `
                    -MissingCycles 0 `
                    -RecoveryAttempts 0 `
                    -LastAction $lastAction `
                    -LastRecoveryAt $lastRecoveryAt `
                    -LastError $null
            }
            elseif ($supervisorCount -eq 0) {
                $missingCycles++

                if (
                    $missingCycles -lt
                    $MissingCyclesBeforeRecovery
                ) {
                    Write-WatchdogState `
                        -Status "DEGRADED" `
                        -SupervisorCount 0 `
                        -TaskState $taskState `
                        -MissingCycles $missingCycles `
                        -RecoveryAttempts $recoveryAttempts `
                        -LastAction "WAITING_GRACE" `
                        -LastRecoveryAt $lastRecoveryAt `
                        -LastError $null
                }
                else {
                    $recoveryAttempts++

                    Write-WatchdogState `
                        -Status "RECOVERING" `
                        -SupervisorCount 0 `
                        -TaskState $taskState `
                        -MissingCycles $missingCycles `
                        -RecoveryAttempts $recoveryAttempts `
                        -LastAction "START_TASK" `
                        -LastRecoveryAt $lastRecoveryAt `
                        -LastError $null

                    $result = Start-MainTaskRecovery `
                        -RecoveryAttempt $recoveryAttempts

                    $lastAction = [string]$result.action

                    if ([bool]$result.recovered) {
                        $lastRecoveryAt = (Get-Date).ToString("o")

                        Write-WatchdogLog `
                            -Level "INFO" `
                            -Message (
                                "Supervisor recuperado | acao={0}" -f
                                $lastAction
                            )

                        $missingCycles = 0
                        $recoveryAttempts = 0

                        Write-WatchdogState `
                            -Status "HEALTHY" `
                            -SupervisorCount 1 `
                            -TaskState (Get-MainTaskState) `
                            -MissingCycles 0 `
                            -RecoveryAttempts 0 `
                            -LastAction $lastAction `
                            -LastRecoveryAt $lastRecoveryAt `
                            -LastError $null
                    }
                    else {
                        Write-WatchdogState `
                            -Status "DEGRADED" `
                            -SupervisorCount 0 `
                            -TaskState (Get-MainTaskState) `
                            -MissingCycles $missingCycles `
                            -RecoveryAttempts $recoveryAttempts `
                            -LastAction $lastAction `
                            -LastRecoveryAt $lastRecoveryAt `
                            -LastError ([string]$result.error)
                    }
                }
            }
            else {
                Write-WatchdogLog `
                    -Level "ERROR" `
                    -Message (
                        "Mais de um supervisor detectado | count={0}" -f
                        $supervisorCount
                    )

                Write-WatchdogState `
                    -Status "DEGRADED" `
                    -SupervisorCount $supervisorCount `
                    -TaskState $taskState `
                    -MissingCycles $missingCycles `
                    -RecoveryAttempts $recoveryAttempts `
                    -LastAction "MULTIPLE_SUPERVISORS" `
                    -LastRecoveryAt $lastRecoveryAt `
                    -LastError "Mais de um supervisor detectado."
            }
        }
        catch {
            Write-WatchdogLog `
                -Level "ERROR" `
                -Message (
                    "Ciclo watchdog falhou: " +
                    $_.Exception.Message
                )

            Write-WatchdogState `
                -Status "DEGRADED" `
                -SupervisorCount 0 `
                -TaskState "UNKNOWN" `
                -MissingCycles $missingCycles `
                -RecoveryAttempts $recoveryAttempts `
                -LastAction "WATCHDOG_ERROR" `
                -LastRecoveryAt $lastRecoveryAt `
                -LastError $_.Exception.Message
        }

        Start-Sleep -Seconds $CheckIntervalSeconds
    }
}
finally {
    if ($ownsMutex) {
        $mutex.ReleaseMutex()
    }

    $mutex.Dispose()
}
