"""Read-only runtime environment probe.

Borrowed patterns:
- LoopX: deterministic, side-effect-free introspection of the host so that
  orchestration decisions can be made from a stable snapshot without mutating
  process state or touching the filesystem.
"""

import os
import platform
import sys


def probe():
    """Return a read-only snapshot of the current runtime environment.

    Pure function: performs no filesystem writes, no network calls, and no
    mutation of process state. Safe to call repeatedly.

    Returns:
        dict with keys:
            os (str): platform.system() value (e.g. "Windows", "Linux").
            python_version (str): sys.version.
            cwd (str): current working directory (os.getcwd()).
            pid (int): current process id (os.getpid()).
            cpu_count (int or None): os.cpu_count().
    """
    return {
        "os": platform.system(),
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "cpu_count": os.cpu_count(),
    }
