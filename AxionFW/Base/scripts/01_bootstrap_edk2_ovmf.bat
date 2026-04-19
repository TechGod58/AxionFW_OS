@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "AXIONFW_BASE_DEFAULT=%%~fI"
if "%AXIONFW_BASE%"=="" set "AXIONFW_BASE=%AXIONFW_BASE_DEFAULT%"
if "%AXIONFW_DISTRO%"=="" set "AXIONFW_DISTRO=Ubuntu"
if "%AXIONFW_WSL_USER%"=="" set "AXIONFW_WSL_USER=root"
if "%AXIONFW_INSTALL_DEPS%"=="" set "AXIONFW_INSTALL_DEPS=0"
if "%AXIONFW_BUILD_TARGET%"=="" set "AXIONFW_BUILD_TARGET=DEBUG"
if "%AXIONFW_TOOLCHAIN%"=="" set "AXIONFW_TOOLCHAIN=GCC5"
if "%AXIONFW_PLATFORM_DSC%"=="" set "AXIONFW_PLATFORM_DSC=OvmfPkg/OvmfPkgX64.dsc"
if "%AXIONFW_BUILD_TIMEOUT_SECS%"=="" set "AXIONFW_BUILD_TIMEOUT_SECS=0"
if "%AXIONFW_REUSE_IF_PRESENT%"=="" set "AXIONFW_REUSE_IF_PRESENT=0"
if "%AXIONFW_CLEAN_BUILD%"=="" set "AXIONFW_CLEAN_BUILD=0"
if "%AXIONFW_SYNC_SUBMODULES%"=="" set "AXIONFW_SYNC_SUBMODULES=0"
if "%AXIONFW_NO_PAUSE%"=="" set "AXIONFW_NO_PAUSE=0"

for %%I in ("%AXIONFW_BASE%\..\edk2") do set "AXIONFW_EDK2_WIN=%%~fI"
for %%I in ("%AXIONFW_BASE%\out") do set "OUTWIN=%%~fI"
for %%I in ("%AXIONFW_BASE%\scripts\wsl_build_ovmf.sh") do set "AXIONFW_BUILD_SH_WIN=%%~fI"
if not exist "%OUTWIN%" mkdir "%OUTWIN%"

call :ToWslPath "%AXIONFW_EDK2_WIN%" AXIONFW_EDK2_MNT
call :ToWslPath "%OUTWIN%" AXIONFW_OUT_MNT
call :ToWslPath "%AXIONFW_BUILD_SH_WIN%" AXIONFW_BUILD_SH_MNT

where wsl >nul 2>nul || (
  echo [!] wsl.exe missing
  if "%AXIONFW_NO_PAUSE%"=="0" pause
  exit /b 1
)

echo [*] Building OVMF in WSL distro=%AXIONFW_DISTRO% user=%AXIONFW_WSL_USER%
echo [*] Base=%AXIONFW_BASE%
echo [*] EDK2=%AXIONFW_EDK2_WIN%
echo [*] Output: %OUTWIN%
echo [*] Target=%AXIONFW_BUILD_TARGET% Toolchain=%AXIONFW_TOOLCHAIN% Reuse=%AXIONFW_REUSE_IF_PRESENT% Clean=%AXIONFW_CLEAN_BUILD% SyncSubmodules=%AXIONFW_SYNC_SUBMODULES% Timeout=%AXIONFW_BUILD_TIMEOUT_SECS%s

wsl -d %AXIONFW_DISTRO% -u %AXIONFW_WSL_USER% -- env ^
  AXIONFW_EDK2_MNT=%AXIONFW_EDK2_MNT% ^
  AXIONFW_OUT_MNT=%AXIONFW_OUT_MNT% ^
  AXIONFW_BUILD_TARGET=%AXIONFW_BUILD_TARGET% ^
  AXIONFW_TOOLCHAIN=%AXIONFW_TOOLCHAIN% ^
  AXIONFW_PLATFORM_DSC=%AXIONFW_PLATFORM_DSC% ^
  AXIONFW_BUILD_TIMEOUT_SECS=%AXIONFW_BUILD_TIMEOUT_SECS% ^
  AXIONFW_REUSE_IF_PRESENT=%AXIONFW_REUSE_IF_PRESENT% ^
  AXIONFW_CLEAN_BUILD=%AXIONFW_CLEAN_BUILD% ^
  AXIONFW_SYNC_SUBMODULES=%AXIONFW_SYNC_SUBMODULES% ^
  bash %AXIONFW_BUILD_SH_MNT% %AXIONFW_INSTALL_DEPS%
if errorlevel 1 (
  echo [!] WSL build failed.
  if "%AXIONFW_NO_PAUSE%"=="0" pause
  exit /b 1
)

echo [OK] Windows OUT folder:
dir "%OUTWIN%"
if "%AXIONFW_NO_PAUSE%"=="0" pause
exit /b 0

:ToWslPath
setlocal EnableDelayedExpansion
set "WINPATH=%~1"
set "DRIVE=!WINPATH:~0,1!"
if /I "!DRIVE!"=="A" set "DRIVE=a"
if /I "!DRIVE!"=="B" set "DRIVE=b"
if /I "!DRIVE!"=="C" set "DRIVE=c"
if /I "!DRIVE!"=="D" set "DRIVE=d"
if /I "!DRIVE!"=="E" set "DRIVE=e"
if /I "!DRIVE!"=="F" set "DRIVE=f"
if /I "!DRIVE!"=="G" set "DRIVE=g"
if /I "!DRIVE!"=="H" set "DRIVE=h"
if /I "!DRIVE!"=="I" set "DRIVE=i"
if /I "!DRIVE!"=="J" set "DRIVE=j"
if /I "!DRIVE!"=="K" set "DRIVE=k"
if /I "!DRIVE!"=="L" set "DRIVE=l"
if /I "!DRIVE!"=="M" set "DRIVE=m"
if /I "!DRIVE!"=="N" set "DRIVE=n"
if /I "!DRIVE!"=="O" set "DRIVE=o"
if /I "!DRIVE!"=="P" set "DRIVE=p"
if /I "!DRIVE!"=="Q" set "DRIVE=q"
if /I "!DRIVE!"=="R" set "DRIVE=r"
if /I "!DRIVE!"=="S" set "DRIVE=s"
if /I "!DRIVE!"=="T" set "DRIVE=t"
if /I "!DRIVE!"=="U" set "DRIVE=u"
if /I "!DRIVE!"=="V" set "DRIVE=v"
if /I "!DRIVE!"=="W" set "DRIVE=w"
if /I "!DRIVE!"=="X" set "DRIVE=x"
if /I "!DRIVE!"=="Y" set "DRIVE=y"
if /I "!DRIVE!"=="Z" set "DRIVE=z"
set "TAIL=!WINPATH:~2!"
set "TAIL=!TAIL:\=/!"
endlocal & set "%~2=/mnt/%DRIVE%%TAIL%"
exit /b 0
