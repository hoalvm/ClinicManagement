[CmdletBinding()]
param([switch]$Reset)

$ErrorActionPreference = 'Stop'
if (-not $Reset) {
    throw 'This command deletes all project data. Run .\script\seed_run.ps1 -Reset to reset explicitly.'
}

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$VenvPython = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw 'Virtual environment missing. Run .\script\init_run.ps1 first.'
}

Push-Location -LiteralPath $ProjectRoot
try {
    & $VenvPython -m backend.app.db.reset_seed --reset
    if ($LASTEXITCODE -ne 0) {
        throw 'Project database reset failed. Check the message above before retrying.'
    }
} finally {
    Pop-Location
}
