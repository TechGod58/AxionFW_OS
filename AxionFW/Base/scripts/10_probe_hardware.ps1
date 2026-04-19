param(
  [string]$OutputDir = "",
  [string]$MachineId = "",
  [switch]$TryElevatedCollector,
  [switch]$ElevatedCollector,
  [string]$ElevatedOutputPath = ""
)

$ErrorActionPreference = 'Stop'

$baseRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
  $OutputDir = Join-Path $baseRoot 'out\manifests'
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Test-IsAdministrator {
  try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  } catch {
    return $false
  }
}

function Read-Instances {
  param(
    [Parameter(Mandatory = $true)][string]$ClassName,
    [string[]]$Props
  )

  try {
    $raw = Get-CimInstance -ClassName $ClassName -ErrorAction Stop
    if ($Props -and $Props.Count -gt 0) {
      return $raw | Select-Object -Property $Props
    }
    return $raw
  }
  catch {
    return @()
  }
}

function ConvertTo-PnpRows {
  param(
    [object[]]$Rows,
    [string]$SourceName
  )

  $out = @()
  foreach ($row in @($Rows)) {
    $id = [string]$row.PNPDeviceID
    if ([string]::IsNullOrWhiteSpace($id)) { continue }
    $out += [pscustomobject]@{
      Name = [string]$row.Name
      PNPDeviceID = $id
      Service = [string]$row.Service
      ClassGuid = [string]$row.ClassGuid
      Source = $SourceName
    }
  }
  return $out
}

function Collect-PnpViaPnPUtil {
  $cmd = Get-Command pnputil.exe -ErrorAction SilentlyContinue
  if ($null -eq $cmd) { return @() }

  $all = @()
  foreach ($bus in @('PCI', 'ACPI', 'USB')) {
    try {
      $lines = & $cmd.Source /enum-devices /bus $bus /connected 2>$null
      $current = $null
      foreach ($line in @($lines)) {
        if ($line -match '^\s*Instance ID:\s*(.+)$') {
          if ($null -ne $current -and -not [string]::IsNullOrWhiteSpace([string]$current.PNPDeviceID)) {
            $all += [pscustomobject]$current
          }
          $current = [ordered]@{
            Name = ''
            PNPDeviceID = $matches[1].Trim()
            Service = ''
            ClassGuid = ''
            Source = 'pnputil'
          }
          continue
        }
        if ($null -eq $current) { continue }
        if ($line -match '^\s*Device Description:\s*(.+)$') {
          $current.Name = $matches[1].Trim()
          continue
        }
        if ($line -match '^\s*Service:\s*(.+)$') {
          $current.Service = $matches[1].Trim()
          continue
        }
        if ($line -match '^\s*Class GUID:\s*(.+)$') {
          $current.ClassGuid = $matches[1].Trim()
          continue
        }
      }
      if ($null -ne $current -and -not [string]::IsNullOrWhiteSpace([string]$current.PNPDeviceID)) {
        $all += [pscustomobject]$current
      }
    }
    catch {
      continue
    }
  }

  return $all
}

