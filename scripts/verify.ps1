param(
    [switch]$SkipViewer
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

Write-Host "== LAS verify =="
Write-Host "Workspace: $Root"

Write-Host "`n[1/4] Python compile check"
$pythonFiles = @(
    "agent_workspace\api.py",
    "agent_workspace\core\engine.py",
    "agent_workspace\core\providers.py",
    "agent_workspace\core\router.py",
    "agent_workspace\long_term_memory.py",
    "agent_workspace\memory_backends.py",
    "agent_workspace\observability.py",
    "agent_workspace\pap_validate.py",
    "agent_workspace\tool_manifest.py",
    "agent_workspace\topology_bridge.py",
    "agent_workspace\topology_stream.py"
)
Invoke-Native "python" "-m" "py_compile" @pythonFiles

Write-Host "`n[2/4] PAP workspace contract"
Invoke-Native "python" "agent_workspace\pap_validate.py"

Write-Host "`n[3/4] Runtime tool manifest contract"
Invoke-Native "python" "agent_workspace\tool_manifest.py" "validate"

if (-not $SkipViewer) {
    Write-Host "`n[4/4] Viewer build"
    Push-Location viewer
    try {
        Invoke-Native "npm" "run" "build"
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "`n[4/4] Viewer build skipped"
}

Write-Host "`nLAS verification complete."
