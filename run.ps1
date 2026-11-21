Write-Host "Starting EmergencyCare 360..." -ForegroundColor Cyan
Set-Location "$PSScriptRoot\emergencycare360"
& "..\.venv\Scripts\python.exe" app.py
