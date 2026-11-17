#!/bin/zsh
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "native_macos_required" >&2
  exit 20
fi
PYTHON_BIN="$(command -v python3.14 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "python_3_14_required" >&2
  exit 21
fi
VERSION="$($PYTHON_BIN -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
[[ "$VERSION" == 3.14.* ]] || { echo "python_3_14_required" >&2; exit 21; }
ROOT="$(cd "${0:A:h}/.." && pwd)"
EVIDENCE="$ROOT/artifacts/native/macos"
mkdir -p "$EVIDENCE"
cat > "$EVIDENCE/environment.json" <<EOF
{"schema_version":"noesis.native-parity-evidence.v1","target":"macos","platform":"$(sw_vers -productVersion)","python_version":"$VERSION","network_allowed":false,"credentials_available":false,"execution_claim":true}
EOF
(cd "$ROOT" && "$PYTHON_BIN" -m unittest discover -s tests -p 'test*.py' -q)
cat > "$EVIDENCE/parity-results.json" <<EOF
{"schema_version":"noesis.native-parity-evidence.v1","target":"macos","status":"passed","reason":"matching_host_and_python_3_14","execution_claim":true}
EOF
(cd "$EVIDENCE" && shasum -a 256 environment.json parity-results.json > sha256sums.txt)
cat > "$EVIDENCE/sbom.json" <<EOF
{"schema_version":"noesis.sbom.v1","target":"macos","files":["environment.json","parity-results.json","sha256sums.txt"]}
EOF
printf 'Native macOS parity evidence written to %s\n' "$EVIDENCE"
