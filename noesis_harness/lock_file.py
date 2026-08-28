"""noesis_harness/lock_file.py — advisory file lock (best-effort).

Patterns: LoopX file lock.
Stdlib only.
"""
from __future__ import annotations
import os, time

class FileLock:
    def __init__(self, path: str):
        self.path = path
    def acquire(self, timeout: float = 0) -> bool:
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd); return True
        except FileExistsError:
            return False
    def release(self) -> None:
        try: os.remove(self.path)
        except FileNotFoundError: pass
    def locked(self) -> bool:
        return os.path.exists(self.path)
