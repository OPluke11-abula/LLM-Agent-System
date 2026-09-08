param(
    [switch]$SkipViewer,
    [switch]$SkipTests,
    [switch]$SkipLint,
    [switch]$SkipDoctor,
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

    # First pass: look for an interpreter that can import yaml
    foreach ($candidate in $candidates) {
        if ((Test-Path $candidate) -or $candidate -eq "python") {
            if (Test-NativeCommand $candidate "-c" "import yaml") {
                return $candidate
            }
        }
    }

    # Second pass: standard version check
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

Write-Host "== LAS 8-Step Golden Verification Ladder =="
Write-Host "Workspace: $Root"
Write-Host "Python path: $pythonPath"

Write-Host "`n[1/8] Python compile check"
$pythonFiles = @(
    "agent_workspace\api.py",
    "agent_workspace\core\engine.py",
    "agent_workspace\core\precheck.py",
    "agent_workspace\core\providers.py",
    "agent_workspace\core\router.py",
    "agent_workspace\core\token_counter.py",
    "agent_workspace\core\ws_manager.py",
    "agent_workspace\long_term_memory.py",
    "agent_workspace\memory_backends.py",
    "agent_workspace\observability.py",
    "agent_workspace\pap_validate.py",
    "agent_workspace\tool_manifest.py",
    "agent_workspace\topology_bridge.py",
    "agent_workspace\topology_stream.py",
    "agent_workspace\workflow_lint.py",
    "scripts\git_guard.py"
)
Invoke-Python "-m" "py_compile" @pythonFiles

if (-not $SkipTests) {
    Write-Host "`n[2/8] Python test suite"
    $hasPytest = Test-NativeCommand $pythonPath "-m" "pytest" "--version"
    if ($hasPytest) {
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
    } else {
        Write-Warning "pytest not installed in active environment ($pythonPath). Run .\scripts\bootstrap_verify.ps1 or pass -PythonPath to run tests."
    }
}
else {
    Write-Host "`n[2/8] Python test suite skipped"
}

Write-Host "`n[3/8] PAP workspace & workflow schema contract"
Invoke-Python "agent_workspace\pap_validate.py"
if (Test-Path "agent_workspace\workflow_lint.py") {
    Invoke-Python "agent_workspace\workflow_lint.py" "validate" "spec\workflow.schema.json"
}

Write-Host "`n[4/8] Runtime tool manifest contract & skills matrix"
Invoke-Python "agent_workspace\tool_manifest.py" "validate"
Write-Host "Generating skills acceptance matrix..."
Invoke-Python "agent_workspace\tool_manifest.py" "matrix"

if (-not $SkipLint) {
    Write-Host "`n[5/8] Knowledge base & Obsidian vault integrity"
    $kbLinter = Join-Path $Root ".agent\knowledge_base\tools\lint_knowledge_base.ps1"
    if (Test-Path $kbLinter) {
        Write-Host "Auditing Knowledge Base..."
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $kbLinter
        if ($LASTEXITCODE -ne 0) {
            throw "Knowledge base audit failed with exit code $LASTEXITCODE"
        }
    }
    $vaultLinter = Join-Path $Root ".agent\knowledge_base\tools\lint_obsidian_vault.ps1"
    if (Test-Path $vaultLinter) {
        Write-Host "Auditing Obsidian Vault..."
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $vaultLinter
        if ($LASTEXITCODE -ne 0) {
            throw "Obsidian vault audit failed with exit code $LASTEXITCODE"
        }
    }
} else {
    Write-Host "`n[5/8] Knowledge base & Obsidian vault integrity check skipped"
}

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
    $npmPath = Resolve-NpmPath
    Push-Location viewer
    try {
        Write-Host "`n[6/8] Viewer production build (Rolldown / Vite)"
        Invoke-Native $npmPath "run" "build"

        Write-Host "`n[7/8] Viewer UI smoke & swarm governance tests"
        Invoke-Native $npmPath "run" "verify:ui"
        Invoke-Native $npmPath "run" "test:swarm-ui"

        if (-not $SkipDoctor) {
            Write-Host "`n[8/8] React Doctor code quality check"
            Invoke-Native $npmPath "run" "doctor"
        } else {
            Write-Host "`n[8/8] React Doctor code quality check skipped"
        }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "`n[6/8] Viewer production build skipped"
    Write-Host "[7/8] Viewer UI smoke tests skipped"
    Write-Host "[8/8] React Doctor code quality check skipped"
}

Write-Host "`nLAS verification complete."
