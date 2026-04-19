param(
  [string]$OutputPath = ""
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')
if([string]::IsNullOrWhiteSpace($OutputPath)){
  $osRoot = Get-AxionOsRoot -ScriptPath $PSCommandPath
  $OutputPath = Join-Path $osRoot 'out\hardware_inventory\windows_hardware_inventory.json'
}
$outFile = [System.IO.FileInfo]$OutputPath
$outFile.Directory.Create()

function Read-Instances($ClassName, $Props) {
  Get-CimInstance -ClassName $ClassName | ForEach-Object {
    $row = [ordered]@{}
    foreach ($prop in $Props) {
      $row[$prop] = $_.$prop
    }
    [pscustomobject]$row
  }
}

$payload = [ordered]@{
  collected_utc = [DateTime]::UtcNow.ToString('o')
  computer_system = Read-Instances -ClassName Win32_ComputerSystem -Props @('Manufacturer','Model','SystemFamily','TotalPhysicalMemory')
  bios = Read-Instances -ClassName Win32_BIOS -Props @('Manufacturer','SMBIOSBIOSVersion','ReleaseDate','SerialNumber')
  processor = Read-Instances -ClassName Win32_Processor -Props @('Name','Manufacturer','NumberOfCores','NumberOfLogicalProcessors','AddressWidth')
  baseboard = Read-Instances -ClassName Win32_BaseBoard -Props @('Manufacturer','Product','Version','SerialNumber')
  disk_drives = Read-Instances -ClassName Win32_DiskDrive -Props @('Model','InterfaceType','MediaType','Size','PNPDeviceID')
  logical_disks = Read-Instances -ClassName Win32_LogicalDisk -Props @('DeviceID','FileSystem','Size','FreeSpace','DriveType')
  network_adapters = Read-Instances -ClassName Win32_NetworkAdapter -Props @('Name','Manufacturer','MACAddress','PNPDeviceID','NetEnabled')
  video_controllers = Read-Instances -ClassName Win32_VideoController -Props @('Name','AdapterCompatibility','DriverVersion','PNPDeviceID')
  sound_devices = Read-Instances -ClassName Win32_SoundDevice -Props @('Name','Manufacturer','PNPDeviceID')
  battery = Read-Instances -ClassName Win32_Battery -Props @('Name','DeviceID','BatteryStatus')
  keyboards = Read-Instances -ClassName Win32_Keyboard -Props @('Name','Description','PNPDeviceID')
  pointing_devices = Read-Instances -ClassName Win32_PointingDevice -Props @('Name','Description','PNPDeviceID')
}

$payload | ConvertTo-Json -Depth 6 | Set-Content -Path $outFile.FullName -Encoding UTF8
Write-Host "[inventory] wrote $($outFile.FullName)"
