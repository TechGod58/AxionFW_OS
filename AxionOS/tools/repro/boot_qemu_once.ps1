param(
  [string]$Version = '0.1.0',
  [string]$ReleaseRoot = '',
  [string]$FwGateSummary = '',
  [string]$OutDir = '',
  [switch]$DryRun,
  [int]$TimeoutSec = 30
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')

$osRoot = Get-AxionOsRoot -ScriptPath $PSCommandPath
if([string]::IsNullOrWhiteSpace($ReleaseRoot)){
  $ReleaseRoot = Join-Path $osRoot 'out\release'
}
if([string]::IsNullOrWhiteSpace($FwGateSummary)){
  $FwGateSummary = Join-Path $osRoot 'out\fw_gate\summary.json'
}
if([string]::IsNullOrWhiteSpace($OutDir)){
  $OutDir = Join-Path $osRoot 'out\repro'
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$releaseDir = Join-Path $ReleaseRoot $Version
if(-not (Test-Path $releaseDir)){ throw "Release dir missing: $releaseDir" }

$qemu = Get-Command qemu-system-x86_64 -ErrorAction SilentlyContinue
$qemuExe = if($qemu){ $qemu.Source } else { 'qemu-system-x86_64' }

$ovmfCode = $null
$ovmfVars = $null
if(Test-Path $FwGateSummary){
  $fw = Get-Content $FwGateSummary -Raw | ConvertFrom-Json
  $buildLog = $fw.artifacts.build_log
  if($buildLog -and (Test-Path $buildLog)){
    $meta = Get-Content $buildLog -Raw | ConvertFrom-Json
    $cands = @($meta.ovmf_candidates)
    foreach($c in $cands){
      if(-not $ovmfCode -and $c -match 'CODE'){ $ovmfCode = $c }
      if(-not $ovmfVars -and $c -match 'VARS'){ $ovmfVars = $c }
    }
    if(-not $ovmfCode -and $cands.Count -gt 0){ $ovmfCode = $cands[0] }
    if(-not $ovmfVars -and $cands.Count -gt 1){ $ovmfVars = $cands[1] }
  }
}
if(-not $ovmfCode){ throw "No OVMF code artifact found (check $FwGateSummary)" }
if(-not (Test-Path $ovmfCode)){ throw "Missing OVMF code path: $ovmfCode" }

$serialLog = Join-Path $OutDir ("qemu_serial_{0}.log" -f $Version)
$cmd = @(
  $qemuExe,
  '-machine','q35,accel=tcg',
  '-m','2048',
  '-smp','2',
  '-drive',("if=pflash,format=raw,readonly=on,file={0}" -f $ovmfCode),
  '-serial',("file:{0}" -f $serialLog),
  '-display','none',
  '-no-reboot'
)
if($ovmfVars -and (Test-Path $ovmfVars)){
  $cmd += @('-drive',("if=pflash,format=raw,file={0}" -f $ovmfVars))
}

$commandLine = ($cmd | ForEach-Object { if($_ -match '\s'){ '"' + $_ + '"' } else { $_ } }) -join ' '
$cmdPath = Join-Path $OutDir ("qemu_command_{0}.txt" -f $Version)
$metaPath = Join-Path $OutDir ("qemu_boot_meta_{0}.json" -f $Version)

$meta = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString('o')
  version = $Version
  release_dir = $releaseDir
  ovmf_code = $ovmfCode
  ovmf_vars = $ovmfVars
  serial_log = $serialLog
  qemu_detected = [bool]$qemu
  command_line = $commandLine
  dry_run = [bool]$DryRun
  timeout_sec = $TimeoutSec
}
$meta | ConvertTo-Json -Depth 6 | Set-Content -Path $metaPath -Encoding UTF8
$commandLine | Set-Content -Path $cmdPath -Encoding UTF8

if($DryRun){
  Write-Output "QEMU_CMD_SAVED:$cmdPath"
  Write-Output "QEMU_META:$metaPath"
  Write-Output "QEMU_DRY_RUN:true"
  exit 0
}

if(-not $qemu){ throw 'qemu-system-x86_64 not found on PATH (dry-run succeeded; actual boot unavailable)' }

$argList = ($cmd[1..($cmd.Count-1)] -join ' ')
$p = Start-Process -FilePath $qemu.Source -ArgumentList $argList -PassThru -WindowStyle Hidden
$start = Get-Date
while(-not $p.HasExited -and ((Get-Date)-$start).TotalSeconds -lt $TimeoutSec){ Start-Sleep -Milliseconds 500 }
if(-not $p.HasExited){ try { $p.Kill() } catch {} }

$exit = if($p.HasExited){$p.ExitCode}else{124}
Write-Output "QEMU_EXIT:$exit"
Write-Output "QEMU_CMD_SAVED:$cmdPath"
Write-Output "QEMU_META:$metaPath"
exit 0
