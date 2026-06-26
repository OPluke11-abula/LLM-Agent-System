param(
    [switch]$SkipViewer,
    [switch]$SkipTests,
    [string]$PythonPath,
    [switch]$InstallGitHooks
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

function Test-NativeCommand {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
    )
    try {
        & $FilePath @Arguments *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Resolve-PythonPath {
    if ($PythonPath) {
        if (Test-NativeCommand $PythonPath "--version") {
            return $PythonPath
        }
        throw "Configured PythonPath is not executable: $PythonPath"
    }

    $candidates = @(
        "$Root\.venv\Scripts\python.exe",
        "python"
    )

    foreach ($candidate in $candidates) {
        if ((Test-Path $candidate) -or $candidate -eq "python") {
            if (Test-NativeCommand $candidate "--version") {
                return $candidate
            }
            Write-Warning "Skipping unusable Python interpreter: $candidate"
        }
    }

    throw "No usable Python interpreter found. Recreate .venv or pass -PythonPath <path>."
}

$pythonPath = Resolve-PythonPath

function Resolve-NpmPath {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        if (Test-NativeCommand "npm.cmd" "--version") {
            return "npm.cmd"
        }
    }

    if (Test-NativeCommand "npm" "--version") {
        return "npm"
    }

    throw "No usable npm executable found."
}

function Invoke-Python {
    param(
        [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
    )
    & $pythonPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $pythonPath $($Arguments -join ' '). If this is a ModuleNotFoundError, rebuild .venv or pass -PythonPath for an interpreter with requirements.txt installed."
    }
}

Write-Host "== LAS verify =="
Write-Host "Workspace: $Root"
Write-Host "Python path: $pythonPath"

Write-Host "`n[1/5] Python compile check"
$pythonFiles = @(
    "agent_workspace\api.py",
    "agent_workspace\core\engine.py",
    "agent_workspace\core\precheck.py",
    "agent_workspace\core\providers.py",
    "agent_workspace\core\router.py",
    "agent_workspace\core\token_counter.py",
    "agent_workspace\long_term_memory.py",
    "agent_workspace\memory_backends.py",
    "agent_workspace\observability.py",
    "agent_workspace\pap_validate.py",
    "agent_workspace\tool_manifest.py",
    "agent_workspace\topology_bridge.py",
    "agent_workspace\topology_stream.py",
    "scripts\git_guard.py"
)
Invoke-Python "-m" "py_compile" @pythonFiles

if (-not $SkipTests) {
    Write-Host "`n[2/5] Python test suite"
    $pytestScratch = Join-Path $Root "agent_workspace\scratch\pytest-$PID"
    $pytestTemp = Join-Path $pytestScratch "tmp"
    $pytestBaseTemp = Join-Path $pytestScratch "basetemp"
    $pytestCache = Join-Path $pytestScratch "cache"
    New-Item -ItemType Directory -Force -Path $pytestTemp, $pytestCache | Out-Null

    $previousTemp = $env:TEMP
    $previousTmp = $env:TMP
    $env:TEMP = $pytestTemp
    $env:TMP = $pytestTemp
    try {
        Invoke-Python "-m" "pytest" "--no-cov" "-q" "-o" "cache_dir=$pytestCache" "--basetemp" $pytestBaseTemp "-o" "faulthandler_timeout=90" "-o" "faulthandler_exit_on_timeout=true"
    }
    finally {
        $env:TEMP = $previousTemp
        $env:TMP = $previousTmp
        $scratchRoot = [System.IO.Path]::GetFullPath((Join-Path $Root "agent_workspace\scratch"))
        $resolvedPytestScratch = [System.IO.Path]::GetFullPath($pytestScratch)
        $scratchPrefix = $scratchRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
        if (
            $resolvedPytestScratch.StartsWith($scratchPrefix, [System.StringComparison]::OrdinalIgnoreCase) -and
            (Split-Path -Leaf $resolvedPytestScratch).StartsWith("pytest-", [System.StringComparison]::OrdinalIgnoreCase) -and
            (Test-Path $resolvedPytestScratch)
        ) {
            Remove-Item -LiteralPath $resolvedPytestScratch -Recurse -Force
        }
    }
}
else {
    Write-Host "`n[2/5] Python test suite skipped"
}

Write-Host "`n[3/5] PAP workspace contract"
Invoke-Python "agent_workspace\pap_validate.py"

Write-Host "`n[4/5] Runtime tool manifest contract"
Invoke-Python "agent_workspace\tool_manifest.py" "validate"
Write-Host "Generating skills acceptance matrix..."
Invoke-Python "agent_workspace\tool_manifest.py" "matrix"

if ($InstallGitHooks) {
    Write-Host "`nChecking Git safety hooks..."
    $gitHooksDir = Join-Path $Root ".git\hooks"
    if (Test-Path $gitHooksDir) {
        $prePushHook = Join-Path $gitHooksDir "pre-push"
        $hookBody = @(
            "# LAS git guard",
            "if [ -x `".venv/Scripts/python.exe`" ]; then",
            "  PYTHON=`".venv/Scripts/python.exe`"",
            "elif [ -x `".venv/bin/python`" ]; then",
            "  PYTHON=`".venv/bin/python`"",
            "else",
            "  PYTHON=`"python`"",
            "fi",
            "exec `"`$PYTHON`" scripts/git_guard.py `"`$@`""
        ) -join "`n"
        $hookContent = "#!/bin/sh`nset -eu`n$hookBody`n"
        if (-not (Test-Path $prePushHook)) {
            Write-Host "Creating Git pre-push hook for safety guardrails..."
            [System.IO.File]::WriteAllText($prePushHook, $hookContent)
        } else {
            $existingContent = [System.IO.File]::ReadAllText($prePushHook)
            if (-not ($existingContent -like "*git_guard.py*")) {
                Write-Host "Appending safety guardrails to existing pre-push hook..."
                [System.IO.File]::AppendAllText($prePushHook, "`n$hookBody`n")
            }
        }
    } else {
        Write-Host "Not a Git repository or .git/hooks directory missing. Skipping hook setup."
    }
} else {
    Write-Host "`nGit safety hook setup skipped. Pass -InstallGitHooks to modify .git/hooks."
}

if (-not $SkipViewer) {
    Write-Host "`n[5/5] Viewer build and smoke checks"
    $npmPath = Resolve-NpmPath
    Push-Location viewer
    try {
        Invoke-Native $npmPath "run" "build"
        Invoke-Native $npmPath "run" "verify:ui"
        Invoke-Native $npmPath "run" "test:swarm-ui"
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "`n[5/5] Viewer build skipped"
}

Write-Host "`nLAS verification complete."
