"""noesis_harness/hashlib_util.py — hash helpers.

Patterns: LoopX crypto.
Stdlib only.
"""
from __future__ import annotations
import hashlib

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()
def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()
def hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
    return h.hexdigest()
