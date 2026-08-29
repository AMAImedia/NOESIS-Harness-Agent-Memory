"""noesis_harness/crypto_hmac.py — HMAC signing.

Patterns: LoopX HMAC.
Stdlib only.
"""
from __future__ import annotations
import hashlib, hmac

def sign(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()
def verify(key: bytes, data: bytes, sig: str) -> bool:
    return hmac.compare_digest(hmac.new(key, data, hashlib.sha256).hexdigest(), sig)
