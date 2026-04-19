param(
  [string]$Version = '0.1.0',
  [string]$ReleaseRoot = '',
  [string]$FwGateSummary = '',
  [string]$OutDir = '',
  [int]$TimeoutSec = 90,
  [switch]$DryRun,
  [switch]$StrictProbes,
  [string]$BootImage = '',
  [string]$NetModel = 'virtio-net-pci',
  [switch]$NetworkImplemented,
  [switch]$DiskImplemented,
  [switch]$NetworkKernelImplemented,
  [switch]$DiskKernelImplemented
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
  $OutDir = Join-Path $osRoot 'out\smoke'
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$releaseDir = Join-Path $ReleaseRoot $Version
if(-not (Test-Path $releaseDir)){ throw "Release dir missing: $releaseDir" }

$qemu = Get-Command qemu-system-x86_64 -ErrorAction SilentlyContinue
if(-not $qemu){
  $qemuCand = @('C:\Program Files\qemu\qemu-system-x86_64.exe','C:\Program Files\qemu\qemu-system-x86_64w.exe') | Where-Object { Test-Path $_ } | Select-Object -First 1
  if($qemuCand){ $qemu = [pscustomobject]@{ Source = $qemuCand } }
}
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
if(-not $ovmfCode){ throw 'No OVMF code artifact found for smoke run.' }
if(-not (Test-Path $ovmfCode)){ throw "Missing OVMF code path: $ovmfCode" }

if(-not $BootImage){
  $candImgs = Get-ChildItem $releaseDir -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in '.img','.qcow2','.vhdx','.raw','.iso' }
  if($candImgs){ $BootImage = $candImgs[0].FullName }
}

$serialLog = Join-Path $OutDir ("serial_{0}.log" -f $Version)
$summaryPath = Join-Path $OutDir ("golden_vm_smoke_{0}.json" -f $Version)
if(Test-Path $serialLog){ Remove-Item $serialLog -Force }

$cmd = @(
  $qemuExe,
  '-machine','q35,accel=tcg',
  '-m','2048',
  '-smp','2',
  '-drive',("if=pflash,format=raw,readonly=on,file={0}" -f $ovmfCode),
  '-serial',("file:{0}" -f $serialLog),
  '-nographic',
  '-no-reboot',
  '-netdev','user,id=n1',
  '-device',("{0},netdev=n1" -f $NetModel)
)
if($ovmfVars -and (Test-Path $ovmfVars)){ $cmd += @('-drive',("if=pflash,format=raw,file={0}" -f $ovmfVars)) }
$diskAttached = $false
if($BootImage -and (Test-Path $BootImage)){
  $cmd += @('-drive',("id=drv0,file={0},if=none,format=raw" -f $BootImage),'-device','virtio-blk-pci,drive=drv0')
  $diskAttached = $true
}
$commandLine = ($cmd | ForEach-Object { if($_ -match '\s'){ '"' + $_ + '"' } else { $_ } }) -join ' '

$checks = [ordered]@{ boot='PENDING'; init='PENDING'; networking='PENDING'; disk='PENDING'; shutdown='PENDING' }
$probe = [ordered]@{
  boot_pattern='(?i)uefi|ovmf|boot|shell|bdsdxe'
  init_pattern='(?i)init|kernel|systemd|boot manager|shell|bdsdxe'
  network_pattern='(?i)NET_MAC=|NET_FULL_OK|NET_PCI_FOUND|KNET_LINK_OK|KNET_DEV_INIT_OK|net|dhcp|eth|e1000|rtl8139|virtio-net|ip4|ip6|link'
  disk_pattern='(?i)DISK_SECTOR0_READ_OK|DISK_PCI_FOUND|KDISK_LBA0_OK|disk|blk|nvme|sata|ahci|virtio-blk|fs0:|blkio|bootable'
  boot_hits=0
  init_hits=0
  network_hits=0
  disk_hits=0
  matched_lines=@{boot=@();init=@();network=@();disk=@()}
}

