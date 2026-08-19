"""Build and verify deterministic operator artifact inventories.

Patterns are adapted from signed report bundle manifests, portable artifact
checksums, external evidence provenance, and operator-owned audit receipts. The
inventory is metadata only; it never executes files or follows artifact content.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "noesis.operator-artifact-inventory.v1"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_inventory(root: str | Path, files: Sequence[str | Path], key: str, provenance: Mapping[str, Any]) -> dict[str, Any]:
    base = Path(root).resolve()
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        raise ValueError("inventory_signing_key_too_short")
    entries: list[dict[str, Any]] = []
    for raw in files:
        path = Path(raw).resolve()
        if base not in path.parents or not path.is_file():
            raise ValueError("inventory_file_invalid")
        entries.append({"path": path.relative_to(base).as_posix(), "size": path.stat().st_size, "sha256": _sha256(path)})
    entries.sort(key=lambda item: item["path"])
    unsigned = {"schema_version": SCHEMA, "root": ".", "files": entries, "file_count": len(entries), "provenance": dict(provenance), "automatic_execution": False}
    return {**unsigned, "inventory_digest": hashlib.sha256(_canonical(unsigned)).hexdigest(), "signature": hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()}


def verify_inventory(inventory: Mapping[str, Any], root: str | Path, key: str) -> dict[str, Any]:
    if not isinstance(inventory, Mapping) or inventory.get("schema_version") != SCHEMA:
        return {"status": "blocked", "reason": "inventory_schema_invalid"}
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        return {"status": "blocked", "reason": "inventory_signing_key_too_short"}
    unsigned = {k: inventory[k] for k in inventory if k not in {"inventory_digest", "signature"}}
    expected_digest = hashlib.sha256(_canonical(unsigned)).hexdigest()
    if inventory.get("inventory_digest") != expected_digest:
        return {"status": "blocked", "reason": "inventory_digest_mismatch"}
    expected_signature = hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()
    if not isinstance(inventory.get("signature"), str) or not hmac.compare_digest(inventory["signature"], expected_signature):
        return {"status": "blocked", "reason": "inventory_signature_invalid"}
    base = Path(root).resolve()
    files = inventory.get("files")
    if not isinstance(files, list) or inventory.get("file_count") != len(files) or inventory.get("automatic_execution") is not False:
        return {"status": "blocked", "reason": "inventory_metadata_invalid"}
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, Mapping) or not isinstance(item.get("path"), str) or item["path"] in seen:
            return {"status": "blocked", "reason": "inventory_path_invalid"}
        seen.add(item["path"])
        path = (base / item["path"]).resolve()
        if base not in path.parents or not path.is_file() or _sha256(path) != item.get("sha256") or path.stat().st_size != item.get("size"):
            return {"status": "blocked", "reason": "inventory_file_mismatch"}
    return {"status": "passed", "inventory_digest": str(inventory["inventory_digest"]), "file_count": len(files)}
