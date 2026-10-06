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
    $Settings = & $VenvPython -c 'from backend.app.core.config import get_settings; s=get_settings(); print(s.app_mode, s.db_name, s.api_host, s.api_port, sep=chr(124))'
    if ($LASTEXITCODE -ne 0) { throw 'Backend configuration is invalid.' }
    $Values = $Settings -split '\|'
    if ($Values.Count -ne 4 -or $Values[0] -ne 'demo' -or $Values[1] -ne 'ClinicManagementDB') {
        throw 'Expected APP_MODE=demo and DB_NAME=ClinicManagementDB in .env.'
    }

    # The project database is persistent. Starting the API never initializes or seeds it.
    & $VenvPython -m backend.app.ops.project_preflight
    if ($LASTEXITCODE -ne 0) { throw 'Backend startup check failed.' }

    Write-Host "Starting API for $($Values[1]) at $($Values[2]):$($Values[3])"
    & $VenvPython -m uvicorn backend.app.main:app --host $Values[2] --port $Values[3] --workers 1
    if ($LASTEXITCODE -ne 0) { throw 'Backend stopped with an error.' }
} finally {
    Pop-Location
}
