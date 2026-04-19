function Start-Heartbeat {
  param(
    [Parameter(Mandatory=$true)][string]$Phase,
    [int]$IntervalSec = 45,
    [Parameter(Mandatory=$true)][string]$LogPath
  )
  $scriptBlock = {
    param($Phase,$IntervalSec,$LogPath)
    $start = Get-Date
    while ($true) {
      $elapsed = [int]((Get-Date) - $start).TotalSeconds
      $line = "[rail] HEARTBEAT phase=$Phase step=-/- elapsed_s=$elapsed"
      Write-Output $line
      Add-Content -Path $LogPath -Value $line
      Start-Sleep -Seconds $IntervalSec
    }
  }
  $job = Start-Job -ScriptBlock $scriptBlock -ArgumentList $Phase,$IntervalSec,$LogPath
  return $job.Id
}

function Stop-Heartbeat {
  param([int]$HeartbeatJobId)
  if ($HeartbeatJobId) {
    $job = Get-Job -Id $HeartbeatJobId -ErrorAction SilentlyContinue
    if ($job) {
      Stop-Job -Id $HeartbeatJobId -ErrorAction SilentlyContinue | Out-Null
      Remove-Job -Id $HeartbeatJobId -ErrorAction SilentlyContinue | Out-Null
    }
  }
}
