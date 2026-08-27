"""Read-only capability inventory for the NOESIS harness.

Patterns borrowed from:
- Cloudflare-OS: capability manifest model used to declare and inspect
  what a runtime/environment is allowed to do without mutating state.
- agentmemory: stable, content-addressed snapshot digests so a view can be
  fingerprinted and compared deterministically across runs.

This module is pure and side-effect free. It only reads a capabilities
manifest JSON file and projects it into an immutable-shaped view. It uses
just the Python standard library (hashlib, json) so it can be imported on
dependency-free paths inside the harness.
"""

import hashlib
import json


def _read_manifest(path):
    """Read and parse a capabilities manifest JSON file.

    Returns the parsed object. Raises the underlying ``OSError`` or
    ``json.JSONDecodeError`` if the file is missing or malformed.
    """
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_capabilities(manifest):
    """Normalize a manifest object into a sorted list of capability dicts.

    Accepts either a mapping with a ``capabilities`` key (list of dicts or
    list of name strings) or a bare list of capabilities. Each capability is
    projected to ``{"name": str, "enabled": bool}``. Capabilities are sorted
    by name so the resulting view is order-independent and deterministic.
    """
    raw = manifest
    if isinstance(manifest, dict):
        raw = manifest.get("capabilities", [])

    if not isinstance(raw, list):
        raise ValueError("capabilities manifest must contain a list")

    capabilities = []
    for item in raw:
        if isinstance(item, str):
            name = item
            enabled = True
        elif isinstance(item, dict):
            name = item.get("name")
            if name is None:
                raise ValueError("capability entry missing 'name'")
            enabled = bool(item.get("enabled", True))
        else:
            raise ValueError("capability entry must be a string or object")
        capabilities.append({"name": str(name), "enabled": enabled})

    capabilities.sort(key=lambda cap: cap["name"])
    return capabilities


def _digest(capabilities):
    """Compute a stable SHA-256 hex digest over the normalized capabilities."""
    canonical = json.dumps(
        capabilities,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def view(path):
    """Load a capabilities manifest and return a read-only view dict.

    The returned dict has the shape::

        {
            "path": <source path>,
            "capabilities": [{"name": str, "enabled": bool}, ...],
            "count": <int>,
            "enabled_count": <int>,
            "digest": <sha256 hex>,
        }

    ``capabilities`` is sorted by name, making the view deterministic
    regardless of manifest ordering. The ``digest`` is a stable content
    fingerprint of the capability set.
    """
    manifest = _read_manifest(path)
    capabilities = _normalize_capabilities(manifest)
    enabled_count = sum(1 for cap in capabilities if cap["enabled"])
    return {
        "path": path,
        "capabilities": capabilities,
        "count": len(capabilities),
        "enabled_count": enabled_count,
        "digest": _digest(capabilities),
    }


def filter_enabled(view):
    """Return the list of capability names that are enabled in ``view``.

    ``view`` is a dict as produced by :func:`view`. The returned names are
    ordered by the (already sorted) capability list.
    """
    return [
        cap["name"]
        for cap in view.get("capabilities", [])
        if cap.get("enabled")
    ]
