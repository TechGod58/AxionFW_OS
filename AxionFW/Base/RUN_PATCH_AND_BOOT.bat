@echo off
REM EXECUTION ONLY: PATCH EDK2 /WX + REBUILD + RUN QEMU
setlocal EnableExtensions

for %%I in ("%~dp0.") do set "AXIONFW_BASE=%%~fI"
for %%I in ("%AXIONFW_BASE%\..") do set "AXIONFW_ROOT=%%~fI"

set "PATH=%PATH%;C:\Program Files\NASM"
set "PATH=%PATH%;C:\Program Files\qemu"

REM Patch tools_def.txt to remove /WX
set "TOOLS_DEF=%AXIONFW_ROOT%\edk2\Conf\tools_def.txt"
if exist "%TOOLS_DEF%" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "(Get-Content -Raw '%TOOLS_DEF%') -replace '([ \t])/WX(\b)', '$1' | Set-Content -NoNewline '%TOOLS_DEF%'"
)

REM Rebuild firmware
cd /d "%AXIONFW_BASE%\scripts" || exit /b 1
call 01_bootstrap_edk2_ovmf.bat || exit /b %ERRORLEVEL%

REM Run QEMU
call 03_run_qemu_no_tpm.bat
set "EC=%ERRORLEVEL%"
exit /b %EC%