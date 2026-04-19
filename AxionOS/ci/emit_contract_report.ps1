#requires -Version 5.1
$ErrorActionPreference='Stop'
$repoRoot=(Get-Location).Path
$buildId = if($env:AXION_BUILD_ID){$env:AXION_BUILD_ID}elseif($env:GITHUB_RUN_ID -and $env:GITHUB_SHA){"AXION_BUILD_"+([DateTimeOffset]::UtcNow).ToString('yyyyMMddTHHmmssZ')+"_RUN"+$env:GITHUB_RUN_ID}else{"AXION_BUILD_"+([DateTimeOffset]::UtcNow).ToString('yyyyMMddTHHmmssZ')}
$py = Join-Path $repoRoot 'tools\contracts\emit_contract_report.py'
$out = & python $py --build-id $buildId
Write-Host "[emit-contract-report] wrote=$out"
Write-Host "[emit-contract-report] build_id=$buildId"
exit 0
