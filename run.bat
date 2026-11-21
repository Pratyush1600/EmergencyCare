@echo off
echo Starting EmergencyCare 360...
cd /d "%~dp0emergencycare360"
call "..\.venv\Scripts\python.exe" app.py
pause
