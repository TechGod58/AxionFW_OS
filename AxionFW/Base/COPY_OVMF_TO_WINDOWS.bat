@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Finds OVMF firmware inside WSL and copies it to Windows OUT folder.

for %%I in ("%~dp0.") do set "AXIONFW_BASE=%%~fI"
for %%I in ("%AXIONFW_BASE%\..") do set "AXIONFW_ROOT=%%~fI"
set "OUTDIR=%AXIONFW_BASE%\out"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

set "OUTDIR_SLASH=%OUTDIR:\=/%"
set "FWROOT_SLASH=%AXIONFW_ROOT:\=/%"
set "WSL_OUT=/mnt/c%OUTDIR_SLASH:~2%"
set "WSL_FW_ROOT=/mnt/c%FWROOT_SLASH:~2%"

echo [*] Searching for OVMF*.fd in WSL (Ubuntu)...
echo     (If WSL prompts for a password, press Ctrl+C and tell me.)

wsl -d Ubuntu -- bash -lc ^
"set -e; " ^
"OUT='%WSL_OUT%'; mkdir -p \"$OUT\"; " ^
"FWROOT='%WSL_FW_ROOT%'; " ^
"candidates=( \"$FWROOT/edk2/Build\" \"$FWROOT/edk2\" '/home' '/root' ); " ^
"found=''; " ^
"for base in \"${candidates[@]}\"; do " ^
"  if [ -d \"$base\" ]; then " ^
"    f=$(find \"$base\" -maxdepth 8 -type f -name 'OVMF*.fd' 2>/dev/null | head -n 1 || true); " ^
"    if [ -n \"$f\" ]; then found=\"$f\"; break; fi; " ^
"  fi; " ^
"done; " ^
"if [ -z \"$found\" ]; then echo '[!] Not found'; exit 2; fi; " ^
"echo \"[*] Found: $found\"; " ^
"cp -f \"$found\" \"$OUT/OVMF.fd\"; " ^
"echo \"[*] Copied to: $OUT/OVMF.fd\"; " ^
"ls -la \"$OUT\""

if errorlevel 1 (
  echo [!] Copy failed.
  pause
  exit /b 1
)

echo [OK] Windows OUTDIR contents:
dir "%OUTDIR%"
pause
exit /b 0