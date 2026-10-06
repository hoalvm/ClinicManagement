[CmdletBinding()]
param([switch]$Reset)

$ErrorActionPreference = 'Stop'
if ($Reset) {
    throw 'Reset is not a routine command for the persistent ClinicManagementDB. Back up and replace it through the one-time migration procedure.'
}

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$VenvPython = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw 'Virtual environment missing. Run .\script\init_run.ps1 first.'
}

Push-Location -LiteralPath $ProjectRoot
try {
    $Target = & $VenvPython -c 'from backend.app.core.config import get_settings; s=get_settings(); print(s.app_mode, s.db_name, sep=chr(124))'
    if ($LASTEXITCODE -ne 0) { throw 'Database configuration is invalid.' }
    if ($Target -cne 'demo|ClinicManagementDB') {
        throw 'Expected APP_MODE=demo and DB_NAME=ClinicManagementDB in .env. Database was not changed.'
    }

    # The seed entrypoint initializes the schema and inserts the project fixture only
    # into an empty DB. Its version marker makes repeated calls preserve live changes.
    & $VenvPython -m backend.app.db.seed
    if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed; existing data was not reset.' }
    Write-Host 'ClinicManagementDB is ready. Existing project records were preserved.'
} finally {
    Pop-Location
}
