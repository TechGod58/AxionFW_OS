@echo off
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0.") do set "AXIONFW_BASE=%%~fI"
for %%I in ("%AXIONFW_BASE%\..") do set "AXIONFW_ROOT=%%~fI"

REM Session-only tool paths
set "PATH=%PATH%;C:\Program Files\NASM"
set "PATH=%PATH%;C:\Program Files\qemu"

set "EDK2=%AXIONFW_ROOT%\edk2"
if not exist "%EDK2%\BaseTools" (
  echo [!] Missing: %EDK2%\BaseTools
  echo     Run: %AXIONFW_BASE%\RUN_BOOTSTRAP.bat
  pause
  exit /b 1
)

REM Remove /WX from BaseTools makefiles (EDK2 BaseTools uses these flags)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root='%EDK2%\BaseTools\Source\C\Makefiles';" ^
  "Get-ChildItem -Path $root -Recurse -File | ForEach-Object { " ^
  "  $p=$_.FullName; $c=Get-Content -Raw -LiteralPath $p; " ^
  "  $n=$c -replace '([ \t])/WX(\b)', '$1' ; " ^
  "  if ($n -ne $c) { Set-Content -NoNewline -LiteralPath $p -Value $n; Write-Host ('[PATCH] ' + $p) }" ^
  "}"

REM Run existing bootstrap (idempotent)
cd /d "%AXIONFW_BASE%\scripts" || (echo [!] Missing %AXIONFW_BASE%\scripts & pause & exit /b 2)
call 01_bootstrap_edk2_ovmf.bat

REM Check for firmware
set "FWFD=%AXIONFW_ROOT%\edk2\Build\OvmfX64\DEBUG_VS2022\FV\OVMF.fd"
if exist "%FWFD%" (
  echo [OK] Found: %FWFD%
) else (
  echo [!] Still missing OVMF.fd
  pause
  exit /b 3
)

REM Run QEMU
call 03_run_qemu_no_tpm.bat

pause
endlocal