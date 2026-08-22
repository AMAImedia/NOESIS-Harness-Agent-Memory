$ErrorActionPreference = 'Stop'
$repo = 'B:\Downloads\Portable\NOESIS-VC-ONE\models\llm\NOESIS-3.5B-A0.5B-DUBBING-FILM\_research_2026-08\NOESIS-Harness-Agent-Memory'
$bat = Join-Path $repo 'scripts\run_noesis_autoloop_windows.cmd'
$account = (whoami).Trim()
if (-not (Test-Path $bat)) { throw 'launcher_missing' }
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "' + $bat + '"') -WorkingDirectory $repo
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $account
$recoveryTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 2) -ExecutionTimeLimit (New-TimeSpan -Days 3650) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName 'NOESIS-Harness-AutoLoop' -Action $action -Trigger @($logonTrigger, $recoveryTrigger) -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName 'NOESIS-Harness-AutoLoop'
Start-Sleep -Seconds 10
$info = Get-ScheduledTaskInfo -TaskName 'NOESIS-Harness-AutoLoop'
Write-Output ('NOESIS_TASK_INSTALLED account=' + $account)
Write-Output ('STATE=' + (Get-ScheduledTask -TaskName 'NOESIS-Harness-AutoLoop').State)
Write-Output ('LAST_RESULT=' + $info.LastTaskResult)
Write-Output ('LAST_RUN=' + $info.LastRunTime)
