@echo off
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0.") do set "AXIONFW_BASE_DEFAULT=%%~fI"
if "%AXIONFW_BASE%"=="" set "AXIONFW_BASE=%AXIONFW_BASE_DEFAULT%"
if "%AXIONFW_NO_PAUSE%"=="" set "AXIONFW_NO_PAUSE=0"

set "PATH=%PATH%;C:\Program Files\NASM"
set "PATH=%PATH%;C:\Program Files\qemu"

cd /d "%AXIONFW_BASE%\scripts" || exit /b 1
call 01_bootstrap_edk2_ovmf.bat || exit /b 1
call 03_run_qemu_no_tpm.bat
set "EC=%ERRORLEVEL%"
if "%AXIONFW_NO_PAUSE%"=="0" pause
exit /b %EC%