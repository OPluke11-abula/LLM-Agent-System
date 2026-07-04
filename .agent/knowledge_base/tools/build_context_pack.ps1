[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Query,
    [string]$OutputPath = '',
    [int]$Top = 5,
    [string]$InventoryPath = '',
    [switch]$Refresh
)

$ErrorActionPreference = 'Stop'

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

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
$refreshScript = Join-Path $toolsDir 'refresh_knowledge_inventory.ps1'
$queryScript = Join-Path $toolsDir 'query_knowledge_inventory.ps1'

if ($Refresh) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $refreshScript | Out-Null
}

if ([string]::IsNullOrWhiteSpace($InventoryPath)) {
    $InventoryPath = Join-Path $root 'indexes\knowledge-inventory-latest.json'
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $slug = Get-Slug -Text $Query
    $OutputPath = Join-Path $root ("handoffs/context-pack-latest-$slug.md")
}

$outputDir = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$queryJson = & powershell -NoProfile -ExecutionPolicy Bypass -File $queryScript -Query $Query -Top $Top -InventoryPath $InventoryPath -Format Json
$queryResult = $queryJson | ConvertFrom-Json

$pack = New-Object System.Text.StringBuilder
[void]$pack.AppendLine("# Context Pack - $Query")
[void]$pack.AppendLine()
[void]$pack.AppendLine("Generated: $(Get-Date -Format 'yyyy-MM-dd')")
[void]$pack.AppendLine()
[void]$pack.AppendLine("## Query")
[void]$pack.AppendLine()
[void]$pack.AppendLine($Query)
[void]$pack.AppendLine()
[void]$pack.AppendLine("## Inventory")
[void]$pack.AppendLine()
[void]$pack.AppendLine("- Source: $InventoryPath")
[void]$pack.AppendLine("- Contains full text: $($queryResult.contains_full_text)")
[void]$pack.AppendLine()
[void]$pack.AppendLine("## Read Order")
[void]$pack.AppendLine()

if ($queryResult.results.Count -eq 0) {
    [void]$pack.AppendLine("- No candidates found. Use live discovery and update the knowledge base if reusable memory is created.")
} else {
    $i = 1
    foreach ($item in $queryResult.results) {
        [void]$pack.AppendLine("$i. $($item.path) - $($item.title)")
        $i++
    }
}

[void]$pack.AppendLine()
[void]$pack.AppendLine("## Candidate Details")
[void]$pack.AppendLine()

foreach ($item in $queryResult.results) {
    [void]$pack.AppendLine("### $($item.path)")
    [void]$pack.AppendLine()
    [void]$pack.AppendLine("- Title: $($item.title)")
    [void]$pack.AppendLine("- Type: $($item.type)")
    [void]$pack.AppendLine("- Score: $($item.score)")
    [void]$pack.AppendLine("- Matched: $(@($item.matched) -join ', ')")
    [void]$pack.AppendLine("- Read first: $($item.read_first)")
    [void]$pack.AppendLine()
}

[void]$pack.AppendLine("## Verification Needed")
[void]$pack.AppendLine()
[void]$pack.AppendLine("- Treat this context pack as orientation only.")
[void]$pack.AppendLine("- Verify current git status, code, config, tool versions, tests, builds, plugins, and external docs live before making current-state claims.")
[void]$pack.AppendLine("- If the query leads to code work, use repository code-discovery tools and focused tests before claiming success.")
[void]$pack.AppendLine()
[void]$pack.AppendLine("## Not Included")
[void]$pack.AppendLine()
[void]$pack.AppendLine("- Full note bodies are not copied into this pack.")
[void]$pack.AppendLine("- Secrets, credentials, caches, databases, and generated workspace state are not intentionally included.")

Write-Utf8NoBom -Path $OutputPath -Content $pack.ToString()

[pscustomobject]@{
    query = $Query
    output = $OutputPath
    candidates = @($queryResult.results).Count
    contains_full_text = $false
} | ConvertTo-Json -Depth 4
