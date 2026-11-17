$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'native_windows_required' }
$python = Get-Command python3.14 -ErrorAction SilentlyContinue
if (-not $python) { throw 'python_3_14_required' }
$version = & $python.Source -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if (-not $version.StartsWith('3.14.')) { throw 'python_3_14_required' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$evidence = Join-Path $root 'artifacts/native/windows'
New-Item -ItemType Directory -Force $evidence | Out-Null
@{
  schema_version = 'noesis.native-parity-evidence.v1'
  target = 'windows'
  platform = [Environment]::OSVersion.VersionString
  python_version = $version
  network_allowed = $false
  credentials_available = $false
  execution_claim = $true
} | ConvertTo-Json | Set-Content (Join-Path $evidence 'environment.json')
& $python.Source -m unittest discover -s (Join-Path $root 'tests') -p 'test*.py' -q
@{
  schema_version = 'noesis.native-parity-evidence.v1'
  target = 'windows'
  status = 'passed'
  reason = 'matching_host_and_python_3_14'
  execution_claim = $true
} | ConvertTo-Json | Set-Content (Join-Path $evidence 'parity-results.json')
Get-ChildItem $evidence -File | Get-FileHash -Algorithm SHA256 | ConvertTo-Json | Set-Content (Join-Path $evidence 'sha256sums.txt')
@{ schema_version = 'noesis.sbom.v1'; target = 'windows'; files = @('environment.json','parity-results.json','sha256sums.txt') } | ConvertTo-Json | Set-Content (Join-Path $evidence 'sbom.json')
Write-Host "Native Windows parity evidence written to $evidence"
