@echo off
cd /d "%~dp0" || exit /b 1
".venv\Scripts\python.exe" "main_agent.py"
