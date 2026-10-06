[CmdletBinding()]
param([switch]$IncludeProductionStaging)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$VenvPython = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw 'Virtual environment missing. Run .\script\init_run.ps1 first.'
}

$PreviousSqlIntegration = [Environment]::GetEnvironmentVariable('RUN_SQLSERVER_INTEGRATION', 'Process')
$PreviousStagingIntegration = [Environment]::GetEnvironmentVariable('RUN_PRODUCTION_STAGING_INTEGRATION', 'Process')
$PreviousQtPlatform = [Environment]::GetEnvironmentVariable('QT_QPA_PLATFORM', 'Process')

Push-Location -LiteralPath $ProjectRoot
try {
    Write-Host 'Checking the persistent project database...'
    & $VenvPython -m backend.app.ops.project_preflight
    if ($LASTEXITCODE -ne 0) { throw 'Project database check failed. Run .\script\init_db.ps1 first.' }

    Write-Host 'Checking Python code style...'
    & $VenvPython -m ruff check backend frontend tests
    if ($LASTEXITCODE -ne 0) { throw 'Ruff found errors.' }

    $env:RUN_SQLSERVER_INTEGRATION = '1'
    $env:RUN_PRODUCTION_STAGING_INTEGRATION = '0'
    $env:QT_QPA_PLATFORM = 'offscreen'

    # Qt's QApplication lifetime is process-global. Keep widget tests in their
    # own pytest process so API/SQL fixtures cannot destabilize Qt on Windows.
    Write-Host 'Running desktop and unit tests in an isolated Qt process...'
    & $VenvPython -m pytest -q tests/unit
    if ($LASTEXITCODE -ne 0) { throw 'Desktop or unit tests failed.' }

    $PytestArgs = @('-m', 'pytest', '-q', 'tests/api', 'tests/integration')
    if ($IncludeProductionStaging) {
        $env:RUN_PRODUCTION_STAGING_INTEGRATION = '1'
        Write-Host 'Running API and SQL Server tests, including production staging...'
    } else {
        $PytestArgs += '--ignore=tests/integration/test_production_staging.py'
        Write-Host 'Running API and rollback-only project SQL Server integration tests...'
    }
    & $VenvPython @PytestArgs
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    Write-Host 'All selected checks passed.'
} finally {
    [Environment]::SetEnvironmentVariable('RUN_SQLSERVER_INTEGRATION', $PreviousSqlIntegration, 'Process')
    [Environment]::SetEnvironmentVariable('RUN_PRODUCTION_STAGING_INTEGRATION', $PreviousStagingIntegration, 'Process')
    [Environment]::SetEnvironmentVariable('QT_QPA_PLATFORM', $PreviousQtPlatform, 'Process')
    Pop-Location
}
