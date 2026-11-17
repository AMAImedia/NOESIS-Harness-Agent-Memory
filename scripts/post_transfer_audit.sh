#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-python3}
exec "$PYTHON" "$ROOT/scripts/post_transfer_audit.py" "$@"
