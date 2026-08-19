$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
& $Python (Join-Path $Root "scripts\verify_release_gate_artifact.py") @args
exit $LASTEXITCODE
