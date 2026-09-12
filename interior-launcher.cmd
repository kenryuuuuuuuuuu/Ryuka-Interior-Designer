@echo off
setlocal
rem Keep this entry point ASCII with CRLF line endings for Windows cmd.exe.
cd /d "%~dp0"
set "PYEXE="
where py >nul 2>nul
if not errorlevel 1 set "PYEXE=py -3"
if not defined PYEXE (
  where python >nul 2>nul
  if not errorlevel 1 set "PYEXE=python"
)
if not defined PYEXE (
  echo Python 3 was not found. Please install Python 3.
  pause
  exit /b 1
)
%PYEXE% -X utf8 "%~dp0scripts\guest_launcher\__main__.py" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo Launcher failed. Exit code: %RC%
  echo Check build\launcher\logs for details.
  pause
)
endlocal & exit /b %RC%
