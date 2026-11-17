$ErrorActionPreference = "Stop"
# The verifier imports the noesis_harness package and the scripts modules from
# the repository root, but running a script file puts only that script's own
# directory on sys.path. Prepending the repository root keeps this wrapper at
# the same contract as verify_operator_artifacts.sh.
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$Root;$env:PYTHONPATH" } else { $Root }
& $Python (Join-Path $Root "scripts\verify_operator_artifact_set.py") --require-signed-result @args
exit $LASTEXITCODE
