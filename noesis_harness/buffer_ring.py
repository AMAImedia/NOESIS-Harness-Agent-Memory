"""noesis_harness/buffer_ring.py — ring buffer for bytes.

Patterns: LoopX ring buffer.
Stdlib only.
"""
from __future__ import annotations

class ByteBuffer:
    def __init__(self, size: int):
        if size < 1: raise ValueError("size >=1")
        self._buf = bytearray(size); self._head = 0; self._count = 0; self._size = size
    def write(self, data: bytes) -> int:
        n = min(len(data), self._size - self._count)
        for i in range(n): self._buf[(self._head + self._count + i) % self._size] = data[i]
        self._count += n; return n
    def read(self, n: int = -1) -> bytes:
        if n < 0: n = self._count
        n = min(n, self._count); out = bytes(self._buf[(self._head + i) % self._size] for i in range(n))
        self._head = (self._head + n) % self._size; self._count -= n; return out
    def peek(self, n: int = -1) -> bytes:
        if n < 0: n = self._count
        n = min(n, self._count)
        return bytes(self._buf[(self._head + i) % self._size] for i in range(n))
    def available(self) -> int: return self._count
    def free(self) -> int: return self._size - self._count
    def __len__(self): return self._count
