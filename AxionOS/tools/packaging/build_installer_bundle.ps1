param(
  [string]$Version = '0.1.0',
  [string]$ReleaseRoot = '',
  [string]$InstallerOut = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')

$osRoot = Get-AxionOsRoot -ScriptPath $PSCommandPath
Enable-AxionLocalRuntimePath -OsRoot $osRoot
$pythonInvocation = Get-AxionPythonInvocation -OsRoot $osRoot
if([string]::IsNullOrWhiteSpace($ReleaseRoot)){
  $ReleaseRoot = Join-Path $osRoot 'out\release'
}
if([string]::IsNullOrWhiteSpace($InstallerOut)){
  $InstallerOut = Join-Path $osRoot 'out\installer'
}

$releaseDir = Join-Path $ReleaseRoot $Version
if(-not (Test-Path $releaseDir)){ throw "Release dir missing: $releaseDir" }

$complianceScript = Join-Path $PSScriptRoot 'validate_third_party_bundle_compliance.py'
& $pythonInvocation.file_path @($pythonInvocation.args_prefix + @($complianceScript, '--os-root', $osRoot))
if($LASTEXITCODE -ne 0){
  throw "Third-party bundle compliance validation failed."
}
$complianceLatestJson = Join-Path $osRoot 'out\packaging\third_party_bundle_compliance_latest.json'
$complianceLatestMd = Join-Path $osRoot 'out\packaging\third_party_bundle_compliance_latest.md'

$staging = Join-Path $InstallerOut ("AxionOS-Installer-{0}" -f $Version)
if(Test-Path $staging){ Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null

# Copy full release payload
Copy-Item "$releaseDir\*" $staging -Recurse -Force

# Add installer metadata
$meta = [ordered]@{
  product = 'AxionOS'
  edition = 'Qh8#'
  version = $Version
  created_utc = (Get-Date).ToUniversalTime().ToString('o')
  notes = 'Installer staging payload. Use UltraISO/Etcher/YUMI to create boot/install media as needed.'
  compliance = @{
    third_party_bundle_report = 'compliance/third_party_bundle_compliance_latest.json'
  }
}
$meta | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $staging 'installer_meta.json') -Encoding UTF8
New-Item -ItemType Directory -Force -Path (Join-Path $staging 'compliance') | Out-Null
if(Test-Path $complianceLatestJson){ Copy-Item $complianceLatestJson (Join-Path $staging 'compliance\third_party_bundle_compliance_latest.json') -Force }
if(Test-Path $complianceLatestMd){ Copy-Item $complianceLatestMd (Join-Path $staging 'compliance\third_party_bundle_compliance_latest.md') -Force }

# Zip payload for distribution
$zip = Join-Path $InstallerOut ("AxionOS-Installer-{0}.zip" -f $Version)
if(Test-Path $zip){ Remove-Item $zip -Force }
Compress-Archive -Path "$staging\*" -DestinationPath $zip -Force

Write-Output "INSTALLER_STAGING:$staging"
Write-Output "INSTALLER_ZIP:$zip"
