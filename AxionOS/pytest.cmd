@echo off
setlocal
call "%~dp0python.cmd" -m pytest %*
exit /b %ERRORLEVEL%
