# 63.8738, -149.7525

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$RuntimeScript = Join-Path $ProjectRoot "runtime.py"
$ListenerScript = Join-Path $ProjectRoot "social_scout_telegram.py"
$NodeAgentScript = Join-Path $ProjectRoot "node_agent.py"
$PartnerScoutScript = Join-Path $ProjectRoot "partner_scout.py"
$ChromeProfile = Join-Path $ProjectRoot "browser_profile_cdp"
$CdpEndpoint = "http://127.0.0.1:9222/json/version"
$SupervisorLogDirectory = Join-Path $ProjectRoot "logs\supervisor"

$ManagedScriptRegex = (
    "runtime\.py|" +
    "bot_consulta\.py|" +
    "publicador_fila\.py|" +
    "services[\\/]launcher[\\/]chrome_launcher\.py|" +
    "[\\/]main\.py"
)

$ComponentStates = @{}

$CurrentIdentity = (
    [Security.Principal.WindowsIdentity]::GetCurrent().Name
)

$CurrentSessionId = (
    Get-Process -Id $PID
).SessionId

$RunChromeHeadless = (
    $CurrentIdentity -ieq "NT AUTHORITY\SYSTEM" -or
    $CurrentSessionId -eq 0
)

Set-Location $ProjectRoot

New-Item `
    -ItemType Directory `
    -Path $SupervisorLogDirectory `
    -Force |
    Out-Null


function Write-SupervisorLog {
    param(
        [ValidateSet("INFO", "WARNING", "ERROR")]
        [string]$Level,
        [string]$Message
    )

    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $logFile = Join-Path `
        $SupervisorLogDirectory `
        ("supervisor_{0}.log" -f (Get-Date).ToString("yyyy-MM-dd"))

    $line = "{0} | {1} | {2}" -f $timestamp, $Level, $Message

    Add-Content `
        -LiteralPath $logFile `
        -Value $line `
        -Encoding UTF8

    Write-Host $line
}


function Set-ComponentState {
    param(
        [string]$Name,
        [string]$State,
        [string]$Detail = ""
    )

    $previous = $ComponentStates[$Name]

    if ($previous -eq $State) {
        return
    }

    $ComponentStates[$Name] = $State

    $message = "{0} => {1}" -f $Name, $State

    if ($Detail) {
        $message = "{0} | {1}" -f $message, $Detail
    }

    $level = "INFO"

    if ($State -eq "DEGRADED") {
        $level = "WARNING"
    }

    Write-SupervisorLog `
        -Level $level `
        -Message $message
}


function Get-ProjectPythonProcess {
    param(
        [string]$ScriptPath
    )

    $result = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -match "^python(w)?\.exe$" -and
                $_.CommandLine -and
                $_.CommandLine -like "*$ProjectRoot*" -and
                $_.CommandLine -like "*$ScriptPath*"
            }
    )

    return $result
}


