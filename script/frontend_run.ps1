[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$VenvPython = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw 'Virtual environment missing. Run .\script\init_run.ps1 first.'
}

Push-Location -LiteralPath $ProjectRoot
try {
    $ProgressPreference = 'SilentlyContinue'
    $Settings = & $VenvPython -c 'from frontend.core.config import get_frontend_settings; s=get_frontend_settings(); print(s.app_mode, s.api_base_url, sep=chr(124))'
    if ($LASTEXITCODE -ne 0) { throw 'Desktop configuration is invalid.' }
    $Values = $Settings -split '\|', 2
    if ($Values.Count -ne 2 -or $Values[0] -ne 'demo') {
        throw 'Expected APP_MODE=demo in .env.'
    }

    try {
        $Ready = Invoke-WebRequest -Uri ($Values[1].TrimEnd('/') + '/health/ready') -TimeoutSec 3 -UseBasicParsing
        if ($Ready.StatusCode -ne 200) { throw 'API readiness check failed.' }
        $Identity = Invoke-RestMethod -Uri ($Values[1].TrimEnd('/') + '/api/v1/system/time') -TimeoutSec 3
    } catch {
        throw 'API is unavailable. Start script/backend_run.ps1 first.'
    }
    if ($Identity.demo_mode -ne $true -or $Identity.project_database -cne 'ClinicManagementDB') {
        throw 'API is not connected to the persistent ClinicManagementDB project instance.'
    }

    Write-Host "Connecting desktop to $($Values[1])"
    & $VenvPython -m frontend.main
    if ($LASTEXITCODE -ne 0) { throw 'Desktop stopped with an error.' }
} finally {
    Pop-Location
}
