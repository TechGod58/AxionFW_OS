function Get-AxionOsRoot {
  param(
    [string]$ScriptPath = ""
  )

  if(-not [string]::IsNullOrWhiteSpace($ScriptPath) -and (Test-Path $ScriptPath)){
    $scriptDir = Split-Path -Parent (Resolve-Path $ScriptPath).Path
    $cursor = (Resolve-Path $scriptDir).Path
    while($true){
      if((Test-Path (Join-Path $cursor 'runtime')) -and (Test-Path (Join-Path $cursor 'config')) -and (Test-Path (Join-Path $cursor 'tools'))){
        return (Resolve-Path $cursor).Path
      }
      $parent = Split-Path -Parent $cursor
      if([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $cursor){
        break
      }
      $cursor = $parent
    }
  }

  if($env:AXIONOS_ROOT -and (Test-Path $env:AXIONOS_ROOT)){
    return (Resolve-Path $env:AXIONOS_ROOT).Path
  }

  $systemDrive = [System.Environment]::GetEnvironmentVariable('SystemDrive','Process')
  if([string]::IsNullOrWhiteSpace($systemDrive)){ $systemDrive = 'C:' }
  $legacyOs = Join-Path $systemDrive 'AxionOS'
  if(Test-Path $legacyOs){
    return (Resolve-Path $legacyOs).Path
  }

  throw 'Unable to resolve AxionOS root. Set AXIONOS_ROOT to the workspace path.'
}

function Get-AxionFwBase {
  param(
    [string]$OsRoot = ""
  )

  if($env:AXIONFW_BASE -and (Test-Path $env:AXIONFW_BASE)){
    return (Resolve-Path $env:AXIONFW_BASE).Path
  }

  if([string]::IsNullOrWhiteSpace($OsRoot)){
    $OsRoot = Get-AxionOsRoot
  }

  $combined = Join-Path (Split-Path -Parent $OsRoot) 'AxionFW\Base'
  if(Test-Path $combined){
    return (Resolve-Path $combined).Path
  }

  $systemDrive = [System.Environment]::GetEnvironmentVariable('SystemDrive','Process')
  if([string]::IsNullOrWhiteSpace($systemDrive)){ $systemDrive = 'C:' }
  $legacyFw = Join-Path $systemDrive 'AxionFW\Base'
  if(Test-Path $legacyFw){
    return (Resolve-Path $legacyFw).Path
  }

  return $legacyFw
}

function Enable-AxionLocalRuntimePath {
  param(
    [string]$OsRoot = ""
  )

  if([string]::IsNullOrWhiteSpace($OsRoot)){
    $OsRoot = Get-AxionOsRoot
  }

  $candidates = @(
    $OsRoot,
    (Join-Path $OsRoot 'tools\runtime\python311'),
    (Join-Path $OsRoot 'tools\runtime\python311\Scripts')
  )

  $existing = @()
  if(-not [string]::IsNullOrWhiteSpace($env:Path)){
    $existing = @($env:Path -split ';' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
  }

  foreach($p in $candidates){
    if((Test-Path $p) -and ($existing -notcontains $p)){
      $existing = @($p) + $existing
    }
  }

  $env:Path = ($existing -join ';')
}

function Get-AxionPythonInvocation {
  param(
    [string]$OsRoot = ""
  )

  if([string]::IsNullOrWhiteSpace($OsRoot)){
    $OsRoot = Get-AxionOsRoot
  }

  $repoPythonCmd = Join-Path $OsRoot 'python.cmd'
  if(Test-Path $repoPythonCmd){
    return [pscustomobject][ordered]@{
      file_path = $repoPythonCmd
      args_prefix = @()
      source = 'repo_python_cmd'
    }
  }

  $localPython = Join-Path $OsRoot 'tools\runtime\python311\python.exe'
  if(Test-Path $localPython){
    return [pscustomobject][ordered]@{
      file_path = $localPython
      args_prefix = @()
      source = 'local_python311'
    }
  }

  $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
  if($null -ne $pythonCmd){
    return [pscustomobject][ordered]@{
      file_path = $pythonCmd.Source
      args_prefix = @()
      source = 'system_python'
    }
  }

  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if($null -ne $pyLauncher){
    return [pscustomobject][ordered]@{
      file_path = $pyLauncher.Source
      args_prefix = @('-3')
      source = 'py_launcher_3'
    }
  }

  throw "Unable to resolve Python command. Install Python runtime or add python/py launcher to PATH."
}