function Get-ProjectProcess {
    param(
        [string]$ScriptPath
    )

    $processes = @(
        Get-ProjectPythonProcess `
            -ScriptPath $ScriptPath
    )

    if ($processes.Count -eq 0) {
        return @()
    }

    $ids = @($processes.ProcessId)

    return @(
        $processes |
            Where-Object {
                $_.ParentProcessId -notin $ids
            }
    )
}


function Get-ManagedProjectPythonProcess {
    return @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -match "^python(w)?\.exe$" -and
                $_.CommandLine -and
                $_.CommandLine -like "*$ProjectRoot*" -and
                $_.CommandLine -match $ManagedScriptRegex
            }
    )
}


function Get-ManagedProjectRootProcess {
    $processes = @(
        Get-ManagedProjectPythonProcess
    )

    if ($processes.Count -eq 0) {
        return @()
    }

    $ids = @($processes.ProcessId)

    return @(
        $processes |
            Where-Object {
                $_.ParentProcessId -notin $ids
            }
    )
}


function Stop-ProjectProcessTree {
    param(
        [int]$ProcessId,
        [string]$Description
    )

    $process = Get-CimInstance `
        Win32_Process `
        -Filter "ProcessId=$ProcessId" `
        -ErrorAction SilentlyContinue

    if ($null -eq $process) {
        return
    }

    Write-SupervisorLog `
        -Level "INFO" `
        -Message (
            "Encerrando arvore antiga: {0} | PID {1}" -f
            $Description,
            $ProcessId
        )

    & taskkill.exe /PID $ProcessId /T /F | Out-Null
}


function Stop-StaleManagedProjectTrees {
    Write-SupervisorLog `
        -Level "INFO" `
        -Message (
            "Verificando componentes operacionais orfaos " +
            "de execucoes anteriores."
        )

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $processes = @(
            Get-ManagedProjectPythonProcess
        )

        if ($processes.Count -eq 0) {
            Write-SupervisorLog `
                -Level "INFO" `
                -Message (
                    "Nenhuma arvore operacional antiga permanece ativa."
                )

            return
        }

        $roots = @(
            Get-ManagedProjectRootProcess
        )

        if ($roots.Count -eq 0) {
            throw (
                "Existem processos gerenciados antigos, " +
                "mas nenhuma raiz segura foi identificada."
            )
        }

        foreach ($root in $roots) {
            Stop-ProjectProcessTree `
                -ProcessId $root.ProcessId `
                -Description $root.CommandLine
        }

        Start-Sleep -Seconds 1
    }

    $remaining = @(
        Get-ManagedProjectPythonProcess
    )

    if ($remaining.Count -ne 0) {
        throw (
            "Nao foi possivel remover completamente as " +
            "arvores operacionais antigas."
        )
    }

    Write-SupervisorLog `
        -Level "INFO" `
        -Message "Arvores operacionais antigas removidas com sucesso."
}


function Ensure-SingleProjectProcess {
    param(
        [string]$ScriptName,
        [string]$ScriptPath
    )

    $processes = @(
        Get-ProjectProcess `
            -ScriptPath $ScriptPath
    )

    if ($processes.Count -gt 1) {
        $ordered = @(
            $processes |
                Sort-Object CreationDate, ProcessId
        )

        foreach ($extra in @($ordered | Select-Object -Skip 1)) {
            Stop-ProjectProcessTree `
                -ProcessId $extra.ProcessId `
                -Description "instancia duplicada de $ScriptName"
        }

        Start-Sleep -Seconds 1

        $processes = @(
            Get-ProjectProcess `
                -ScriptPath $ScriptPath
        )
    }

    if ($processes.Count -eq 0) {
        Start-Process `
            -FilePath $Python `
            -ArgumentList $ScriptPath `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden

        Start-Sleep -Seconds 2

        $processes = @(
            Get-ProjectProcess `
                -ScriptPath $ScriptPath
        )

        if ($processes.Count -eq 0) {
            throw (
                "$ScriptName nao permaneceu ativo " +
                "apos a tentativa de inicializacao."
            )
        }

        Write-SupervisorLog `
            -Level "INFO" `
            -Message (
                "Componente iniciado: {0} | PID {1}" -f
                $ScriptName,
                $processes[0].ProcessId
            )
    }
}


function Test-Cdp {
    try {
        Invoke-RestMethod `
            -Uri $CdpEndpoint `
            -TimeoutSec 3 |
            Out-Null

        return $true
    }
    catch {
        return $false
    }
}


function Get-CdpRootProcess {
    return @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -eq "chrome.exe" -and
                $_.CommandLine -and
                $_.CommandLine -like "*--remote-debugging-port=9222*" -and
                $_.CommandLine -notlike "*--type=*"
            }
    )
}


