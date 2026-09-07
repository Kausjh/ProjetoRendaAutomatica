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

$ChromeProfile = Join-Path `
    $ProjectRoot `
    "browser_profile_cdp"

$CdpEndpoint = "http://127.0.0.1:9222/json/version"

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


function Get-ProjectProcess {
    param(
        [string]$ScriptName
    )

    $resultado = @(
        Get-CimInstance Win32_Process |
        Where-Object {
            $_.ExecutablePath -eq $Python -and
            $_.CommandLine -and
            $_.CommandLine -like "*$ScriptName*"
        }
    )

    return $resultado
}


function Ensure-SingleProjectProcess {
    param(
        [string]$ScriptName,
        [string]$ScriptPath
    )

    $processos = @(
        Get-ProjectProcess `
            -ScriptName $ScriptName
    )

    if ($processos.Count -gt 1) {
        $ordenados = @(
            $processos |
            Sort-Object ProcessId
        )

        $extras = @(
            $ordenados |
            Select-Object -Skip 1
        )

        foreach ($extra in $extras) {
            Stop-Process `
                -Id $extra.ProcessId `
                -Force `
                -ErrorAction SilentlyContinue
        }

        Start-Sleep -Seconds 1

        $processos = @(
            Get-ProjectProcess `
                -ScriptName $ScriptName
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


while ($true) {
    try {
        Ensure-Cdp

        Ensure-SingleProjectProcess `
            -ScriptName "social_scout_telegram.py" `
            -ScriptPath $ListenerScript

        Ensure-SingleProjectProcess `
            -ScriptName "runtime.py" `
            -ScriptPath $RuntimeScript
    }
    catch {
        $mensagemErro = $_.Exception.Message

        Write-Warning (
            "Supervisor encontrou falha transitoria: $mensagemErro"
        )
    }

    Start-Sleep -Seconds 30
}
