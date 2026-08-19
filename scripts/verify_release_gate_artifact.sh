#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-python3}
exec "$PYTHON" "$ROOT/scripts/verify_release_gate_artifact.py" "$@"
