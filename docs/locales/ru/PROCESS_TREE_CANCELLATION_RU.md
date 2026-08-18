# Process-Tree Cancellation Contract

NOESIS различает cooperative callback cancellation и **process-level cancellation** для non-cooperative tools/skills. Python thread token не считается sandbox и не гарантирует остановку дочерних процессов.

| Platform/backend | Start semantics | Termination semantics | Current evidence |
|---|---|---|---|
| Linux direct runtime | New session/process group | `SIGTERM` process group, bounded grace, `SIGKILL` fallback | Local Python 3.14 regression passed |
| Linux/Bubblewrap | New session around `bwrap` child | Process-group termination through backend timeout path | Linux conformance passed; descendant timeout test passed |
| macOS sandbox backend | Native process group when run on Darwin | Backend timeout path plus process-group termination | Implemented; execution requires matching macOS host, current record `not_run` |
| Windows native | New process group plus `taskkill /T /F` fallback | Native process-tree termination | Requires matching Windows/Python 3.14 host, current record `not_run` |

## Acceptance criteria

A timeout must return stable `timeout` status, preserve bounded/redacted output, and never mark the action `done`. A non-cooperative descendant must not survive a POSIX process-group termination test. Missing target host or backend must produce `not_run`/fail-closed status rather than simulated native success.

## Operator commands

On Linux, run the local suite with the portable Python 3.14 runtime:

```text
runtime/python-3.14.7/build/bin/python3.14 -m unittest tests.test_child_execution tests.test_sandbox_bwrap tests.test_sandbox_conformance -q
```

On matching macOS or Windows hosts, run the same conformance tests with native Python 3.14 and store backend identity, host facts, timeout mechanism, and signed evidence. Do not change `sys.platform` or reinterpret Linux output as native evidence.
