#!/usr/bin/env sh
# The verifier imports the noesis_harness package and the scripts modules from
# the repository root, but running a script file puts only that script's own
# directory on sys.path. Exporting the repository root is what makes the wrapper
# usable from any working directory; without it the wrapper exits 1 with
# ModuleNotFoundError: No module named 'noesis_harness'.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-python3}
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
exec "$PYTHON" "$ROOT/scripts/verify_operator_artifact_set.py" --require-signed-result "$@"
