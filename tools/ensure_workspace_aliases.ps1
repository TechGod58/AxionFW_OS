param(
  [string]$RepoRoot = "",
  [switch]$CreateLegacyAliases
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$targets = @(
  @{ Link = 'C:\AxionOS'; Target = (Join-Path $RepoRoot 'AxionOS') },
  @{ Link = 'C:\AxionFW'; Target = (Join-Path $RepoRoot 'AxionFW') }
)

foreach ($entry in $targets) {
  if (-not (Test-Path $entry.Target)) {
    throw "Missing workspace target: $($entry.Target)"
  }
}

if ($CreateLegacyAliases) {
  foreach ($entry in $targets) {
    if (Test-Path $entry.Link) {
      Write-Host "[alias] keeping existing $($entry.Link)"
      continue
    }

    try {
      New-Item -ItemType Junction -Path $entry.Link -Target $entry.Target -ErrorAction Stop | Out-Null
      Write-Host "[alias] created $($entry.Link) -> $($entry.Target)"
    } catch {
      Write-Warning ("[alias] unable to create {0} -> {1}: {2}" -f $entry.Link, $entry.Target, $_.Exception.Message)
      Write-Host ("[alias] continuing with direct workspace paths for $($entry.Target)")
    }
  }
} else {
  Write-Host "[alias] legacy junction creation skipped (use -CreateLegacyAliases to enable)"
}

[Environment]::SetEnvironmentVariable('AXIONOS_ROOT', $targets[0].Target, 'Process')
[Environment]::SetEnvironmentVariable('AXIONFW_BASE', (Join-Path $targets[1].Target 'Base'), 'Process')