function Collect-PnpInventory {
  param(
    [switch]$TryElevated,
    [switch]$AllowRunAs
  )

  $collectorSource = 'win32_pnpentity'
  $runAsAttempted = $false
  $runAsSucceeded = $false
  $runAsError = $null
  $pnp = ConvertTo-PnpRows -Rows (Read-Instances -ClassName Win32_PnPEntity -Props @('Name', 'PNPDeviceID', 'Service', 'ClassGuid')) -SourceName 'win32_pnpentity'

  if (@($pnp).Count -eq 0 -and (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue)) {
    try {
      $raw = Get-PnpDevice -ErrorAction Stop | Select-Object `
        @{Name = 'Name'; Expression = { $_.FriendlyName }}, `
        @{Name = 'PNPDeviceID'; Expression = { $_.InstanceId }}, `
        @{Name = 'Service'; Expression = { $_.Service }}, `
        @{Name = 'ClassGuid'; Expression = { $_.ClassGuid }}
      $pnp = ConvertTo-PnpRows -Rows $raw -SourceName 'get_pnpdevice'
      if (@($pnp).Count -gt 0) { $collectorSource = 'get_pnpdevice' }
    }
    catch {
      $pnp = @()
    }
  }

  if (@($pnp).Count -eq 0) {
    $pnputilRows = Collect-PnpViaPnPUtil
    if (@($pnputilRows).Count -gt 0) {
      $pnp = ConvertTo-PnpRows -Rows $pnputilRows -SourceName 'pnputil'
      $collectorSource = 'pnputil'
    }
  }

  if (@($pnp).Count -eq 0 -and $TryElevated -and $AllowRunAs -and -not (Test-IsAdministrator)) {
    $runAsAttempted = $true
    $tmpOut = Join-Path ([System.IO.Path]::GetTempPath()) ("axionfw_pnp_elevated_{0}.json" -f ([Guid]::NewGuid().ToString('N')))
    try {
      $argList = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', $PSCommandPath,
        '-OutputDir', $OutputDir,
        '-MachineId', $MachineId,
        '-TryElevatedCollector',
        '-ElevatedCollector',
        '-ElevatedOutputPath', $tmpOut
      )
      $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList -Verb RunAs -Wait -PassThru
      if ($proc.ExitCode -eq 0 -and (Test-Path -LiteralPath $tmpOut)) {
        $raw = Get-Content -Path $tmpOut -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($null -ne $raw -and $raw.PSObject.Properties.Name -contains 'pnp') {
          $pnp = ConvertTo-PnpRows -Rows @($raw.pnp) -SourceName 'elevated'
          if (@($pnp).Count -gt 0) {
            $collectorSource = 'elevated'
            $runAsSucceeded = $true
          }
        }
      } else {
        $runAsError = "elevated collector exited with code $($proc.ExitCode)"
      }
    }
    catch {
      $runAsError = $_.Exception.Message
    }
    finally {
      if (Test-Path -LiteralPath $tmpOut) {
        Remove-Item -LiteralPath $tmpOut -Force -ErrorAction SilentlyContinue
      }
    }
  }

  return [pscustomobject]@{
    pnp = @($pnp)
    collector_source = $collectorSource
    runas_attempted = [bool]$runAsAttempted
    runas_succeeded = [bool]$runAsSucceeded
    runas_error = $runAsError
  }
}

$cs = Read-Instances -ClassName Win32_ComputerSystem -Props @('Manufacturer', 'Model', 'SystemFamily', 'TotalPhysicalMemory')
$bios = Read-Instances -ClassName Win32_BIOS -Props @('Manufacturer', 'SMBIOSBIOSVersion', 'ReleaseDate', 'SerialNumber')
$baseboard = Read-Instances -ClassName Win32_BaseBoard -Props @('Manufacturer', 'Product', 'Version', 'SerialNumber')
$cpu = Read-Instances -ClassName Win32_Processor -Props @('Name', 'Manufacturer', 'NumberOfCores', 'NumberOfLogicalProcessors', 'AddressWidth')
$mem = Read-Instances -ClassName Win32_PhysicalMemory -Props @('Manufacturer', 'PartNumber', 'Capacity', 'Speed')
$disk = Read-Instances -ClassName Win32_DiskDrive -Props @('Model', 'InterfaceType', 'MediaType', 'Size', 'PNPDeviceID')
$net = Read-Instances -ClassName Win32_NetworkAdapter -Props @('Name', 'Manufacturer', 'MACAddress', 'PNPDeviceID', 'NetEnabled')

$pnpMeta = Collect-PnpInventory -TryElevated:$TryElevatedCollector -AllowRunAs:(-not $ElevatedCollector)
$pnp = @($pnpMeta.pnp)

$pciDevices = @($pnp | Where-Object { $_.PNPDeviceID -like 'PCI\*' })
$acpiDevices = @($pnp | Where-Object { $_.PNPDeviceID -like 'ACPI\*' })
$usbDevices = @($pnp | Where-Object { $_.PNPDeviceID -like 'USB\*' })

