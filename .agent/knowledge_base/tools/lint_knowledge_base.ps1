[CmdletBinding()]
param(
    [string]$Root = '',
    [ValidateSet('Markdown', 'Json')][string]$Format = 'Markdown',
    [ValidateSet('None', 'Critical', 'High', 'Medium', 'Low', 'Info')][string]$FailOn = 'None'
)

$ErrorActionPreference = 'Stop'

function Resolve-KnowledgeRoot {
    if (-not [string]::IsNullOrWhiteSpace($Root)) {
        return (Resolve-Path -LiteralPath $Root).Path
    }

    $scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    return (Resolve-Path (Join-Path $scriptRoot '..')).Path
}

function Add-Finding {
    param(
        [System.Collections.Generic.List[object]]$Findings,
        [Parameter(Mandatory = $true)][string]$Severity,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Message
    )

    [void]$Findings.Add([pscustomobject]@{
        severity = $Severity
        code = $Code
        path = $Path
        message = $Message
    })
}

function Get-RelativePath {
    param([Parameter(Mandatory = $true)][string]$RootPath, [Parameter(Mandatory = $true)][string]$Path)

    $rootUri = [System.Uri]::new(($RootPath.TrimEnd('\') + '\'))
    $pathUri = [System.Uri]::new($Path)
    return [System.Uri]::UnescapeDataString($rootUri.MakeRelativeUri($pathUri).ToString()).Replace('/', '\')
}

function Test-IndexedPath {
    param([string]$IndexText, [string]$RelativePath)

    $slashPath = $RelativePath.Replace('\', '/')
    $withoutExt = $slashPath -replace '\\.md$', ''
    return $IndexText.Contains($slashPath) -or $IndexText.Contains($withoutExt)
}

function Resolve-WikilinkPath {
    param(
        [string]$RootPath,
        [string]$SourceDirectory,
        [string]$RawLink,
        [hashtable]$StemIndex
    )

    $target = ($RawLink -split '\|')[0]
    $target = ($target -split '#')[0]
    $target = $target.Trim()
    if ([string]::IsNullOrWhiteSpace($target)) { return $null }
    if ($target -match '^(https?|file):') { return $null }
    if (-not $target.EndsWith('.md')) { $target = "$target.md" }

    $normalized = $target.Replace('/', '\')
    if ($normalized.Contains('\')) {
        if ($normalized.StartsWith('..\') -or $normalized.StartsWith('.\')) {
            return [System.IO.Path]::GetFullPath((Join-Path $SourceDirectory $normalized))
        }
        return Join-Path $RootPath $normalized
    }

    $sameDirectory = Join-Path $SourceDirectory $normalized
    if (Test-Path -LiteralPath $sameDirectory) { return $sameDirectory }

    $stem = [System.IO.Path]::GetFileNameWithoutExtension($normalized).ToLowerInvariant()
    if ($StemIndex.ContainsKey($stem) -and @($StemIndex[$stem]).Count -eq 1) {
        return @($StemIndex[$stem])[0]
    }

    return Join-Path $RootPath $normalized
}

$rootPath = Resolve-KnowledgeRoot
$findings = New-Object System.Collections.Generic.List[object]
$indexPath = Join-Path $rootPath 'index.md'
$latestInventoryPath = Join-Path $rootPath 'indexes\knowledge-inventory-latest.json'

$indexedPathSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
if (-not (Test-Path -LiteralPath $indexPath)) {
    Add-Finding $findings 'Critical' 'missing-index' 'index.md' 'Knowledge base index.md is missing.'
} else {
    $indexText = Get-Content -LiteralPath $indexPath -Raw
    foreach ($match in [regex]::Matches($indexText, '\[\[([^\]]+)\]\]')) {
        $target = (($match.Groups[1].Value -split '\|')[0] -split '#')[0].Trim().Replace('\', '/')
        if (-not [string]::IsNullOrWhiteSpace($target)) {
            [void]$indexedPathSet.Add($target)
            [void]$indexedPathSet.Add(($target -replace '\.md$', ''))
        }
    }
    foreach ($match in [regex]::Matches($indexText, '\[[^\]]+\]\(([^)]+)\)')) {
        $target = (($match.Groups[1].Value -split '#')[0]).Trim().Replace('\', '/')
        if (-not [string]::IsNullOrWhiteSpace($target) -and $target -notmatch '^(https?|file):') {
            [void]$indexedPathSet.Add($target)
            [void]$indexedPathSet.Add(($target -replace '\.md$', ''))
        }
    }
}

$markdownFiles = @(Get-ChildItem -LiteralPath $rootPath -Recurse -File -Filter '*.md' | Sort-Object FullName)
$stemIndex = @{}
foreach ($file in $markdownFiles) {
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($file.Name).ToLowerInvariant()
    if (-not $stemIndex.ContainsKey($stem)) { $stemIndex[$stem] = New-Object System.Collections.Generic.List[string] }
    [void]$stemIndex[$stem].Add($file.FullName)
}
$indexedDirs = @('projects', 'workflows', 'decisions', 'known-issues', 'evidence', 'handoffs', 'exports')
foreach ($file in $markdownFiles) {
    $relative = Get-RelativePath -RootPath $rootPath -Path $file.FullName
    $slashRelative = $relative.Replace('\', '/')
    if ($file.Length -eq 0) {
        Add-Finding $findings 'High' 'empty-markdown' $slashRelative 'Markdown file is empty.'
    }

    if ($slashRelative -ne 'index.md' -and $slashRelative -ne 'log.md') {
        $topDir = ($slashRelative -split '/')[0]
        $slashWithoutExt = $slashRelative -replace '\.md$', ''
        if ($indexedDirs -contains $topDir -and $indexText -and -not ($indexedPathSet.Contains($slashRelative) -or $indexedPathSet.Contains($slashWithoutExt))) {
            Add-Finding $findings 'Medium' 'not-linked-from-index' $slashRelative 'Task-facing note is not linked from index.md.'
        }
    }

    $text = Get-Content -LiteralPath $file.FullName -Raw
    $secretPattern = '(?i)(authorization:\s*bearer\s+[A-Za-z0-9._-]{8,}|\bsk-[A-Za-z0-9]{8,}|\b(api[_-]?key|secret|token|password|cookie)\b\s*[:=]\s*[^\s`''"]{4,})'
    if ($text -match $secretPattern) {
        Add-Finding $findings 'High' 'potential-secret-string' $slashRelative 'Potential credential-like string found; inspect before sharing or committing.'
    }

    foreach ($match in [regex]::Matches($text, '\[\[([^\]]+)\]\]')) {
        $resolved = Resolve-WikilinkPath -RootPath $rootPath -SourceDirectory $file.DirectoryName -RawLink $match.Groups[1].Value -StemIndex $stemIndex
        if ($resolved -and -not (Test-Path -LiteralPath $resolved)) {
            Add-Finding $findings 'Medium' 'unresolved-wikilink' $slashRelative "Unresolved wikilink: $($match.Groups[1].Value)"
        }
    }
}

if (-not (Test-Path -LiteralPath $latestInventoryPath)) {
    Add-Finding $findings 'Medium' 'missing-latest-inventory' 'indexes/knowledge-inventory-latest.json' 'Latest inventory JSON is missing.'
} else {
    try {
        $inventory = Get-Content -LiteralPath $latestInventoryPath -Raw | ConvertFrom-Json
        if ($inventory.contains_full_text -ne $false) {
            Add-Finding $findings 'High' 'inventory-contains-full-text' 'indexes/knowledge-inventory-latest.json' 'Inventory must keep contains_full_text=false.'
        }
    } catch {
        Add-Finding $findings 'High' 'invalid-inventory-json' 'indexes/knowledge-inventory-latest.json' "Inventory JSON failed to parse: $($_.Exception.Message)"
    }
}

$severityRank = @{ Critical = 5; High = 4; Medium = 3; Low = 2; Info = 1; None = 0 }
$ordered = @($findings | Sort-Object @{ Expression = { $severityRank[$_.severity] }; Descending = $true }, @{ Expression = 'path'; Descending = $false }, @{ Expression = 'code'; Descending = $false })
$summary = [ordered]@{
    root = $rootPath
    markdown_files = $markdownFiles.Count
    findings = $ordered.Count
    critical = @($ordered | Where-Object severity -eq 'Critical').Count
    high = @($ordered | Where-Object severity -eq 'High').Count
    medium = @($ordered | Where-Object severity -eq 'Medium').Count
    low = @($ordered | Where-Object severity -eq 'Low').Count
    info = @($ordered | Where-Object severity -eq 'Info').Count
    contains_full_text = if (Test-Path -LiteralPath $latestInventoryPath) { $inventory.contains_full_text } else { $null }
}

if ($Format -eq 'Json') {
    [pscustomobject]@{
        summary = [pscustomobject]$summary
        findings = $ordered
    } | ConvertTo-Json -Depth 8
} else {
    '# Knowledge Base Health Audit'
    ''
    "Root: $rootPath"
    "Markdown files: $($summary.markdown_files)"
    "Findings: $($summary.findings)"
    "Critical: $($summary.critical); High: $($summary.high); Medium: $($summary.medium); Low: $($summary.low); Info: $($summary.info)"
    "contains_full_text: $($summary.contains_full_text)"
    ''
    '## Findings'
    ''
    if ($ordered.Count -eq 0) {
        '- No findings.'
    } else {
        foreach ($finding in $ordered) {
            "- [$($finding.severity)] $($finding.code) - $($finding.path): $($finding.message)"
        }
    }
    ''
    '## Rule Notes'
    ''
    '- This audit is read-only.'
    '- Findings are orientation for future cleanup; current repo, test, build, and tool claims still require live verification.'
}

if ($FailOn -ne 'None') {
    $threshold = $severityRank[$FailOn]
    $shouldFail = @($ordered | Where-Object { $severityRank[$_.severity] -ge $threshold }).Count -gt 0
    if ($shouldFail) { exit 2 }
}
