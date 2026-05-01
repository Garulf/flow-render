Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-PlaywrightInstall {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe
    )

    Write-Host "Installing Playwright Chromium (headless)..."

    & $PythonExe -m playwright install chromium
    if ($LASTEXITCODE -eq 0) {
        return
    }

    if (Test-IsAdmin) {
        throw "Playwright install failed even when already elevated."
    }

    Write-Warning "Playwright install failed without elevation."
    $answer = Read-Host "Retry Playwright install as Administrator? (Y/N)"
    if ($answer -notin @("Y", "y", "Yes", "yes")) {
        throw "Playwright install failed and elevation was declined."
    }

    $proc = Start-Process -FilePath $PythonExe -ArgumentList "-m", "playwright", "install", "chromium" -Verb RunAs -PassThru -Wait
    if ($proc.ExitCode -ne 0) {
        throw "Elevated Playwright install failed with exit code $($proc.ExitCode)."
    }
}

$workspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspaceRoot

$venvPath = ".venv"
$requirementsFile = "requirements.in"
$skipPlaywrightInstall = $false

$venvFullPath = Join-Path $workspaceRoot $venvPath
$venvPython = Join-Path $venvFullPath "Scripts\python.exe"
$venvAlreadyExisted = Test-Path $venvPython

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment at $venvFullPath"
    py -3 -m venv $venvFullPath
}

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment Python executable not found: $venvPython"
}

if ($venvAlreadyExisted) {
    Write-Host "Existing virtual environment detected; skipping venv creation and dependency installation."
} else {
    Write-Host "Upgrading pip in virtual environment"
    & $venvPython -m pip install --upgrade pip

    $requirementsPath = Join-Path $workspaceRoot $requirementsFile
    if (-not (Test-Path $requirementsPath)) {
        throw "Requirements file not found: $requirementsPath"
    }

    Write-Host "Installing dependencies from $requirementsFile"
    & $venvPython -m pip install -r $requirementsPath
}

if (-not $skipPlaywrightInstall) {
    Invoke-PlaywrightInstall -PythonExe $venvPython
}

$cliPath = Join-Path $workspaceRoot "src\cli.py"
if (-not (Test-Path $cliPath)) {
    throw "CLI entrypoint not found: $cliPath"
}

$resolvedCliArgs = @($args)

Write-Host "Running cli.py"
& $venvPython $cliPath @resolvedCliArgs
exit $LASTEXITCODE
