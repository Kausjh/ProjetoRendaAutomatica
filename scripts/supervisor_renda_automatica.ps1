# 63.8738, -149.7525

$ErrorActionPreference = "Stop"

$ProjectRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot ".."
    )
).Path

$Python = Join-Path `
    $ProjectRoot `
    ".venv\Scripts\python.exe"

$RuntimeScript = Join-Path `
    $ProjectRoot `
    "runtime.py"

$ListenerScript = Join-Path `
    $ProjectRoot `
    "social_scout_telegram.py"

$NodeAgentScript = Join-Path `
    $ProjectRoot `
    "node_agent.py"

$PartnerScoutScript = Join-Path `
    $ProjectRoot `
    "partner_scout.py"

$ChromeProfile = Join-Path `
    $ProjectRoot `
    "browser_profile_cdp"

$CdpEndpoint = "http://127.0.0.1:9222/json/version"

$ManagedScriptRegex = (
    "runtime\.py|" +
    "bot_consulta\.py|" +
    "publicador_fila\.py|" +
    "services[\\/]launcher[\\/]chrome_launcher\.py|" +
    "[\\/]main\.py"
)

Set-Location $ProjectRoot


if (-not (Test-Path $Python)) {
    throw "Python do projeto nao encontrado."
}

if (-not (Test-Path $RuntimeScript)) {
    throw "runtime.py nao encontrado."
}

if (-not (Test-Path $ListenerScript)) {
    throw "social_scout_telegram.py nao encontrado."
}

if (-not (Test-Path $NodeAgentScript)) {
    throw "node_agent.py nao encontrado."
}

if (-not (Test-Path $PartnerScoutScript)) {
    throw "partner_scout.py nao encontrado."
}


function Get-ProjectPythonProcess {
    param(
        [string]$ScriptPath
    )

    $resultado = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -match "^python(w)?\.exe$" -and
                $_.CommandLine -and
                $_.CommandLine -like "*$ProjectRoot*" -and
                $_.CommandLine -like "*$ScriptPath*"
            }
    )

    return $resultado
}


