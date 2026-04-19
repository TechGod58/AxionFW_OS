@echo off
setlocal
set "AXION_PY=%~dp0tools\runtime\python311\python.exe"
if not exist "%AXION_PY%" (
  echo Axion local Python runtime not found at "%AXION_PY%".
  exit /b 1
)
set "AXION_PYTHONPATH=%~dp0;%CD%"
if not "%~1"=="" (
  if /I not "%~1"=="-m" (
    if /I not "%~1"=="-c" (
      set "AXION_PYTHONPATH=%~dp1;%AXION_PYTHONPATH%"
    )
  )
)
if defined PYTHONPATH (
  set "AXION_PYTHONPATH=%AXION_PYTHONPATH%;%PYTHONPATH%"
)
set "PYTHONPATH=%AXION_PYTHONPATH%"
"%AXION_PY%" %*
exit /b %ERRORLEVEL%
