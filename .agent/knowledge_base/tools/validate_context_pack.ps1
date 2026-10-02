[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PackPath,
    [string]$Root = '',
    [int]$MaxLines = 120,
    [ValidateSet('Markdown', 'Json')][string]$Format = 'Markdown'
)

$ErrorActionPreference = 'Stop'

function Resolve-KnowledgeRoot {
    $scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    return (Resolve-Path (Join-Path $scriptRoot '..')).Path
}

function Add-Check {
    param(
        [System.Collections.Generic.List[object]]$Checks,
        [string]$Name,
        $Passed,
        [string]$Detail
    )

    [void]$Checks.Add([pscustomobject]@{
        name = $Name
        passed = [bool]$Passed
        detail = $Detail
    })
}

if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = Resolve-KnowledgeRoot
}
$rootPath = (Resolve-Path $Root).Path
$resolvedPack = (Resolve-Path $PackPath).Path
$pack = Get-Content -LiteralPath $resolvedPack -Raw
$lines = @($pack -split "`r?`n")
$checks = New-Object System.Collections.Generic.List[object]

$requiredSections = @(
    '## Query',
    '## Inventory',
    '## Read Order',
    '## Candidate Details',
    '## Verification Needed',
    '## Not Included'
)

foreach ($section in $requiredSections) {
    Add-Check $checks "section:$section" ($pack.Contains($section)) "Required section $section must be present."
}

Add-Check $checks 'contains_full_text_false' ($pack.Contains('Contains full text: False')) 'Pack must declare that inventory did not contain full text.'
Add-Check $checks 'no_full_note_bodies_notice' ($pack.Contains('Full note bodies are not copied')) 'Pack must explicitly say full note bodies are not copied.'
Add-Check $checks 'live_verification_notice' ($pack.Contains('Verify current git status') -or $pack.Contains('live before')) 'Pack must remind agents to verify current state live.'
Add-Check $checks 'line_budget' ($lines.Count -le $MaxLines) "Pack has $($lines.Count) lines; max is $MaxLines."

$candidateMatches = [regex]::Matches($pack, '(?m)^\d+\.\s+([^\s]+\.md)\s+-\s+(.+)$')
$candidatePaths = @($candidateMatches | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique)
Add-Check $checks 'candidate_count' ($candidatePaths.Count -gt 0) "Found $($candidatePaths.Count) candidate paths in read order."

$missing = New-Object System.Collections.Generic.List[string]
foreach ($candidate in $candidatePaths) {
    $candidatePath = Join-Path $rootPath ($candidate -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $candidatePath)) {
        [void]$missing.Add($candidate)
    }
}
Add-Check $checks 'candidate_files_exist' ($missing.Count -eq 0) $(if ($missing.Count -eq 0) { 'All candidate files exist.' } else { 'Missing: ' + (@($missing) -join ', ') })

$credentialPatterns = @(
    '(?i)(api[_-]?key|secret|token|password|passwd|cookie)\s*[:=]\s*[''"]?[A-Za-z0-9_./+\-=]{12,}',
    '(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{12,}',
    'sk-[A-Za-z0-9]{20,}',
    'ghp_[A-Za-z0-9]{20,}',
    'AIza[0-9A-Za-z_-]{20,}'
)
$credentialHit = $false
foreach ($pattern in $credentialPatterns) {
    if ($pack -match $pattern) {
        $credentialHit = $true
        break
    }
}
Add-Check $checks 'credential_value_scan' (-not $credentialHit) 'Pack must not contain likely credential values.'

$passed = -not (@($checks | Where-Object { -not $_.passed }).Count)
$result = [pscustomobject]@{
    pack = $resolvedPack
    root = $rootPath
    passed = [bool]$passed
    candidates = [object[]]@($candidatePaths)
    line_count = $lines.Count
    checks = [object[]]@($checks.ToArray())
}

if ($Format -eq 'Json') {
    $result | ConvertTo-Json -Depth 8
} else {
    "# Context Pack Validation"
    ""
    "Pack: $resolvedPack"
    "Passed: $passed"
    "Candidates: $($candidatePaths.Count)"
    "Lines: $($lines.Count)"
    ""
    "## Checks"
    ""
    foreach ($check in $checks) {
        $status = if ($check.passed) { 'PASS' } else { 'FAIL' }
        "- $status $($check.name): $($check.detail)"
    }
}

if (-not $passed) {
    exit 1
}
