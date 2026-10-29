@echo off
rem Opens the Agent Composer window. This console can stay minimized; closing it closes Agent Composer.
title Agent Composer
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if %errorlevel%==0 (
  uv run --no-project --python 3.12 app\server.py
) else (
  python app\server.py
)
if errorlevel 1 pause
