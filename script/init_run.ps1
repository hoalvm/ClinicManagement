$ErrorActionPreference = "Stop"

# Determine project root directory regardless of current working directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..").Path
Set-Location -LiteralPath $ProjectRoot

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   CLINIC MANAGEMENT SYSTEM - ENVIRONMENT SETUP           " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Project directory: $ProjectRoot`n" -ForegroundColor DarkGray

# ------------------------------------------------------------------------------
# 1. Detect Python executable on system
# ------------------------------------------------------------------------------
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Yellow

$PythonExecutable = $null

# Candidate commands and common Windows installation paths
$Candidates = @(
    "py -3.12",
    "py -3.13",
    "py -3.14",
    "python",
    "py",
    "python3"
)

# Also check LocalAppData Program Python folders if command lookup fails
if ($env:LOCALAPPDATA) {
    $CommonPaths = Get-ChildItem -Path "$env:LOCALAPPDATA\Programs\Python" -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName
    if ($CommonPaths) {
        $Candidates += $CommonPaths
    }
}

foreach ($Candidate in $Candidates) {
    try {
        $TestOutput = & (Invoke-Expression -Command "Get-Command $Candidate -ErrorAction SilentlyContinue") --version 2>&1
        if (-not $TestOutput) {
            # Try direct invocation if expression didn't resolve as single command name
            $TestOutput = & $Candidate --version 2>&1
        }
        if ($LASTEXITCODE -eq 0 -and $TestOutput -match "Python\s+3\.\d+") {
            # Verify Python can execute code and is at least 3.10+
            $CheckVersion = & $Candidate -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>&1
            if ($LASTEXITCODE -eq 0) {
                $PythonExecutable = $Candidate
                break
            }
        }
    } catch {
        # Continue searching candidates
    }
}

# Fallback: check standard 'python' in path directly
if (-not $PythonExecutable) {
    try {
        $Ver = & python --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $Ver -match "Python\s+3\.\d+") {
            $PythonExecutable = "python"
        }
    } catch {}
}

if (-not $PythonExecutable) {
    Write-Host "[ERROR] Functional Python 3 installation (>= 3.10) was not found." -ForegroundColor Red
    Write-Host "Please install Python 3.12 or newer from https://www.python.org/ and check 'Add python.exe to PATH'." -ForegroundColor Yellow
    exit 1
}

$PyVerString = & $PythonExecutable --version 2>&1
Write-Host "[OK] Detected: $PyVerString (using: $PythonExecutable)" -ForegroundColor Green

# ------------------------------------------------------------------------------
# 2. Setup Virtual Environment (venv)
# ------------------------------------------------------------------------------
Write-Host "`n[2/5] Setting up virtual environment (venv)..." -ForegroundColor Yellow

$VenvDir = Join-Path $ProjectRoot "venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

$NeedCreate = $false
if (-not (Test-Path -LiteralPath $VenvPython)) {
    $NeedCreate = $true
} else {
    # Verify existing venv is healthy
    try {
        & "$VenvPython" --version 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $NeedCreate = $true
        }
    } catch {
        $NeedCreate = $true
    }
}

if ($NeedCreate) {
    Write-Host "Creating fresh virtual environment in 'venv'..." -ForegroundColor Cyan
    & $PythonExecutable -m venv "$VenvDir"
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Write-Host "[ERROR] Failed to create virtual environment at '$VenvDir'." -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "[OK] Existing virtual environment verified." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 3. Configure Environment Variables (.env)
# ------------------------------------------------------------------------------
Write-Host "`n[3/5] Checking configuration (.env)..." -ForegroundColor Yellow

$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path -LiteralPath $EnvFile)) {
    if (Test-Path -LiteralPath $EnvExample) {
        Copy-Item -LiteralPath $EnvExample -Destination $EnvFile
        Write-Host "[OK] Created .env file from .env.example." -ForegroundColor Green
        
        # Generate a cryptographically secure JWT_SECRET
        try {
            $GeneratedSecret = & "$VenvPython" -c "import secrets; print(secrets.token_urlsafe(48))" 2>$null
            if ($GeneratedSecret) {
                $Content = Get-Content -LiteralPath $EnvFile -Raw
                $Content = $Content -replace "JWT_SECRET=.*", "JWT_SECRET=$GeneratedSecret"
                Set-Content -LiteralPath $EnvFile -Value $Content
                Write-Host "[OK] Generated secure random JWT_SECRET in .env." -ForegroundColor Green
            }
        } catch {}
    } else {
        Write-Host "[WARN] .env.example not found; skipping .env creation." -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Configuration file .env already exists." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 4. Upgrade pip
# ------------------------------------------------------------------------------
Write-Host "`n[4/5] Upgrading pip..." -ForegroundColor Yellow
& "$VenvPython" -m pip install --upgrade pip --quiet
Write-Host "[OK] Pip is up to date." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 5. Install Dependencies
# ------------------------------------------------------------------------------
Write-Host "`n[5/5] Installing dependencies from requirements.txt..." -ForegroundColor Yellow

$ReqFile = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path -LiteralPath $ReqFile) {
    & "$VenvPython" -m pip install -r "$ReqFile"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Dependency installation encountered errors." -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "[OK] All required packages installed successfully." -ForegroundColor Green
} else {
    Write-Host "[ERROR] requirements.txt not found at '$ReqFile'!" -ForegroundColor Red
    exit 1
}