# Unregister Broadcast Server from Task Scheduler
# Run this script as Administrator

$TaskName = "BroadcastServer"

# Stop the task if running
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

# Kill any running python processes
Stop-Process -Name python -Force -ErrorAction SilentlyContinue

# Unregister the task
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "Task '$TaskName' has been unregistered and stopped."




