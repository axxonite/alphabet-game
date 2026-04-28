# Builds phonemes.json from CMU Pronouncing Dictionary.
#
# Output: ../phonemes.json — { "word": ["P","H","O","N","E"], ... }
# Filtering rules:
#   - Keep entries with <= 4 phonemes (covers all plausible letter mishearings;
#     a kid spelling C-A-T won't trigger 6-syllable confusions).
#   - Strip CMU stress digits (EY1 -> EY) so the runtime can compare directly.
#   - Drop alternate-pronunciation entries marked "word(2)", "word(3)" — keep primary.
#   - Drop entries with non-alphabetic characters (punctuation tokens like "'TIS").
#
# Run from anywhere:
#   pwsh -File tools/build-phonemes.ps1
# or:
#   powershell -ExecutionPolicy Bypass -File tools/build-phonemes.ps1

$ErrorActionPreference = 'Stop'
$ProgressPreference   = 'SilentlyContinue'

$cmuUrl  = 'https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict'
$repoRoot = Split-Path -Parent $PSScriptRoot
$outFile = Join-Path $repoRoot 'phonemes.json'

Write-Host "Fetching CMU dict from $cmuUrl ..."
$raw = (Invoke-WebRequest -Uri $cmuUrl -UseBasicParsing).Content

$dict = [ordered]@{}
$lines = $raw -split "`n"
$kept = 0
$skipped = 0

foreach ($line in $lines) {
    $line = $line.Trim()
    if (-not $line -or $line.StartsWith(';;;')) { continue }

    # Drop in-line comments after '#'
    $hash = $line.IndexOf('#')
    if ($hash -ge 0) { $line = $line.Substring(0, $hash).Trim() }
    if (-not $line) { continue }

    $parts = $line -split '\s+'
    if ($parts.Count -lt 2) { continue }

    $word = $parts[0].ToLower()

    # Skip alternate pronunciations (we only keep the primary)
    if ($word -match '\(\d+\)$') { $skipped++; continue }

    # Skip non-alphabetic words (e.g. "'tis", "a.")
    if ($word -notmatch '^[a-z]+$') { $skipped++; continue }

    $phonemes = $parts[1..($parts.Count - 1)] | ForEach-Object {
        ($_ -replace '\d+$', '').ToUpper()
    }

    if ($phonemes.Count -lt 1 -or $phonemes.Count -gt 4) { $skipped++; continue }

    $dict[$word] = $phonemes
    $kept++
}

Write-Host "Kept $kept entries; skipped $skipped."

# NOTE: PowerShell's ordered dictionary exposes member access (.Count, .Keys, etc.)
# as KEY LOOKUPS first. Since cmudict contains the words "count" and "keys", $dict.Count
# and $dict.Keys silently return the wrong thing. Always go through .PSBase here.
$keys = @($dict.PSBase.Keys)

# Emit compact JSON manually so each word is one short line — small and grep-friendly.
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine('{')
for ($i = 0; $i -lt $keys.Count; $i++) {
    $k = $keys[$i]
    $phs = $dict[$k] | ForEach-Object { '"' + $_ + '"' }
    $line = '  "' + $k + '": [' + ($phs -join ',') + ']'
    if ($i -lt $keys.Count - 1) { $line += ',' }
    [void]$sb.AppendLine($line)
}
[void]$sb.AppendLine('}')

[System.IO.File]::WriteAllText($outFile, $sb.ToString(), [System.Text.UTF8Encoding]::new($false))
$size = (Get-Item $outFile).Length
Write-Host ("Wrote {0} ({1:N0} bytes, {2:N1} KB)" -f $outFile, $size, ($size / 1KB))