function Ensure-Cdp {
    if (Test-Cdp) {
        return
    }

    foreach ($process in @(Get-CdpRootProcess)) {
        & taskkill.exe /PID $process.ProcessId /T /F | Out-Null
    }

    Start-Sleep -Seconds 2

    $chromeCandidates = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    )

    $Chrome = (
        $chromeCandidates |
            Where-Object { Test-Path $_ } |
            Select-Object -First 1
    )

    if (-not $Chrome) {
        throw "Google Chrome nao encontrado."
    }

    $chromeArguments = @(
        "--remote-debugging-port=9222",
        "--user-data-dir=$ChromeProfile",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank"
    )

    $chromeMode = "interactive"

    if ($RunChromeHeadless) {
        $chromeArguments = @(
            "--headless=new",
            "--disable-gpu"
        ) + $chromeArguments

        $chromeMode = "headless-system"
    }

    Write-SupervisorLog `
        -Level "INFO" `
        -Message (
            "Iniciando Chrome/CDP | modo={0}" -f
            $chromeMode
        )

    Start-Process `
        -FilePath $Chrome `
        -ArgumentList $chromeArguments

    $cdpOk = $false

    for ($i = 1; $i -le 20; $i++) {
        Start-Sleep -Seconds 1

        if (Test-Cdp) {
            $cdpOk = $true
            break
        }
    }

    if (-not $cdpOk) {
        throw "Chrome/CDP nao respondeu na porta 9222."
    }

    Write-SupervisorLog `
        -Level "INFO" `
        -Message "Chrome/CDP iniciado e responsivo."
}


function Invoke-SupervisorStep {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    try {
        & $Action

        Set-ComponentState `
            -Name $Name `
            -State "HEALTHY"
    }
    catch {
        Set-ComponentState `
            -Name $Name `
            -State "DEGRADED" `
            -Detail $_.Exception.Message
    }
}


if (-not (Test-Path $Python)) {
    throw "Python do projeto nao encontrado."
}

$identity = $CurrentIdentity
$sessionId = $CurrentSessionId
$bootTime = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime

Write-SupervisorLog `
    -Level "INFO" `
    -Message (
        "Supervisor iniciado | identidade=$identity | " +
        "sessao={1} | boot={2:yyyy-MM-dd HH:mm:ss}" -f
        $identity,
        $sessionId,
        $bootTime
    )

try {
    Stop-StaleManagedProjectTrees
}
catch {
    Write-SupervisorLog `
        -Level "WARNING" `
        -Message (
            "Limpeza inicial encontrou falha: " +
            $_.Exception.Message
        )
}

while ($true) {
    Invoke-SupervisorStep `
        -Name "node_agent" `
        -Action {
            if (-not (Test-Path $NodeAgentScript)) {
                throw "node_agent.py nao encontrado."
            }

            Ensure-SingleProjectProcess `
                -ScriptName "node_agent.py" `
                -ScriptPath $NodeAgentScript
        }

    Invoke-SupervisorStep `
        -Name "partner_scout" `
        -Action {
            if (-not (Test-Path $PartnerScoutScript)) {
                throw "partner_scout.py nao encontrado."
            }

            Ensure-SingleProjectProcess `
                -ScriptName "partner_scout.py" `
                -ScriptPath $PartnerScoutScript
        }

    Invoke-SupervisorStep `
        -Name "social_scout" `
        -Action {
            if (-not (Test-Path $ListenerScript)) {
                throw "social_scout_telegram.py nao encontrado."
            }

            Ensure-SingleProjectProcess `
                -ScriptName "social_scout_telegram.py" `
                -ScriptPath $ListenerScript
        }

    Invoke-SupervisorStep `
        -Name "chrome_cdp" `
        -Action {
            Ensure-Cdp
        }

    Invoke-SupervisorStep `
        -Name "runtime" `
        -Action {
            if (-not (Test-Path $RuntimeScript)) {
                throw "runtime.py nao encontrado."
            }

            Ensure-SingleProjectProcess `
                -ScriptName "runtime.py" `
                -ScriptPath $RuntimeScript
        }

    Start-Sleep -Seconds 30
}
