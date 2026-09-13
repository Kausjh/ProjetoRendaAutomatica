param(
    [ValidateSet("apply", "status", "remove")]
    [string]$Action = "apply",

    [ValidateRange(1024, 65535)]
    [int]$PublicPort = 18767,

    [ValidateRange(1, 65535)]
    [int]$BackendPort = 8766
)

$ErrorActionPreference = "Stop"

function Get-TailscaleExe {
    $cmd = Get-Command tailscale.exe -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "tailscale.exe nao encontrado no PATH."
    }
    return $cmd.Source
}

$tailscale = Get-TailscaleExe

if ($Action -eq "status") {
    & $tailscale serve status
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao consultar tailscale serve status."
    }
    exit 0
}

if ($Action -eq "remove") {
    $eap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $tailscale serve --tcp=$PublicPort off
    $codigo = $LASTEXITCODE
    $ErrorActionPreference = $eap

    if ($codigo -eq 0) {
        Write-Host "FORWARDER_CLIENTE=REMOVIDO"
    } else {
        Write-Host "FORWARDER_CLIENTE=JA_AUSENTE_OU_NAO_REMOVIDO"
    }
    exit 0
}

try {
    $health = Invoke-RestMethod `
        -Uri "http://127.0.0.1:$BackendPort/api/v1/health" `
        -Method Get `
        -TimeoutSec 5
} catch {
    throw "Application API nao respondeu em 127.0.0.1:$BackendPort."
}

if ($health.status -ne "ok") {
    throw "Health da Application API nao esta ok."
}

& $tailscale serve `
    --bg `
    --yes `
    --tcp=$PublicPort `
    "tcp://127.0.0.1:$BackendPort"

if ($LASTEXITCODE -ne 0) {
    throw "Falha ao configurar o forwarder Tailscale."
}

Start-Sleep -Seconds 1

$status = (& $tailscale serve status 2>&1 | Out-String)

if ($status -notmatch [regex]::Escape(":$PublicPort")) {
    throw "Status do Tailscale nao confirmou a porta $PublicPort."
}

if ($status -notmatch [regex]::Escape("127.0.0.1:$BackendPort")) {
    throw "Status do Tailscale nao confirmou o backend 127.0.0.1:$BackendPort."
}

$tailscaleIp = (& $tailscale ip -4 | Select-Object -First 1).Trim()

Write-Host "CLIENT_TRANSPORT=READY"
Write-Host "TAILSCALE_IPV4=$tailscaleIp"
Write-Host "REMOTE_PORT=$PublicPort"
Write-Host "BACKEND=127.0.0.1:$BackendPort"
Write-Host "MAGICDNS_REQUIRED=False"
Write-Host "FUNNEL_REQUIRED=False"
Write-Host "BEARER_REQUIRED=True"
Write-Host "CLIENT_URL=http://$tailscaleIp`:$PublicPort"
