[CmdletBinding()]
param(
    [string]$Root = '',
    [string]$Date = (Get-Date -Format 'yyyy-MM-dd'),
    [string]$OutputStem = 'knowledge-inventory-latest'
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

function Get-RelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$FullPath
    )

    $base = [System.IO.Path]::GetFullPath($BasePath).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $full = [System.IO.Path]::GetFullPath($FullPath)
    return $full.Substring($base.Length).Replace('\', '/')
}

function Get-NoteType {
    param([Parameter(Mandatory = $true)][string]$RelativePath)

    $first = ($RelativePath -split '/')[0]
    switch ($first) {
        'projects' { 'project' }
        'workflows' { 'workflow' }
        'decisions' { 'decision' }
        'known-issues' { 'known_issue' }
        'handoffs' { 'handoff' }
        'evidence' { 'evidence' }
        'exports' { 'export' }
        'templates' { 'template' }
        default {
            if ($RelativePath -eq 'index.md') { 'router' }
            elseif ($RelativePath -eq 'log.md') { 'audit_log' }
            else { 'note' }
        }
    }
}

function Get-SearchCues {
    param(
        [string]$RelativePath,
        [string]$Title,
        [string[]]$Headings,
        [string[]]$Links
    )

    $text = @($RelativePath, $Title) + $Headings + $Links
    $words = ($text -join ' ') -split '[^A-Za-z0-9_-]+' |
        Where-Object { $_ -and $_.Length -ge 3 } |
        ForEach-Object { $_.Trim().ToLowerInvariant() } |
        Where-Object { $_ -notin @('the', 'and', 'for', 'with', 'from', 'this', 'that', 'workflow', 'notes') }

    return @($words | Select-Object -Unique -First 12)
}

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = Join-Path $scriptRoot '..'
}

$rootPath = (Resolve-Path $Root).Path
$indexDir = Join-Path $rootPath 'indexes'
if (-not (Test-Path -LiteralPath $indexDir)) {
    New-Item -ItemType Directory -Path $indexDir | Out-Null
}

$excludedSegments = @('/indexes/', '/tools/')
$markdownFiles = Get-ChildItem -LiteralPath $rootPath -Recurse -File -Filter '*.md' |
    Where-Object {
        $relative = Get-RelativePath -BasePath $rootPath -FullPath $_.FullName
        $normalized = '/' + $relative
        -not ($excludedSegments | Where-Object { $normalized.Contains($_) })
    } |
    Sort-Object FullName

$entries = foreach ($file in $markdownFiles) {
    $relative = Get-RelativePath -BasePath $rootPath -FullPath $file.FullName
    $lines = Get-Content -LiteralPath $file.FullName
    $titleLine = @($lines | Where-Object { $_ -match '^#\s+' } | Select-Object -First 1)
    $title = if ($titleLine.Count -gt 0) { ($titleLine[0] -replace '^#\s+', '').Trim() } else { [System.IO.Path]::GetFileNameWithoutExtension($file.Name) }
    $headings = @($lines | Where-Object { $_ -match '^#{1,3}\s+' } | Select-Object -First 10 | ForEach-Object { ($_ -replace '^#{1,3}\s+', '').Trim() })
    $allText = $lines -join "`n"
    $links = @([regex]::Matches($allText, '\[\[([^\]]+)\]\]') | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique -First 12)
    $cues = Get-SearchCues -RelativePath $relative -Title $title -Headings $headings -Links $links

    [pscustomobject]@{
        path = $relative
        type = Get-NoteType -RelativePath $relative
        title = $title
        headings = $headings
        links = $links
        cues = $cues
    }
}

$jsonObject = [pscustomobject]@{
    generated = $Date
    root = $rootPath.Replace('\', '/')
    purpose = 'Token-saving local inventory for ranking LAS knowledge notes before reading them.'
    contains_full_text = $false
    excluded_segments = $excludedSegments
    ranking_order = @('exact_title', 'path_segment', 'heading', 'wikilink', 'search_cue', 'body_search_fallback')
    entries = @($entries)
}

$jsonPath = Join-Path $indexDir ($OutputStem + '.json')
$mdPath = Join-Path $indexDir ($OutputStem + '.md')

$json = $jsonObject | ConvertTo-Json -Depth 8
Write-Utf8NoBom -Path $jsonPath -Content ($json + "`n")

$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine("# LAS Knowledge Inventory - Latest")
[void]$md.AppendLine()
[void]$md.AppendLine("Generated: $Date")
[void]$md.AppendLine()
[void]$md.AppendLine("This inventory is generated from compact metadata only. It does not store full note bodies.")
[void]$md.AppendLine()
[void]$md.AppendLine("## Ranking Rules")
[void]$md.AppendLine()
[void]$md.AppendLine("1. exact title match")
[void]$md.AppendLine("2. path segment match")
[void]$md.AppendLine("3. heading match")
[void]$md.AppendLine("4. wikilink match")
[void]$md.AppendLine("5. search cue match")
[void]$md.AppendLine("6. broad body search fallback")
[void]$md.AppendLine()
[void]$md.AppendLine("## Entries")
[void]$md.AppendLine()

foreach ($entry in $entries) {
    [void]$md.AppendLine("### $($entry.path)")
    [void]$md.AppendLine()
    [void]$md.AppendLine("- Type: $($entry.type)")
    [void]$md.AppendLine("- Title: $($entry.title)")
    $headingText = if (@($entry.headings).Count -gt 0) { @($entry.headings) -join '; ' } else { '(none)' }
    $linkText = if (@($entry.links).Count -gt 0) { @($entry.links) -join '; ' } else { '(none)' }
    $cueText = if (@($entry.cues).Count -gt 0) { @($entry.cues) -join ', ' } else { '(none)' }
    [void]$md.AppendLine("- Headings: $headingText")
    [void]$md.AppendLine("- Links: $linkText")
    [void]$md.AppendLine("- Search cues: $cueText")
    [void]$md.AppendLine()
}

Write-Utf8NoBom -Path $mdPath -Content ($md.ToString().TrimEnd() + "`n")

[pscustomobject]@{
    root = $rootPath
    entries = @($entries).Count
    markdown = $mdPath
    json = $jsonPath
    contains_full_text = $false
} | ConvertTo-Json -Depth 4
