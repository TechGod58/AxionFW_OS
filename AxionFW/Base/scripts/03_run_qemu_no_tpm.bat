@echo off
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0..") do set "AXIONFW_BASE_DEFAULT=%%~fI"
if "%AXIONFW_BASE%"=="" set "AXIONFW_BASE=%AXIONFW_BASE_DEFAULT%"
if "%AXIONFW_NO_PAUSE%"=="" set "AXIONFW_NO_PAUSE=0"
if "%AXIONFW_QEMU_ACCEL%"=="" set "AXIONFW_QEMU_ACCEL=tcg"

if exist "C:\Program Files\qemu\qemu-system-x86_64.exe" set "PATH=%PATH%;C:\Program Files\qemu"
where qemu-system-x86_64 >nul 2>nul || (
  echo [!] qemu-system-x86_64 not found on PATH
  if "%AXIONFW_NO_PAUSE%"=="0" pause
  exit /b 1
)

set "OUTDIR=%AXIONFW_BASE%\out"
set "ONE=%OUTDIR%\OVMF.fd"
set "CODE=%OUTDIR%\OVMF_CODE.fd"
set "VARS=%OUTDIR%\OVMF_VARS.fd"
set "RUNTIME_VARS=%OUTDIR%\OVMF_VARS.runtime.fd"

if exist "%CODE%" if exist "%VARS%" (
  copy /y "%VARS%" "%RUNTIME_VARS%" >nul
  if errorlevel 1 (
    echo [!] Failed to prepare runtime vars copy: %RUNTIME_VARS%
    if "%AXIONFW_NO_PAUSE%"=="0" pause
    exit /b 1
  )
  echo [*] Using %CODE% + %RUNTIME_VARS%
  qemu-system-x86_64 -machine q35,accel=%AXIONFW_QEMU_ACCEL% -m 2048 -cpu qemu64 -drive if=pflash,format=raw,readonly=on,file="%CODE%" -drive if=pflash,format=raw,file="%RUNTIME_VARS%" -net none -serial stdio
  exit /b %errorlevel%
)

if exist "%ONE%" (
  echo [*] Using %ONE%
  qemu-system-x86_64 -machine q35,accel=%AXIONFW_QEMU_ACCEL% -m 2048 -cpu qemu64 -drive if=pflash,format=raw,readonly=on,file="%ONE%" -net none -serial stdio
  exit /b %errorlevel%
)

echo [!] Firmware missing in %OUTDIR%
if "%AXIONFW_NO_PAUSE%"=="0" pause
exit /b 1