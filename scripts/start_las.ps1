<#
.SYNOPSIS
    LAS Developer Control Plane Launcher (PowerShell Entrypoint)
.DESCRIPTION
    Launches the LAS FastAPI server and developer cockpit under Universal Protocol v3.8.0.
.EXAMPLE
    .\scripts\start_las.ps1 -Port 8000
#>

[CmdletBinding()]
param (
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoBrowser,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

# Detect Python interpreter
$PythonExe = ""
if (Test-Path "$env:USERPROFILE\agent-tools\headroom\venv\Scripts\python.exe") {
    $PythonExe = "$env:USERPROFILE\agent-tools\headroom\venv\Scripts\python.exe"
} elseif (Test-Path ".\.venv\Scripts\python.exe") {
    $PythonExe = ".\.venv\Scripts\python.exe"
} else {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
}

if (-not $PythonExe) {
    Write-Error "Python 3 interpreter not found. Please activate your virtual environment."
    exit 1
}

$ScriptPath = Join-Path $PSScriptRoot "start_las.py"

$ArgsList = @("$ScriptPath", "--host", "$HostAddress", "--port", "$Port")
if ($NoBrowser) {
    $ArgsList += "--no-browser"
}
if ($Reload) {
    $ArgsList += "--reload"
}

& $PythonExe @ArgsList
exit $LASTEXITCODE
