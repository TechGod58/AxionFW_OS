@echo off
setlocal
set "AXION_PY=%~dp0tools\runtime\python311\python.exe"
if not exist "%AXION_PY%" (
  echo Axion local Python runtime not found at "%AXION_PY%".
  exit /b 1
)
"%AXION_PY%" -m pip %*
exit /b %ERRORLEVEL%
