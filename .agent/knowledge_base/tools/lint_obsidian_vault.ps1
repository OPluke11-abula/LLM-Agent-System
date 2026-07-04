[CmdletBinding()]
param(
    [string]$VaultPath = '',
    [ValidateSet('Markdown', 'Json')][string]$Format = 'Markdown',
    [ValidateSet('None', 'Critical', 'High', 'Medium', 'Low', 'Info')][string]$FailOn = 'None'
)

$ErrorActionPreference = 'Stop'

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

if ([string]::IsNullOrWhiteSpace($VaultPath)) {
    $oneDrive = Join-Path $env:USERPROFILE 'OneDrive'
    $candidate = @(Get-ChildItem -LiteralPath $oneDrive -Directory -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq 'Obsidian Vault' } |
        Select-Object -First 1)
    if ($candidate.Count -eq 0) {
        throw "Could not auto-discover Obsidian Vault under $oneDrive. Pass -VaultPath explicitly."
    }
    $rootPath = $candidate[0].FullName
} else {
    $rootPath = (Resolve-Path -LiteralPath $VaultPath).Path
}
$findings = New-Object System.Collections.Generic.List[object]
$indexPath = Join-Path $rootPath 'index.md'
$logPath = Join-Path $rootPath 'log.md'
$requiredDirs = @('raw', 'wiki', 'workflows', 'handoffs', 'decisions', 'known-issues', 'exports', 'templates')

foreach ($dir in $requiredDirs) {
    if (-not (Test-Path -LiteralPath (Join-Path $rootPath $dir))) {
        Add-Finding $findings 'High' 'missing-required-directory' $dir "Required vault directory is missing: $dir"
    }
}
if (-not (Test-Path -LiteralPath $indexPath)) {
    Add-Finding $findings 'Critical' 'missing-index' 'index.md' 'Vault index.md is missing.'
}
if (-not (Test-Path -LiteralPath $logPath)) {
    Add-Finding $findings 'High' 'missing-log' 'log.md' 'Vault log.md is missing.'
}

$indexedPathSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
if (Test-Path -LiteralPath $indexPath) {
    $indexText = Get-Content -LiteralPath $indexPath -Raw
    foreach ($match in [regex]::Matches($indexText, '\[\[([^\]]+)\]\]')) {
        $target = (($match.Groups[1].Value -split '\|')[0] -split '#')[0].Trim().Replace('\', '/')
        if (-not [string]::IsNullOrWhiteSpace($target)) {
            [void]$indexedPathSet.Add($target)
            [void]$indexedPathSet.Add(($target -replace '\.md$', ''))
        }
    }
}

$markdownFiles = @(Get-ChildItem -LiteralPath $rootPath -Recurse -File -Filter '*.md' |
    Where-Object { $_.FullName -notmatch '\\.obsidian\\' } |
    Sort-Object FullName)
$stemIndex = @{}
foreach ($file in $markdownFiles) {
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($file.Name).ToLowerInvariant()
    if (-not $stemIndex.ContainsKey($stem)) { $stemIndex[$stem] = New-Object System.Collections.Generic.List[string] }
    [void]$stemIndex[$stem].Add($file.FullName)
}

foreach ($file in $markdownFiles) {
    $relative = Get-RelativePath -RootPath $rootPath -Path $file.FullName
    $slashRelative = $relative.Replace('\', '/')
    $topDir = ($slashRelative -split '/')[0]

    if ($file.Length -eq 0) {
        if ($requiredDirs -contains $topDir) {
            Add-Finding $findings 'High' 'empty-markdown' $slashRelative 'Markdown file is empty.'
        } else {
            Add-Finding $findings 'Info' 'empty-root-note' $slashRelative 'Root-level scratch/default note is empty.'
        }
    }

    if ($requiredDirs -contains $topDir) {
        $slashWithoutExt = $slashRelative -replace '\.md$', ''
        if ($indexText -and -not ($indexedPathSet.Contains($slashRelative) -or $indexedPathSet.Contains($slashWithoutExt))) {
            Add-Finding $findings 'Medium' 'not-linked-from-index' $slashRelative 'Contract-directory note is not linked from index.md.'
        }
    }

    $text = Get-Content -LiteralPath $file.FullName -Raw
    if ($null -eq $text) { $text = '' }
    $secretPattern = '(?i)(authorization:\s*bearer\s+[A-Za-z0-9._-]{8,}|\bsk-[A-Za-z0-9]{8,}|\b(api[_-]?key|secret|token|password|cookie)\b\s*[:=]\s*[^\s`''"]{4,})'
    if ($text -match $secretPattern) {
        Add-Finding $findings 'High' 'potential-secret-string' $slashRelative 'Potential credential-like string found; inspect before sharing or committing.'
    }

    foreach ($match in [regex]::Matches($text, '\[\[([^\]]+)\]\]')) {
        $rawLink = $match.Groups[1].Value
        $plainLink = (($rawLink -split '\|')[0] -split '#')[0].Trim()
        if ($plainLink -eq 'wikilinks') { continue }
        $resolved = Resolve-WikilinkPath -RootPath $rootPath -SourceDirectory $file.DirectoryName -RawLink $rawLink -StemIndex $stemIndex
        if (-not [string]::IsNullOrWhiteSpace($resolved) -and -not (Test-Path -LiteralPath $resolved)) {
            Add-Finding $findings 'Medium' 'unresolved-wikilink' $slashRelative "Unresolved wikilink: $rawLink"
        }
    }
}

$severityRank = @{ Critical = 5; High = 4; Medium = 3; Low = 2; Info = 1; None = 0 }
$ordered = @($findings | Sort-Object @{ Expression = { $severityRank[$_.severity] }; Descending = $true }, @{ Expression = 'path'; Descending = $false }, @{ Expression = 'code'; Descending = $false })
$summary = [ordered]@{
    vault = $rootPath
    markdown_files = $markdownFiles.Count
    findings = $ordered.Count
    critical = @($ordered | Where-Object severity -eq 'Critical').Count
    high = @($ordered | Where-Object severity -eq 'High').Count
    medium = @($ordered | Where-Object severity -eq 'Medium').Count
    low = @($ordered | Where-Object severity -eq 'Low').Count
    info = @($ordered | Where-Object severity -eq 'Info').Count
}

if ($Format -eq 'Json') {
    [pscustomobject]@{
        summary = [pscustomobject]$summary
        findings = $ordered
    } | ConvertTo-Json -Depth 8
} else {
    '# Obsidian Vault Health Audit'
    ''
    "Vault: $rootPath"
    "Markdown files: $($summary.markdown_files)"
    "Findings: $($summary.findings)"
    "Critical: $($summary.critical); High: $($summary.high); Medium: $($summary.medium); Low: $($summary.low); Info: $($summary.info)"
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
    '- Root-level scratch/default notes are not treated as index blockers.'
    '- Current repo, test, build, and external-tool claims still require live verification.'
}

if ($FailOn -ne 'None') {
    $threshold = $severityRank[$FailOn]
    $shouldFail = @($ordered | Where-Object { $severityRank[$_.severity] -ge $threshold }).Count -gt 0
    if ($shouldFail) { exit 2 }
}
