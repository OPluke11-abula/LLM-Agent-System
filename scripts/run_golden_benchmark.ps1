# PowerShell wrapper for LAS Autonomous Coding Pipeline Golden Flow Benchmark (Phase 83 / P4)
param (
    [string]$RepoPath = "",
    [string]$OutputJson = ".agent/evidence/golden_benchmark_receipt.json"
)

$PythonExe = "C:\Users\luke2\agent-tools\headroom\venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

$ScriptPath = Join-Path $PSScriptRoot "run_golden_benchmark.py"

$ArgsList = @($ScriptPath, "--output-json", $OutputJson)
if ($RepoPath -ne "") {
    $ArgsList += @("--repo-path", $RepoPath)
}

Write-Host "Running Golden Benchmark via: $PythonExe" -ForegroundColor Cyan
& $PythonExe @ArgsList
exit $LASTEXITCODE
