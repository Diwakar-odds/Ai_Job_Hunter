# ============================================================================
# setup_scheduler.ps1 - Create or Remove a Windows Task Scheduler task
#                        for the AI Job Hunter agent.
#
# Usage:
#   To CREATE the scheduled task:
#     powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1
#
#   To REMOVE the scheduled task:
#     powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1 -Remove
# ============================================================================

param(
    [switch]$Remove
)

$TaskName = "AI_Job_Hunter"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$SrcDir = Join-Path $ProjectRoot "src"
$PythonExe = "python"  # Assumes python is on PATH; change to full path if needed
$ScriptPath = Join-Path $SrcDir "main.py"
$IntervalMinutes = 60

# ---- REMOVE MODE ----
if ($Remove) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host "  Removing Task: $TaskName" -ForegroundColor Yellow
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host ""

    try {
        $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($existing) {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
            Write-Host "[SUCCESS] Task '$TaskName' has been removed." -ForegroundColor Green
        } else {
            Write-Host "[INFO] Task '$TaskName' does not exist. Nothing to remove." -ForegroundColor Cyan
        }
    } catch {
        Write-Host "[ERROR] Failed to remove task: $_" -ForegroundColor Red
        exit 1
    }
    exit 0
}

# ---- CREATE MODE ----
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setting up Task: $TaskName" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project Root : $ProjectRoot"
Write-Host "  Source Dir   : $SrcDir"
Write-Host "  Script       : $ScriptPath"
Write-Host "  Interval     : Every $IntervalMinutes minutes"
Write-Host ""

# Validate that main.py exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host "[ERROR] main.py not found at: $ScriptPath" -ForegroundColor Red
    Write-Host "        Make sure you run this script from the project root." -ForegroundColor Red
    exit 1
}

try {
    # Remove existing task if present
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "[INFO] Task '$TaskName' already exists. Replacing..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    # Create the action: run python main.py from the src directory
    $Action = New-ScheduledTaskAction `
        -Execute $PythonExe `
        -Argument "`"$ScriptPath`"" `
        -WorkingDirectory $SrcDir

    # Create the trigger: repeat every N minutes indefinitely
    $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
        -RepetitionDuration (New-TimeSpan -Days 9999)

    # Create settings
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

    # Register the task for the current user
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "AI Job Hunter - Automated job search every $IntervalMinutes minutes" `
        -RunLevel Limited

    Write-Host ""
    Write-Host "[SUCCESS] Scheduled task '$TaskName' created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  The job hunter will run every $IntervalMinutes minutes." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  To view the task:" -ForegroundColor Gray
    Write-Host "    Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  To run it immediately:" -ForegroundColor Gray
    Write-Host "    Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  To REMOVE the task:" -ForegroundColor Gray
    Write-Host "    powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1 -Remove" -ForegroundColor Gray
    Write-Host ""

} catch {
    Write-Host "[ERROR] Failed to create scheduled task: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  You may need to run this script as Administrator." -ForegroundColor Yellow
    exit 1
}