function Get-ProjectProcess {
    param(
        [string]$ScriptPath
    )

    $processos = @(
        Get-ProjectPythonProcess `
            -ScriptPath $ScriptPath
    )

    if ($processos.Count -eq 0) {
        return @()
    }

    $ids = @(
        $processos.ProcessId
    )

    $raizesLogicas = @(
        $processos |
            Where-Object {
                $_.ParentProcessId -notin $ids
            }
    )

    return $raizesLogicas
}


function Get-ManagedProjectPythonProcess {
    $resultado = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -match "^python(w)?\.exe$" -and
                $_.CommandLine -and
                $_.CommandLine -like "*$ProjectRoot*" -and
                $_.CommandLine -match $ManagedScriptRegex
            }
    )

    return $resultado
}


function Get-ManagedProjectRootProcess {
    $processos = @(
        Get-ManagedProjectPythonProcess
    )

    if ($processos.Count -eq 0) {
        return @()
    }

    $ids = @(
        $processos.ProcessId
    )

    $raizes = @(
        $processos |
            Where-Object {
                $_.ParentProcessId -notin $ids
            }
    )

    return $raizes
}


function Stop-ProjectProcessTree {
    param(
        [int]$ProcessId,
        [string]$Description
    )

    $processo = Get-CimInstance `
        Win32_Process `
        -Filter "ProcessId=$ProcessId" `
        -ErrorAction SilentlyContinue

    if ($null -eq $processo) {
        return
    }

    Write-Host (
        "Encerrando arvore antiga: {0} | PID {1}" -f
        $Description,
        $ProcessId
    )

    & taskkill.exe `
        /PID $ProcessId `
        /T `
        /F |
        Out-Null
}


function Stop-StaleManagedProjectTrees {
    Write-Host (
        "Verificando componentes operacionais orfaos " +
        "de execucoes anteriores."
    )

    for ($tentativa = 1; $tentativa -le 3; $tentativa++) {

        $processos = @(
            Get-ManagedProjectPythonProcess
        )

        if ($processos.Count -eq 0) {
            Write-Host (
                "Nenhuma arvore operacional antiga permanece ativa."
            )
            return
        }

        $raizes = @(
            Get-ManagedProjectRootProcess
        )

        if ($raizes.Count -eq 0) {
            throw (
                "Existem processos gerenciados antigos, mas nenhuma " +
                "raiz segura foi identificada."
            )
        }

        foreach ($raiz in $raizes) {

            Stop-ProjectProcessTree `
                -ProcessId $raiz.ProcessId `
                -Description $raiz.CommandLine
        }

        Start-Sleep -Seconds 1
    }

    $restantes = @(
        Get-ManagedProjectPythonProcess
    )

    if ($restantes.Count -ne 0) {

        $descricao = (
            $restantes |
                ForEach-Object {
                    "PID $($_.ProcessId): $($_.CommandLine)"
                }
        ) -join "; "

        throw (
            "Nao foi possivel remover completamente as arvores " +
            "operacionais antigas. Restantes: $descricao"
        )
    }

    Write-Host (
        "Arvores operacionais antigas removidas com sucesso."
    )
}


function Ensure-SingleProjectProcess {
    param(
        [string]$ScriptName,
        [string]$ScriptPath
    )

    $processos = @(
        Get-ProjectProcess `
            -ScriptPath $ScriptPath
    )

    if ($processos.Count -gt 1) {

        $ordenados = @(
            $processos |
                Sort-Object `
                    CreationDate,
                    ProcessId
        )

        $extras = @(
            $ordenados |
                Select-Object -Skip 1
        )

        foreach ($extra in $extras) {

            Stop-ProjectProcessTree `
                -ProcessId $extra.ProcessId `
                -Description (
                    "instancia duplicada de $ScriptName"
                )
        }

        Start-Sleep -Seconds 1

        $processos = @(
            Get-ProjectProcess `
                -ScriptPath $ScriptPath
        )
    }

    if ($processos.Count -eq 0) {

        Start-Process `
            -FilePath $Python `
            -ArgumentList $ScriptPath `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden

        Start-Sleep -Seconds 2
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
    $resultado = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -eq "chrome.exe" -and
                $_.CommandLine -and
                $_.CommandLine -like "*--remote-debugging-port=9222*" -and
                $_.CommandLine -notlike "*--type=*"
            }
    )

    return $resultado
}


function Ensure-Cdp {
    if (Test-Cdp) {
        return
    }

    $processosAntigos = @(
        Get-CdpRootProcess
    )

    foreach ($processo in $processosAntigos) {

        & taskkill.exe `
            /PID $processo.ProcessId `
            /T `
            /F |
            Out-Null
    }

    Start-Sleep -Seconds 2

    $chromeCandidatos = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    )

    $Chrome = $chromeCandidatos |
        Where-Object {
            Test-Path $_
        } |
        Select-Object -First 1

    if (-not $Chrome) {
        throw "Google Chrome nao encontrado."
    }

    Start-Process `
        -FilePath $Chrome `
        -ArgumentList @(
            "--remote-debugging-port=9222",
            "--user-data-dir=$ChromeProfile",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank"
        )

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
}


Stop-StaleManagedProjectTrees


while ($true) {
    try {

        Ensure-Cdp

        Ensure-SingleProjectProcess `
            -ScriptName "social_scout_telegram.py" `
            -ScriptPath $ListenerScript

        Ensure-SingleProjectProcess `
            -ScriptName "runtime.py" `
            -ScriptPath $RuntimeScript

        Ensure-SingleProjectProcess `
            -ScriptName "node_agent.py" `
            -ScriptPath $NodeAgentScript

        Ensure-SingleProjectProcess `
            -ScriptName "partner_scout.py" `
            -ScriptPath $PartnerScoutScript
    }
    catch {

        $mensagemErro = $_.Exception.Message

        Write-Warning (
            "Supervisor encontrou falha transitoria: $mensagemErro"
        )
    }

    Start-Sleep -Seconds 30
}
