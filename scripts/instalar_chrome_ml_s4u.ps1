# 63.8738, -149.7525

param(
    [switch]$StartNow,
    [switch]$ReplaceExistingCdp
)

$ErrorActionPreference = "Stop"

$TaskName = "RendaAutomatica_MLChrome"
$CdpEndpoint = "http://127.0.0.1:9222/json/version"

$identity = (
    [Security.Principal.WindowsIdentity]::GetCurrent()
)

$principalAtual = (
    New-Object Security.Principal.WindowsPrincipal(
        $identity
    )
)

$admin = $principalAtual.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $admin) {
    throw "Execute este instalador como Administrador."
}

$usuario = $identity.Name

if (
    $usuario -ieq "NT AUTHORITY\SYSTEM"
) {
    throw (
        "Execute o instalador elevado na conta Windows " +
        "que possui o perfil autenticado do Mercado Livre."
    )
}

$perfil = Join-Path `
    $env:LOCALAPPDATA `
    "ProjetoRendaAutomatica\browser_profile_ml_user"

if (-not (Test-Path -LiteralPath $perfil)) {
    throw (
        "Perfil autenticado nao encontrado em: $perfil"
    )
}

$chromeCandidates = @(
    "$env:PROGRAMFILES\Google\Chrome\Application\chrome.exe"
    "${env:PROGRAMFILES(X86)}\Google\Chrome\Application\chrome.exe"
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) |
    Where-Object {
        $_ -and
        (Test-Path -LiteralPath $_)
    }

$chrome = (
    $chromeCandidates |
    Select-Object -First 1
)

if (-not $chrome) {
    throw "Google Chrome nao encontrado."
}

$argumentos = @(
    "--headless=new"
    "--disable-gpu"
    "--remote-debugging-address=127.0.0.1"
    "--remote-debugging-port=9222"
    "--user-data-dir=`"$perfil`""
    "--no-first-run"
    "--no-default-browser-check"
    "--disable-background-mode"
    "about:blank"
) -join " "

$action = New-ScheduledTaskAction `
    -Execute $chrome `
    -Argument $argumentos

$trigger = New-ScheduledTaskTrigger `
    -AtStartup

$principal = New-ScheduledTaskPrincipal `
    -UserId $usuario `
    -LogonType S4U `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description (
        "Chrome headless autenticado do Projeto Renda Automatica"
    ) `
    -Force |
    Out-Null

Write-Host "TASK_CHROME_REGISTRADA=SIM"
Write-Host "TASK_CHROME_NOME=$TaskName"
Write-Host "TASK_CHROME_LOGON=S4U"
Write-Host "TASK_CHROME_USUARIO=$usuario"
Write-Host "TASK_CHROME_PERFIL=$perfil"

if (-not $StartNow) {
    return
}

$roots = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq "chrome.exe" -and
            $_.CommandLine -and
            $_.CommandLine -like "*--remote-debugging-port=9222*" -and
            $_.CommandLine -notlike "*--type=*"
        }
)

if (($roots.Count -gt 0) -and (-not $ReplaceExistingCdp)) {
    throw (
        "Ja existe Chrome raiz na 9222. " +
        "Use -ReplaceExistingCdp para cutover explicito."
    )
}

if ($ReplaceExistingCdp) {
    foreach ($processo in $roots) {
        Write-Host (
            "ENCERRANDO_CDP_ANTIGO_PID=" +
            $processo.ProcessId
        )

        & taskkill.exe `
            /PID $processo.ProcessId `
            /T `
            /F |
            Out-Null
    }

    for ($i = 1; $i -le 20; $i++) {
        $listener = @(
            Get-NetTCPConnection `
                -LocalPort 9222 `
                -State Listen `
                -ErrorAction SilentlyContinue
        )

        if ($listener.Count -eq 0) {
            break
        }

        Start-Sleep -Milliseconds 500
    }

    $listener = @(
        Get-NetTCPConnection `
            -LocalPort 9222 `
            -State Listen `
            -ErrorAction SilentlyContinue
    )

    if ($listener.Count -ne 0) {
        throw (
            "Porta 9222 nao foi liberada para o cutover."
        )
    }
}

Start-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction Stop

$cdpOk = $false

for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 1

    try {
        $resposta = Invoke-RestMethod `
            -Uri $CdpEndpoint `
            -TimeoutSec 2

        if ($resposta.webSocketDebuggerUrl) {
            $cdpOk = $true
            break
        }
    }
    catch {
    }
}

if (-not $cdpOk) {
    throw (
        "Task S4U registrada, mas CDP 9222 nao ficou funcional."
    )
}

Write-Host "TASK_CHROME_INICIADA=SIM"
Write-Host "CDP_9222_FUNCIONAL=SIM"
Write-Host "BROWSER_VISIVEL=NAO"
