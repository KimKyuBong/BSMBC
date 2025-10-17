# Production Server Startup Script
# Run this via Task Scheduler for background execution

Set-Location "C:\Users\bssmBroadcast\BSMBC"

$pythonExe = "C:\Users\bssmBroadcast\BSMBC\venv\Scripts\python.exe"
$scriptPath = "C:\Users\bssmBroadcast\BSMBC\run_production.py"

# Start the server process in the background
Start-Process -FilePath $pythonExe -ArgumentList $scriptPath -WindowStyle Hidden -WorkingDirectory "C:\Users\bssmBroadcast\BSMBC"

Write-Host "Server started in background"
Write-Host "Check status: Get-Process python"
Write-Host "Stop server: Stop-Process -Name python -Force"




