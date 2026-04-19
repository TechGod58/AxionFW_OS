param(
  [switch]$Rotate,
  [string]$SecretRoot = ''
)

$ErrorActionPreference = 'Stop'

function New-AxionRandomKeyMaterial {
  param(
    [int]$ByteLength = 48
  )

  $bytes = New-Object byte[] $ByteLength
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try {
    $rng.GetBytes($bytes)
  } finally {
    $rng.Dispose()
  }
  return [Convert]::ToBase64String($bytes)
}

function Protect-AxionSecretFileAcl {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath
  )

  $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  $acl = New-Object System.Security.AccessControl.FileSecurity
  $acl.SetOwner([System.Security.Principal.NTAccount]::new($currentUser))
  $acl.SetAccessRuleProtection($true, $false)
  $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new($currentUser, 'FullControl', 'Allow'))
  $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new('SYSTEM', 'FullControl', 'Allow'))
  Set-Acl -LiteralPath $FilePath -AclObject $acl
}

function Ensure-AxionSecretFile {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [switch]$Rotate
  )

  $existing = ''
  if((Test-Path -LiteralPath $FilePath) -and (-not $Rotate)){
    $existing = (Get-Content -LiteralPath $FilePath -Raw).Trim()
  }

  if([string]::IsNullOrWhiteSpace($existing)){
    $existing = New-AxionRandomKeyMaterial
    $dir = Split-Path -Parent $FilePath
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    [System.IO.File]::WriteAllText($FilePath, $existing)
  }

  Protect-AxionSecretFileAcl -FilePath $FilePath
  return $existing.Length
}

if([string]::IsNullOrWhiteSpace($SecretRoot)){
  $SecretRoot = Join-Path $env:LOCALAPPDATA 'AxionOS\secrets\release_signing'
}
New-Item -ItemType Directory -Path $SecretRoot -Force | Out-Null

$kmsPath = Join-Path $SecretRoot 'AXION_KMS_RELEASE_SIGNING_KEY_01.key'
$hsmPath = Join-Path $SecretRoot 'AXION_HSM_RELEASE_SIGNING_KEY_02.key'
$kmsLen = Ensure-AxionSecretFile -FilePath $kmsPath -Rotate:$Rotate
$hsmLen = Ensure-AxionSecretFile -FilePath $hsmPath -Rotate:$Rotate

[Environment]::SetEnvironmentVariable('AXION_KMS_RELEASE_SIGNING_KEY_01_FILE', $kmsPath, 'User')
[Environment]::SetEnvironmentVariable('AXION_HSM_RELEASE_SIGNING_KEY_02_FILE', $hsmPath, 'User')
[Environment]::SetEnvironmentVariable('AXION_KMS_RELEASE_SIGNING_KEY_01_FILE', $kmsPath, 'Process')
[Environment]::SetEnvironmentVariable('AXION_HSM_RELEASE_SIGNING_KEY_02_FILE', $hsmPath, 'Process')
Set-Item -Path 'Env:AXION_KMS_RELEASE_SIGNING_KEY_01_FILE' -Value $kmsPath
Set-Item -Path 'Env:AXION_HSM_RELEASE_SIGNING_KEY_02_FILE' -Value $hsmPath

$summary = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString('o')
  rotated = [bool]$Rotate
  secret_root = $SecretRoot
  configured_file_env = [ordered]@{
    AXION_KMS_RELEASE_SIGNING_KEY_01_FILE = $kmsPath
    AXION_HSM_RELEASE_SIGNING_KEY_02_FILE = $hsmPath
  }
  key_lengths = [ordered]@{
    AXION_KMS_RELEASE_SIGNING_KEY_01 = $kmsLen
    AXION_HSM_RELEASE_SIGNING_KEY_02 = $hsmLen
  }
}

$summary | ConvertTo-Json -Depth 6
