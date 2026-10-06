[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$VenvPython = Join-Path $ProjectRoot 'venv\Scripts\python.exe'

Push-Location -LiteralPath $ProjectRoot
try {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        # Prefer Python 3.12, while keeping the existing project Python 3.11 usable.
        $Candidates = @(
            @{ Command = 'py'; Arguments = @('-3.12') },
            @{ Command = 'python'; Arguments = @() },
            @{ Command = 'py'; Arguments = @('-3') }
        )
        $Selected = $null
        foreach ($Candidate in $Candidates) {
            try {
                & $Candidate.Command @($Candidate.Arguments) -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $Selected = $Candidate
                    break
                }
            } catch {
                # Try the next installed Python command.
            }
        }
        if ($null -eq $Selected) {
            throw 'Python 3.11 or newer was not found. Install Python, then run init_run.ps1 again.'
        }
        Write-Host 'Creating Python virtual environment...'
        & $Selected.Command @($Selected.Arguments) -m venv (Join-Path $ProjectRoot 'venv')
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $VenvPython)) {
            throw 'Could not create the Python virtual environment.'
        }
    }

    & $VenvPython -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'
    if ($LASTEXITCODE -ne 0) {
        throw 'The existing venv uses Python older than 3.11. Recreate it with Python 3.11 or newer.'
    }

    $EnvPath = Join-Path $ProjectRoot '.env'
    if (-not (Test-Path -LiteralPath $EnvPath)) {
        $ExamplePath = Join-Path $ProjectRoot '.env.example'
        if (-not (Test-Path -LiteralPath $ExamplePath)) {
            throw '.env.example is missing.'
        }
        $Secret = & $VenvPython -c 'import secrets; print(secrets.token_urlsafe(48))'
        if ($LASTEXITCODE -ne 0 -or -not $Secret) {
            throw 'Could not generate the application secret.'
        }
        $Example = [System.IO.File]::ReadAllText($ExamplePath)
        $Configured = [regex]::Replace($Example, '(?m)^JWT_SECRET=.*$', "JWT_SECRET=$Secret")
        [System.IO.File]::WriteAllText($EnvPath, $Configured, [System.Text.UTF8Encoding]::new($false))
        Write-Host 'Created .env with a random JWT secret. Set the SQL Server connection values before init_db.ps1.'
    }

    Write-Host 'Installing required packages...'
    & $VenvPython -m pip install --disable-pip-version-check --quiet -r (Join-Path $ProjectRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) {
        throw 'Dependency installation failed.'
    }

    Write-Host 'Environment ready. Next: .\script\init_db.ps1'
} finally {
    Pop-Location
}
