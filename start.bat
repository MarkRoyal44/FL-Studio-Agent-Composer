@echo off
rem Opens the Agent Composer window. Keep this window open while you use it.
cd /d "%~dp0"
python app\server.py
if errorlevel 1 pause