if ([string]::IsNullOrWhiteSpace($MachineId)) {
  $serial = ($bios | Select-Object -First 1).SerialNumber
  if ([string]::IsNullOrWhiteSpace($serial)) {
    $serial = [Environment]::MachineName
  }
  $MachineId = (($serial -replace '[^A-Za-z0-9_-]', '_').Trim('_'))
  if ([string]::IsNullOrWhiteSpace($MachineId)) {
    $MachineId = 'unknown_machine'
  }
}

$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$outJson = Join-Path $OutputDir ("{0}_{1}.json" -f $MachineId, $timestamp)
$outSha = "$outJson.sha256"

$payload = [ordered]@{
  policy_id = 'AXION_FW_INVENTORY_V1'
  generated_utc = (Get-Date).ToUniversalTime().ToString('o')
  machine_id = $MachineId
  source = 'AxionFW/Base/scripts/10_probe_hardware.ps1'
  collector = [ordered]@{
    elevated_mode = [bool]$ElevatedCollector
    try_elevated_requested = [bool]$TryElevatedCollector
    is_admin = [bool](Test-IsAdministrator)
    pnp_collector_source = [string]$pnpMeta.collector_source
    runas_attempted = [bool]$pnpMeta.runas_attempted
    runas_succeeded = [bool]$pnpMeta.runas_succeeded
    runas_error = [string]$pnpMeta.runas_error
  }
  inventory = [ordered]@{
    computer_system = ($cs | Select-Object -First 1)
    bios = ($bios | Select-Object -First 1)
    baseboard = ($baseboard | Select-Object -First 1)
    processor = ($cpu | Select-Object -First 1)
    memory_modules = @($mem)
    disk_drives = @($disk)
    network_adapters = @($net)
    buses = [ordered]@{
      pci = @($pciDevices)
      acpi = @($acpiDevices)
      usb = @($usbDevices)
    }
  }
  counts = [ordered]@{
    pci_devices = @($pciDevices).Count
    acpi_devices = @($acpiDevices).Count
    usb_devices = @($usbDevices).Count
    memory_modules = @($mem).Count
    disk_drives = @($disk).Count
  }
  smart_write_readiness = [ordered]@{
    inventory_complete = $true
    has_pci_inventory = (@($pciDevices).Count -gt 0)
    has_firmware_identity = -not [string]::IsNullOrWhiteSpace((($bios | Select-Object -First 1).SMBIOSBIOSVersion))
    physical_write_enabled = $false
    note = 'Inventory phase only. No physical write or flashing is performed.'
  }
}

$payload | ConvertTo-Json -Depth 8 | Set-Content -Path $outJson -Encoding UTF8

$hash = (Get-FileHash -Algorithm SHA256 -Path $outJson).Hash
@("$hash  $(Split-Path -Leaf $outJson)") | Set-Content -Path $outSha -Encoding ASCII

if (-not [string]::IsNullOrWhiteSpace($ElevatedOutputPath)) {
  $bridge = [ordered]@{
    pnp = @($pnp | Select-Object Name, PNPDeviceID, Service, ClassGuid)
    counts = [ordered]@{
      pci_devices = @($pciDevices).Count
      acpi_devices = @($acpiDevices).Count
      usb_devices = @($usbDevices).Count
    }
    source = [string]$pnpMeta.collector_source
    is_admin = [bool](Test-IsAdministrator)
  }
  $bridge | ConvertTo-Json -Depth 6 | Set-Content -Path $ElevatedOutputPath -Encoding UTF8
}

$result = [ordered]@{
  ok = $true
  code = 'AXION_FW_INVENTORY_READY'
  machine_id = $MachineId
  manifest_path = $outJson
  sha256_path = $outSha
  pci_devices = @($pciDevices).Count
  acpi_devices = @($acpiDevices).Count
  usb_devices = @($usbDevices).Count
  collector_source = [string]$pnpMeta.collector_source
  runas_attempted = [bool]$pnpMeta.runas_attempted
  runas_succeeded = [bool]$pnpMeta.runas_succeeded
}

$result | ConvertTo-Json -Depth 5
