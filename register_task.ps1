# Register Broadcast Server as Windows Task Scheduler Task
# Run this script as Administrator

$TaskName = "BroadcastServer"
$ScriptPath = "C:\Users\bssmBroadcast\BSMBC\start_server.ps1"
$PythonExe = "C:\Users\bssmBroadcast\BSMBC\venv\Scripts\python.exe"
$PythonScript = "C:\Users\bssmBroadcast\BSMBC\run_production.py"
$WorkingDir = "C:\Users\bssmBroadcast\BSMBC"

# Remove existing task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Create action - run python script directly
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $PythonScript -WorkingDirectory $WorkingDir

# Create trigger - at system startup
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Create settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Create principal - run as current user
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest

# Register the task
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Broadcast Control System Server (Production Mode)"

Write-Host "Task '$TaskName' has been registered successfully!"
Write-Host ""
Write-Host "Commands:"
Write-Host "  Start now:   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Stop:        Stop-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Remove:      Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host "  Status:      Get-ScheduledTask -TaskName '$TaskName'"




