"""addons/redis_adapter.py

Optional, disabled-by-default Redis cache adapter for NOESIS agent memory.

BORROWED PATTERNS
-----------------
- LoopX: the "addon that degrades to a no-op when the optional backend is
  absent" pattern. LoopX ships its cache backend as a soft dependency so the
  core never hard-requires it. We mirror that: this module lives in addons/
  (not noesis_harness/) and only touches `redis` lazily, inside the methods
  that need it.
- agentmemory: the "recall never blocks on an unavailable store" guarantee.
  agentmemory keeps retrieval resilient when its primary store is down; this
  adapter keeps cache operations resilient when Redis is unavailable by
  returning a clear "disabled" result instead of raising.

WHY LAZY + DISABLED-BY-DEFAULT
------------------------------
AGENTS.md rule 1 (zero dependencies) forbids third-party packages in the core.
`redis` is an optional cache backend. This module must therefore:
  * import cleanly even when `redis` is NOT installed, and
  * never raise on missing dependencies -- instead return a clear "disabled"
    dict (status == "disabled") so callers can branch without try/except.

Every public method guards on lazy import failure and returns the disabled
shape. No global state imports `redis` at module load.

HONESTY BOUNDARY
----------------
- If `redis` is missing, `ping`, `get`, and `set` report status "disabled" and
  do nothing. They never claim a key was stored or retrieved.
- On a connection failure at runtime (not import failure) the adapter also
  reports status "disabled" with reason "error" rather than raising, so the
  cache is always a safe, best-effort layer.

Zero hard dependency on `redis` at import time.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _disabled_result(reason: str) -> Dict[str, Any]:
    return {
        "status": "disabled",
        "reason": reason,
        "hit": False,
    }


class RedisAdapter:
    """Thin optional Redis cache wrapper that never raises on a missing backend.

    Construct with a host/port/db/ttl; all operations are best-effort. When the
    `redis` package is absent or the server is unreachable, operations return a
    dict with status "disabled" and the call site proceeds without caching.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        default_ttl: Optional[int] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.default_ttl = default_ttl
        self._client = None

    def _connect(self):
        if self._client is not None:
            return self._client
        try:
            import redis  # type: ignore
        except Exception as exc:  # ImportError or any lazy-load failure
            return _disabled_result("redis not installed: %s" % exc)
        try:
            self._client = redis.Redis(host=self.host, port=self.port, db=self.db)
        except Exception as exc:
            return _disabled_result("redis connect failed: %s" % exc)
        return self._client

    def ping(self) -> Dict[str, Any]:
        """Check Redis connectivity. Returns status "ok" or "disabled"."""
        client = self._connect()
        if isinstance(client, dict):
            return client
        try:
            client.ping()
        except Exception as exc:
            return _disabled_result("redis error: %s" % exc)
        return {"status": "ok", "hit": True, "alive": True}

    def get(self, key: str) -> Dict[str, Any]:
        """Fetch a key. Returns status "ok" with value on hit, or "disabled"."""
        client = self._connect()
        if isinstance(client, dict):
            return client
        try:
            raw = client.get(key)
        except Exception as exc:
            return _disabled_result("redis error: %s" % exc)
        if raw is None:
            return {"status": "miss", "hit": False, "value": None}
        try:
            value = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
        except Exception:
            value = raw
        return {"status": "ok", "hit": True, "value": value}

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Store a value. Returns status "ok" on success or "disabled"."""
        client = self._connect()
        if isinstance(client, dict):
            return client
        try:
            effective_ttl = ttl if ttl is not None else self.default_ttl
            if effective_ttl is not None:
                client.set(key, value, ex=int(effective_ttl))
            else:
                client.set(key, value)
        except Exception as exc:
            return _disabled_result("redis error: %s" % exc)
        return {"status": "ok", "hit": True, "key": key, "stored": True}


_default_adapter = RedisAdapter()


def ping() -> Dict[str, Any]:
    """Module-level convenience: ping the default Redis adapter."""
    return _default_adapter.ping()


def get(key: str) -> Dict[str, Any]:
    """Module-level convenience: get from the default Redis adapter."""
    return _default_adapter.get(key)


def set(key: str, value: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
    """Module-level convenience: set on the default Redis adapter."""
    return _default_adapter.set(key, value, ttl=ttl)
