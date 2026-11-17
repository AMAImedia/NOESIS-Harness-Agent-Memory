[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,
    [string]$Python = "py",
    [string]$PythonVersion = "-3.11",
    [string]$WorkerScript = "scripts\noesis_autoloop.py",
    [string]$Command,
    [double]$WorkerTimeoutSeconds = 300,
    [double]$RestartDelaySeconds = 15,
    [double]$MaxBackoffSeconds = 300,
    [int]$MaxCycles = 0,
    [switch]$ValidateHandoff,
    [switch]$WhatIf
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = [System.IO.Path]::GetFullPath($RepositoryRoot)
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    throw "repository_root_missing"
}
if ($WorkerTimeoutSeconds -le 0 -or $WorkerTimeoutSeconds -gt 86400) {
    throw "worker_timeout_out_of_bounds"
}
if ($RestartDelaySeconds -lt 0 -or $MaxBackoffSeconds -lt $RestartDelaySeconds) {
    throw "backoff_bounds_invalid"
}
if ($MaxCycles -lt 0) {
    throw "max_cycles_invalid"
}

$runtime = Join-Path $root ".noesis_autoloop"
$statePath = Join-Path $runtime "supervisor_state.json"
$logPath = Join-Path $runtime "supervisor.log"
$runtimeLog = Join-Path $runtime "supervisor_runtime"
New-Item -ItemType Directory -Force -Path $runtime, $runtimeLog | Out-Null

function Write-AtomicJson {
    param([string]$Path, [object]$Value)
    $temporary = "$Path.$PID.tmp"
    $json = $Value | ConvertTo-Json -Depth 8 -Compress
    [System.IO.File]::WriteAllText($temporary, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Write-SupervisorEvent {
    param([string]$Event, [hashtable]$Fields = @{})
    $record = @{ schema_version = "noesis.worker-supervisor.v1"; event = $Event; at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }
    foreach ($key in $Fields.Keys) { $record[$key] = $Fields[$key] }
    $line = $record | ConvertTo-Json -Depth 8 -Compress
    Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
}

$state = [ordered]@{
    schema_version = "noesis.worker-supervisor.v1"
    repository_root_digest = (([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($root)) | ForEach-Object { $_.ToString("x2") }) -join "")
    status = "starting"
    cycle = 0
    consecutive_failures = 0
    last_exit_code = $null
    last_worker_status = $null
    started_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    updated_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
}
Write-AtomicJson -Path $statePath -Value $state
Write-SupervisorEvent -Event "SUPERVISOR_START" -Fields @{ pid = $PID; max_cycles = $MaxCycles; timeout_seconds = $WorkerTimeoutSeconds }

$backoff = [Math]::Max(0, $RestartDelaySeconds)
try {
    while ($MaxCycles -eq 0 -or $state.cycle -lt $MaxCycles) {
        $state.cycle = [int]$state.cycle + 1
        $state.status = "starting_worker"
        $state.updated_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        Write-AtomicJson -Path $statePath -Value $state

        if ($ValidateHandoff) {
            $handoffOut = Join-Path $runtimeLog ("handoff-{0}.out" -f $state.cycle)
            $handoffErr = Join-Path $runtimeLog ("handoff-{0}.err" -f $state.cycle)
            $handoff = Start-Process -FilePath $Python -ArgumentList @($PythonVersion, $WorkerScript, "--root", $root, "--handoff") -WorkingDirectory $root -Wait -PassThru -NoNewWindow -RedirectStandardOutput $handoffOut -RedirectStandardError $handoffErr
            Write-SupervisorEvent -Event "HANDOFF_CHECK" -Fields @{ cycle = $state.cycle; exit_code = $handoff.ExitCode }
        }

        $stdoutPath = Join-Path $runtimeLog ("worker-{0}.out" -f $state.cycle)
        $stderrPath = Join-Path $runtimeLog ("worker-{0}.err" -f $state.cycle)
        $args = @($PythonVersion, $WorkerScript, "--root", $root, "--once", "--timeout", ([string]$WorkerTimeoutSeconds))
        if ($Command) { $args += @("--command", $Command) }
        $state.status = "worker_running"
        $state.updated_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        Write-AtomicJson -Path $statePath -Value $state
        Write-SupervisorEvent -Event "WORKER_START" -Fields @{ cycle = $state.cycle }

        if ($WhatIf) {
            $exitCode = 0
        } else {
            $process = Start-Process -FilePath $Python -ArgumentList $args -WorkingDirectory $root -PassThru -NoNewWindow -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
            $completed = $process.WaitForExit([int]($WorkerTimeoutSeconds * 1000))
            if (-not $completed) {
                try { $process.Kill($true) } catch { try { $process.Kill() } catch {} }
                $exitCode = 124
                Write-SupervisorEvent -Event "WORKER_TIMEOUT" -Fields @{ cycle = $state.cycle; timeout_seconds = $WorkerTimeoutSeconds }
            } else {
                $exitCode = $process.ExitCode
            }
        }

        $state.last_exit_code = $exitCode
        $state.last_worker_status = if ($exitCode -eq 0) { "passed" } elseif ($exitCode -eq 124) { "timed_out" } else { "failed" }
        $state.last_output_path = $stdoutPath
        $state.last_error_path = $stderrPath
        if ($exitCode -eq 0) {
            $state.status = "passed"
            $state.consecutive_failures = 0
            $backoff = [Math]::Max(0, $RestartDelaySeconds)
        } else {
            $state.status = "restart_pending"
            $state.consecutive_failures = [int]$state.consecutive_failures + 1
            $backoff = [Math]::Min($MaxBackoffSeconds, [Math]::Max($RestartDelaySeconds, [Math]::Max(1, $backoff * 2)))
        }
        $state.updated_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        Write-AtomicJson -Path $statePath -Value $state
        Write-SupervisorEvent -Event "WORKER_END" -Fields @{ cycle = $state.cycle; exit_code = $exitCode; status = $state.last_worker_status; backoff_seconds = $backoff }
        if ($MaxCycles -eq 0 -or $state.cycle -lt $MaxCycles) { Start-Sleep -Seconds ([int]$backoff) }
    }
    $state.status = "stopped_after_max_cycles"
    $state.updated_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    Write-AtomicJson -Path $statePath -Value $state
    Write-SupervisorEvent -Event "SUPERVISOR_STOP" -Fields @{ reason = "max_cycles"; cycle = $state.cycle }
    exit 0
} catch {
    $state.status = "failed"
    $state.error = $_.Exception.GetType().Name
    $state.updated_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    Write-AtomicJson -Path $statePath -Value $state
    Write-SupervisorEvent -Event "SUPERVISOR_ERROR" -Fields @{ error = $_.Exception.GetType().Name }
    throw
} finally {
    Write-SupervisorEvent -Event "SUPERVISOR_FINALLY" -Fields @{ cycle = $state.cycle }
}
