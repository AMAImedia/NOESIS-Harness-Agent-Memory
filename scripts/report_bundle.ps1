[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Arguments
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
& $Python (Join-Path $Root "scripts/report_bundle.py") @Arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
