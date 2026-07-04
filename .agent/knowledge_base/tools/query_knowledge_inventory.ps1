[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Query,
    [string]$InventoryPath = '',
    [int]$Top = 5,
    [ValidateSet('Markdown', 'Json')][string]$Format = 'Markdown'
)

$ErrorActionPreference = 'Stop'

function Resolve-DefaultInventoryPath {
    $scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    return (Resolve-Path (Join-Path $scriptRoot '..\indexes\knowledge-inventory-latest.json')).Path
}

function Get-Terms {
    param([Parameter(Mandatory = $true)][string]$Text)

    return @($Text -split '[^A-Za-z0-9_-]+' |
        Where-Object { $_ -and $_.Length -ge 2 } |
        ForEach-Object { $_.ToLowerInvariant() } |
        Select-Object -Unique)
}

function Join-Field {
    param($Value)

    if ($null -eq $Value) {
        return ''
    }

    return (@($Value) -join ' ')
}

function Get-TypeWeight {
    param([string]$Type)

    switch ($Type) {
        'workflow' { return 18 }
        'known_issue' { return 16 }
        'project' { return 12 }
        'decision' { return 10 }
        'handoff' { return 8 }
        'evidence' { return 6 }
        'template' { return 2 }
        'export' { return -10 }
        'router' { return -18 }
        'audit_log' { return -18 }
        default { return 0 }
    }
}

if ([string]::IsNullOrWhiteSpace($InventoryPath)) {
    $InventoryPath = Resolve-DefaultInventoryPath
}

$inventory = Get-Content -LiteralPath $InventoryPath -Raw | ConvertFrom-Json
if ($inventory.contains_full_text -ne $false) {
    throw "Inventory must have contains_full_text=false."
}

$terms = Get-Terms -Text $Query
if ($terms.Count -eq 0) {
    throw "Query contains no searchable terms."
}

$queryLower = $Query.ToLowerInvariant()

$results = foreach ($entry in $inventory.entries) {
    $score = 0
    $matched = New-Object System.Collections.Generic.List[string]

    $title = Join-Field $entry.title
    $path = Join-Field $entry.path
    $headings = Join-Field $entry.headings
    $cues = Join-Field $entry.cues
    $links = Join-Field $entry.links
    $headingsLower = $headings.ToLowerInvariant()
    $cuesLower = $cues.ToLowerInvariant()

    if ($title.ToLowerInvariant().Contains($queryLower)) {
        $score += 40
        [void]$matched.Add('exact-title')
    }
    if ($path.ToLowerInvariant().Contains($queryLower.Replace(' ', '-'))) {
        $score += 24
        [void]$matched.Add('exact-path')
    }
    if ($headingsLower.Contains($queryLower)) {
        $score += 32
        [void]$matched.Add('exact-heading')
    }
    if ($cuesLower.Contains($queryLower)) {
        $score += 16
        [void]$matched.Add('exact-cue')
    }

    foreach ($term in $terms) {
        $escaped = [regex]::Escape($term)
        if ($title -match $escaped) {
            $score += 12
            [void]$matched.Add("title:$term")
        }
        if ($path -match $escaped) {
            $score += 9
            [void]$matched.Add("path:$term")
        }
        if ($headings -match $escaped) {
            $score += 6
            [void]$matched.Add("heading:$term")
        }
        if ($cues -match $escaped) {
            $score += 4
            [void]$matched.Add("cue:$term")
        }
        if ($links -match $escaped) {
            $score += 1
            [void]$matched.Add("link:$term")
        }
    }

    $typeWeight = Get-TypeWeight -Type $entry.type
    if ($typeWeight -ne 0) {
        $score += $typeWeight
        [void]$matched.Add("type-weight:$($entry.type):$typeWeight")
    }

    if ($entry.type -in @('router', 'audit_log')) {
        [void]$matched.Add('navigation-penalty')
    }

    if ($score -gt 0) {
        [pscustomobject]@{
            path = $entry.path
            title = $entry.title
            type = $entry.type
            score = $score
            matched = @($matched | Select-Object -Unique)
            read_first = $entry.type -notin @('router', 'audit_log')
        }
    }
}

$ranked = @($results | Sort-Object @{Expression = 'score'; Descending = $true}, @{Expression = 'path'; Descending = $false} | Select-Object -First $Top)

if ($Format -eq 'Json') {
    [pscustomobject]@{
        query = $Query
        inventory = $InventoryPath
        contains_full_text = $false
        results = $ranked
    } | ConvertTo-Json -Depth 8
    exit 0
}

"# Inventory Query"
""
"Query: $Query"
"Inventory: $InventoryPath"
""
"## Ranked Candidates"
""
if ($ranked.Count -eq 0) {
    "- No candidates found."
} else {
    foreach ($item in $ranked) {
        "- $($item.path)"
        "  - title: $($item.title)"
        "  - type: $($item.type)"
        "  - score: $($item.score)"
        "  - matched: $(@($item.matched) -join ', ')"
        "  - read_first: $($item.read_first)"
    }
}
""
"## Verification Needed"
""
"- Treat these candidates as orientation only."
"- Verify current repo, tool, test, build, and plugin claims live before reporting them as current facts."
