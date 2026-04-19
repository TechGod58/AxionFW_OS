param(
  [string]$Distro = 'Ubuntu',
  [int]$TimeoutSec = 45,
  [string]$OutDir = '',
  [switch]$SkipClean,
  [switch]$SkipBuild,
  [switch]$NoBoot
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')

function Convert-ToWslPath {
  param(
    [Parameter(Mandatory = $true)][string]$WindowsPath
  )

  $resolved = (Resolve-Path -LiteralPath $WindowsPath).Path
  if($resolved -match '^([A-Za-z]):\\(.*)$'){
    $drive = $matches[1].ToLowerInvariant()
    $rest = $matches[2] -replace '\\','/'
    return "/mnt/$drive/$rest"
  }

  throw "Unable to map Windows path to WSL path: $resolved"
}

function Normalize-WslTextLine {
  param([string]$Line)
  if($null -eq $Line){ return '' }
  return ($Line -replace "`0",'').Trim()
}

$osRoot = Get-AxionOsRoot -ScriptPath $PSCommandPath
if([string]::IsNullOrWhiteSpace($OutDir)){
  $OutDir = Join-Path $osRoot 'out\repro'
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$logPath = Join-Path $OutDir ("verify_kernel_wsl_{0}.log" -f $stamp)
$summaryPath = Join-Path $OutDir ("verify_kernel_wsl_{0}.json" -f $stamp)
$osRootWsl = Convert-ToWslPath -WindowsPath $osRoot

if(-not (Get-Command wsl -ErrorAction SilentlyContinue)){
  throw 'WSL is not available on PATH. Install/enable WSL and retry.'
}

$distroListRaw = & wsl --list --quiet 2>$null
$distroList = @($distroListRaw | ForEach-Object { Normalize-WslTextLine -Line $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if($distroList.Count -eq 0){
  throw 'No WSL distributions found. Install Ubuntu (or another distro) and retry.'
}
if($distroList -notcontains $Distro){
  throw ("Requested WSL distro '{0}' not found. Available: {1}" -f $Distro, ($distroList -join ', '))
}

$doClean = if($SkipClean){0}else{1}
$doBuild = if($SkipBuild){0}else{1}
$doBoot = if($NoBoot){0}else{1}
$effectiveTimeout = if($TimeoutSec -lt 5){5}else{$TimeoutSec}

$bashTemplate = @'
set -euo pipefail
cd '__OS_ROOT_WSL__'

missing=()
for c in make gcc ld objcopy qemu-system-x86_64 mcopy mmd mformat sgdisk timeout cp; do
  command -v "$c" >/dev/null 2>&1 || missing+=("$c")
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "MISSING_TOOLS:${missing[*]}"
  exit 42
fi
if [ ! -f /usr/lib/elf_x86_64_efi.lds ] || [ ! -f /usr/lib/crt0-efi-x86_64.o ]; then
  echo "MISSING_GNU_EFI"
  exit 43
fi

if [ __DOBUILD__ -eq 1 ]; then
  if [ __DOCLEAN__ -eq 1 ]; then
    make clean
  fi
  make all
fi

if [ __DOBOOT__ -eq 1 ]; then
  FW_CODE=$(ls /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE*.fd /usr/share/ovmf/OVMF_CODE*.fd 2>/dev/null | head -n 1 || true)
  FW_VARS_SRC=$(ls /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS*.fd /usr/share/ovmf/OVMF_VARS*.fd 2>/dev/null | head -n 1 || true)
  if [ -z "$FW_CODE" ] || [ -z "$FW_VARS_SRC" ]; then
    echo "MISSING_OVMF:$FW_CODE:$FW_VARS_SRC"
    exit 44
  fi

  mkdir -p build
  FW_VARS_WORK="build/OVMF_VARS_4M.verify.fd"
  cp -f "$FW_VARS_SRC" "$FW_VARS_WORK"

  set +e
  timeout '__TIMEOUT__s' make run FW_CODE="$FW_CODE" FW_VARS="$FW_VARS_WORK"
  RUN_EXIT=$?
  set -e
  echo "VERIFY_RUN_EXIT:$RUN_EXIT"
fi
'@

$bash = $bashTemplate.Replace('__OS_ROOT_WSL__', $osRootWsl)
$bash = $bash.Replace('__DOBUILD__', "$doBuild")
$bash = $bash.Replace('__DOCLEAN__', "$doClean")
$bash = $bash.Replace('__DOBOOT__', "$doBoot")
$bash = $bash.Replace('__TIMEOUT__', "$effectiveTimeout")

$runnerShWin = Join-Path $OutDir ("verify_kernel_wsl_{0}.sh" -f $stamp)
[System.IO.File]::WriteAllText($runnerShWin, ($bash -replace "`r`n","`n"))
$runnerShWsl = Convert-ToWslPath -WindowsPath $runnerShWin

$stdoutTmp = Join-Path $OutDir ("verify_kernel_wsl_{0}.stdout.tmp" -f $stamp)
$stderrTmp = Join-Path $OutDir ("verify_kernel_wsl_{0}.stderr.tmp" -f $stamp)

$proc = Start-Process -FilePath 'wsl.exe' `
  -ArgumentList @('-d', $Distro, '-e', 'bash', $runnerShWsl) `
  -Wait -PassThru -NoNewWindow `
  -RedirectStandardOutput $stdoutTmp `
  -RedirectStandardError $stderrTmp

$wslExit = $proc.ExitCode
$stdoutLines = if(Test-Path $stdoutTmp){ Get-Content -Path $stdoutTmp -ErrorAction SilentlyContinue } else { @() }
$stderrLines = if(Test-Path $stderrTmp){ Get-Content -Path $stderrTmp -ErrorAction SilentlyContinue } else { @() }
$lines = @()
if($stdoutLines){ $lines += $stdoutLines }
if($stderrLines){
  if($lines.Count -gt 0){ $lines += '--- STDERR ---' }
  $lines += $stderrLines
}
$text = $lines -join "`n"
$lines | Set-Content -Path $logPath -Encoding UTF8

if(Test-Path $stdoutTmp){ Remove-Item -LiteralPath $stdoutTmp -Force -ErrorAction SilentlyContinue }
if(Test-Path $stderrTmp){ Remove-Item -LiteralPath $stderrTmp -Force -ErrorAction SilentlyContinue }
if(Test-Path $runnerShWin){ Remove-Item -LiteralPath $runnerShWin -Force -ErrorAction SilentlyContinue }

$runExit = $null
$m = [regex]::Match($text, 'VERIFY_RUN_EXIT:(\d+)')
if($m.Success){ $runExit = [int]$m.Groups[1].Value }

$hasKernelMain = $text -match 'KERNEL_MAIN_START'
$hasDiskOk = $text -match 'KDISK_LBA0_OK'
$hasMissingTools = $text -match 'MISSING_TOOLS:'
$hasMissingGnuEfi = $text -match 'MISSING_GNU_EFI'
$hasMissingOvmf = $text -match 'MISSING_OVMF:'

$bootVerified = if($NoBoot){ $true } else { $hasKernelMain -and $hasDiskOk }
$ok = ($wslExit -eq 0) -and $bootVerified -and (-not $hasMissingTools) -and (-not $hasMissingGnuEfi) -and (-not $hasMissingOvmf)

$summary = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString('o')
  os_root = $osRoot
  distro = $Distro
  out_dir = $OutDir
  log_path = $logPath
  options = [ordered]@{
    timeout_sec = $effectiveTimeout
    skip_clean = [bool]$SkipClean
    skip_build = [bool]$SkipBuild
    no_boot = [bool]$NoBoot
  }
  wsl_exit_code = $wslExit
  run_exit_code = $runExit
  checks = [ordered]@{
    kernel_main_seen = $hasKernelMain
    disk_lba0_ok_seen = $hasDiskOk
    boot_verified = $bootVerified
    missing_tools = $hasMissingTools
    missing_gnu_efi = $hasMissingGnuEfi
    missing_ovmf = $hasMissingOvmf
  }
  ok = $ok
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8

Write-Output ("VERIFY_KERNEL_WSL_LOG:{0}" -f $logPath)
Write-Output ("VERIFY_KERNEL_WSL_SUMMARY:{0}" -f $summaryPath)
Write-Output ("VERIFY_KERNEL_WSL_RESULT:{0}" -f $(if($ok){'PASS'}else{'FAIL'}))

if(-not $ok){ exit 1 }
exit 0
