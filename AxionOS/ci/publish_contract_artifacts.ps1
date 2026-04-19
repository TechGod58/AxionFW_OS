$ErrorActionPreference='Continue'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out=Join-Path $repo 'out\contracts'
$dest=Join-Path $out 'published_artifacts'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item (Join-Path $out 'registry_validation.json') $dest -Force -ErrorAction SilentlyContinue
$latest=Get-ChildItem $out -Filter 'contract_report_*.json' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if($latest){ Copy-Item $latest.FullName $dest -Force }
Write-Output "PUBLISH_OK registry_validation=$(Test-Path (Join-Path $dest 'registry_validation.json')) contract_report=$($latest.Name)"
