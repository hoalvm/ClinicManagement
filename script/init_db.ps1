param(
    [switch]$Reset
)

$ErrorActionPreference = "Stop"

# Determine project root directory regardless of current working directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..").Path
Set-Location -LiteralPath $ProjectRoot

$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "[ERROR] Virtual environment not found. Please run .\script\init_run.ps1 first." -ForegroundColor Red
    exit 1
}

$ArgsList = @("-m", "backend.app.db.init_db")
if ($Reset) {
    $ArgsList += "--reset"
}

& "$VenvPython" @ArgsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