if($DryRun -or -not $qemu){
  $checks.boot = if($qemu){'SKIPPED_DRYRUN'} else {'BLOCKED_NO_QEMU'}
  $checks.init='SKIPPED'
  $checks.networking='SKIPPED'
  $checks.disk='SKIPPED'
  $checks.shutdown='SKIPPED'
  $summary=[ordered]@{
    ts_utc=(Get-Date).ToUniversalTime().ToString('o')
    version=$Version
    mode=if($DryRun){'DRY_RUN'}else{'NO_QEMU'}
    strict_probes=[bool]$StrictProbes
    qemu_detected=[bool]$qemu
    timeout_sec=$TimeoutSec
    command_line=$commandLine
    serial_log=$serialLog
    boot_image=$BootImage
    disk_attached=$diskAttached
    checks=$checks
    probe=$probe
    capability_tier=[ordered]@{
      network_implemented=[bool]$NetworkImplemented
      disk_implemented=[bool]$DiskImplemented
      network_kernel_implemented=[bool]$NetworkKernelImplemented
      disk_kernel_implemented=[bool]$DiskKernelImplemented
    }
    overall=if($qemu -and $DryRun){'SKIPPED'}else{'BLOCKED'}
  }
  $summary | ConvertTo-Json -Depth 12 | Set-Content -Path $summaryPath -Encoding UTF8
  Write-Output "SMOKE_SUMMARY:$summaryPath"
  Write-Output "SMOKE_OVERALL:$($summary.overall)"
  exit 0
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $qemu.Source
$psi.Arguments = (($cmd[1..($cmd.Count-1)] -join ' '))
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$p = [System.Diagnostics.Process]::Start($psi)
$start=Get-Date
while(-not $p.HasExited -and ((Get-Date)-$start).TotalSeconds -lt $TimeoutSec){ Start-Sleep -Milliseconds 500 }
if(-not $p.HasExited){ try { $p.Kill() } catch {} }

$serialText=''
if(Test-Path $serialLog){ $serialText = Get-Content $serialLog -Raw -ErrorAction SilentlyContinue }
$lines=@()
if($serialText){ $lines = ($serialText -split "`r?`n") }
$firstLines = @($lines | Select-Object -First 50)
$lastLines = @($lines | Select-Object -Last 50)

foreach($ln in $lines){
  if($ln -match $probe.boot_pattern -and $probe.matched_lines.boot.Count -lt 20){ $probe.matched_lines.boot += $ln }
  if($ln -match $probe.init_pattern -and $probe.matched_lines.init.Count -lt 20){ $probe.matched_lines.init += $ln }
  if($ln -match $probe.network_pattern -and $probe.matched_lines.network.Count -lt 20){ $probe.matched_lines.network += $ln }
  if($ln -match $probe.disk_pattern -and $probe.matched_lines.disk.Count -lt 20){ $probe.matched_lines.disk += $ln }
}
$probe.boot_hits=$probe.matched_lines.boot.Count
$probe.init_hits=$probe.matched_lines.init.Count
$probe.network_hits=$probe.matched_lines.network.Count
$probe.disk_hits=$probe.matched_lines.disk.Count

$checks.boot = if($serialText.Length -gt 0 -and $probe.boot_hits -gt 0){'PASS'} else {'FAIL'}
$checks.init = if($probe.init_hits -gt 0){ 'PASS' } else { 'FAIL' }

$hasNetUefi = ($serialText -match '(?i)NET_FULL_OK|NET_MAC=')
$hasNetKernel = ($serialText -match '(?i)KNET_LINK_OK|KNET_DEV_INIT_OK')
$hasDiskUefi = ($serialText -match '(?i)DISK_SECTOR0_READ_OK')
$hasDiskKernelMarker = ($serialText -match '(?m)^KDISK_LBA0_OK\s*$')

$notifyMatch = [System.Text.RegularExpressions.Regex]::Match($serialText,'(?m)^NOTIFY_WRITE=mmio16 val=0\s*$')
$notifyIndex = if($notifyMatch.Success){ $notifyMatch.Index } else { -1 }

$statusMatches = [System.Text.RegularExpressions.Regex]::Matches($serialText,'(?m)^STATUS_BYTE=0x00\s*$')
$hasDiskStatusOk = $false
if($statusMatches.Count -gt 0){
  if($notifyIndex -ge 0){ $hasDiskStatusOk = @($statusMatches | Where-Object { $_.Index -gt $notifyIndex }).Count -gt 0 }
  else { $hasDiskStatusOk = $true }
}

$usedMatches = [System.Text.RegularExpressions.Regex]::Matches($serialText,'(?m)^USED_IDX=([0-9A-Fa-f]{4})\s*$')
$usedBeforeNotify = @($usedMatches | Where-Object { $notifyIndex -ge 0 -and $_.Index -lt $notifyIndex } | ForEach-Object { [Convert]::ToInt32($_.Groups[1].Value,16) })
$usedAfterNotify = @($usedMatches | Where-Object { if($notifyIndex -ge 0){ $_.Index -gt $notifyIndex } else { $true } } | ForEach-Object { [Convert]::ToInt32($_.Groups[1].Value,16) })
$usedIdxStart = if($usedBeforeNotify.Count -gt 0){ $usedBeforeNotify[0] } else { 0 }
$usedIdxMaxAfter = if($usedAfterNotify.Count -gt 0){ ($usedAfterNotify | Measure-Object -Maximum).Maximum } else { $null }
$hasDiskUsedAdvance = ($null -ne $usedIdxMaxAfter) -and ($usedIdxMaxAfter -ge ($usedIdxStart + 1))

$hasDiskKernel = $hasDiskKernelMarker -and $hasDiskStatusOk -and $hasDiskUsedAdvance
$probe.disk_kernel_sanity = [ordered]@{
  marker_ok=[bool]$hasDiskKernelMarker
  status_ok=[bool]$hasDiskStatusOk
  used_idx_start=$usedIdxStart
  used_idx_max_after_notify=$usedIdxMaxAfter
  used_idx_advance=[bool]$hasDiskUsedAdvance
  notify_seen=[bool]($notifyIndex -ge 0)
}

if($NetworkKernelImplemented){
  $checks.networking = if($hasNetKernel){ 'PASS_FULL_KERNEL' } else { 'FAIL' }
} elseif($NetworkImplemented){
  $checks.networking = if($hasNetUefi){ 'PASS_FULL_UEFI' } elseif($probe.network_hits -gt 0){ 'PASS_DETECTED' } else { 'FAIL' }
} else {
  $checks.networking = if($probe.network_hits -gt 0){ 'PASS_DETECTED' } else { 'FAIL_NOT_IMPLEMENTED' }
}

if(-not $diskAttached){
  $checks.disk='FAIL_NO_DISK_ATTACHED'
} elseif($DiskKernelImplemented){
  $checks.disk = if($hasDiskKernel){ 'PASS_FULL_KERNEL' } else { 'FAIL' }
} elseif($DiskImplemented){
  $checks.disk = if($hasDiskUefi){ 'PASS_FULL_UEFI' } elseif($probe.disk_hits -gt 0){ 'PASS_DETECTED' } else { 'FAIL' }
} else {
  $checks.disk = if($probe.disk_hits -gt 0){ 'PASS_DETECTED' } else { 'FAIL_NOT_IMPLEMENTED' }
}

$checks.shutdown = if($p.HasExited){ 'PASS' } else { 'FAIL' }

$criticalPass = ($checks.boot -eq 'PASS') -and ($checks.init -eq 'PASS') -and ($checks.shutdown -eq 'PASS')
$netPass = ($checks.networking -eq 'PASS_FULL_UEFI') -or ($checks.networking -eq 'PASS_FULL_KERNEL') -or ($checks.networking -eq 'PASS_DETECTED') -or ($checks.networking -eq 'FAIL_NOT_IMPLEMENTED')
$diskPass = ($checks.disk -eq 'PASS_FULL_UEFI') -or ($checks.disk -eq 'PASS_FULL_KERNEL') -or ($checks.disk -eq 'PASS_DETECTED') -or ($checks.disk -eq 'FAIL_NOT_IMPLEMENTED')
$fullPass = $criticalPass -and $netPass -and $diskPass
$overall = if($StrictProbes){ if($fullPass){'PASS'} else {'FAIL'} } else { if($criticalPass){'PASS'} else {'FAIL'} }

$summary=[ordered]@{
  ts_utc=(Get-Date).ToUniversalTime().ToString('o')
  version=$Version
  mode='LIVE'
  strict_probes=[bool]$StrictProbes
  qemu_detected=$true
  timeout_sec=$TimeoutSec
  capability_tier=[ordered]@{
    network_implemented=[bool]$NetworkImplemented
    disk_implemented=[bool]$DiskImplemented
    network_kernel_implemented=[bool]$NetworkKernelImplemented
    disk_kernel_implemented=[bool]$DiskKernelImplemented
  }
  command_line=$commandLine
  serial_log=$serialLog
  boot_image=$BootImage
  disk_attached=$diskAttached
  checks=$checks
  probe=$probe
  overall=$overall
  overall_critical=if($criticalPass){'PASS'}else{'FAIL'}
  overall_full=if($fullPass){'PASS'}else{'FAIL'}
  first_50_lines=$firstLines
  last_50_lines=$lastLines
  first_2000_chars=($serialText.Substring(0,[Math]::Min(2000,$serialText.Length)))
}
$summary | ConvertTo-Json -Depth 12 | Set-Content -Path $summaryPath -Encoding UTF8
Write-Output "SMOKE_SUMMARY:$summaryPath"
Write-Output "SMOKE_OVERALL:$overall"
Write-Output "SMOKE_CRITICAL:$($summary.overall_critical)"
Write-Output "SMOKE_FULL:$($summary.overall_full)"
