param(
    [string]$PythonPath = "python",
    [switch]$NoVenv,
    [switch]$SkipInstall,
    [switch]$SkipViewer,
    [switch]$InstallProviders,
    [switch]$AllowMsysPython
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Native {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

if (-not $NoVenv) {
    $resolvedPython = (Get-Command $PythonPath -ErrorAction Stop).Source
    if (
        -not $AllowMsysPython `
        -and -not $SkipInstall `
        -and $resolvedPython.ToLowerInvariant().Contains("\msys64\")
    ) {
        throw (
            "The selected Python is MSYS/MinGW ($resolvedPython). " +
            "Several runtime dependencies need native wheels and may fail to build there. " +
            "Install standard Windows CPython, then rerun with -PythonPath <path-to-python.exe>, " +
            "or run verify.cmd -SkipViewer for dependency-free contract checks."
        )
    }
    if (-not (Test-Path ".venv")) {
        Write-Host "Creating .venv"
        Invoke-Native $PythonPath "-m" "venv" ".venv"
    }
    $windowsPython = Join-Path $Root ".venv\Scripts\python.exe"
    $posixPython = Join-Path $Root ".venv\bin\python.exe"
    if (Test-Path $windowsPython) {
        $venvPython = $windowsPython
        $env:Path = "$(Join-Path $Root ".venv\Scripts");$env:Path"
    }
    elseif (Test-Path $posixPython) {
        $venvPython = $posixPython
        $env:Path = "$(Join-Path $Root ".venv\bin");$env:Path"
    }
    else {
        throw "Unable to locate the virtualenv Python executable under .venv"
    }
}
else {
    $venvPython = "python"
}

if (-not $SkipInstall) {
    Write-Host "Installing core Python dependencies"
    Invoke-Native $venvPython "-m" "pip" "install" "-r" "requirements.txt"
    if ($InstallProviders) {
        Write-Host "Installing optional provider SDKs"
        Invoke-Native $venvPython "-m" "pip" "install" "-r" "requirements-providers.txt"
    }
}

& (Join-Path $PSScriptRoot "verify.ps1") -SkipViewer:$SkipViewer
if ($LASTEXITCODE -ne 0) {
    throw "verify.ps1 failed with exit code $LASTEXITCODE"
}
