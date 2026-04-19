@echo off
setlocal EnableExtensions

for %%I in ("%~dp0.") do set "AXIONFW_BASE=%%~fI"
set "PATH=%PATH%;C:\Program Files\NASM"
cd /d "%AXIONFW_BASE%\scripts" || exit /b 1
call 01_bootstrap_edk2_ovmf.bat
exit /b %ERRORLEVEL%