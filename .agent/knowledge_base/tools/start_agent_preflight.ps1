[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Query,
    [int]$Top = 5,
    [string]$OutputPath = '',
    [switch]$NoRefresh
)

$ErrorActionPreference = 'Stop'

function Resolve-KnowledgeRoot {
    $scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    return (Resolve-Path (Join-Path $scriptRoot '..')).Path
}

function Get-Slug {
    param([Parameter(Mandatory = $true)][string]$Text)

    $slug = ($Text.ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
    if ([string]::IsNullOrWhiteSpace($slug)) {
        return 'query'
    }
    if ($slug.Length -gt 60) {
        return $slug.Substring(0, 60).Trim('-')
    }
    return $slug
}

$root = Resolve-KnowledgeRoot
$toolsDir = Join-Path $root 'tools'
$buildScript = Join-Path $toolsDir 'build_context_pack.ps1'
$validateScript = Join-Path $toolsDir 'validate_context_pack.ps1'

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $slug = Get-Slug -Text $Query
    $OutputPath = Join-Path $root ("handoffs/agent-start-preflight-latest-$slug.md")
}

if ($NoRefresh) {
    $buildJson = & powershell -NoProfile -ExecutionPolicy Bypass -File $buildScript -Query $Query -Top $Top -OutputPath $OutputPath
} else {
    $buildJson = & powershell -NoProfile -ExecutionPolicy Bypass -File $buildScript -Query $Query -Top $Top -OutputPath $OutputPath -Refresh
}

$build = $buildJson | ConvertFrom-Json
$validationJson = & powershell -NoProfile -ExecutionPolicy Bypass -File $validateScript -PackPath $build.output -Format Json
$validation = $validationJson | ConvertFrom-Json

if (-not $validation.passed) {
    throw "Generated context pack failed validation: $($build.output)"
}

[pscustomobject]@{
    query = $Query
    pack = $build.output
    candidates = $build.candidates
    validated = $validation.passed
    validation_line_count = $validation.line_count
    contains_full_text = $build.contains_full_text
    next_action = 'Read the pack first, then read candidate notes in order, then verify current-state claims live.'
} | ConvertTo-Json -Depth 4
