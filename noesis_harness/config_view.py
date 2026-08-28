"""noesis_harness/config_view.py — read-only config view.

Patterns: LoopX projection.
Stdlib only.
"""
from __future__ import annotations
import hashlib, json, os
from typing import Any, Dict, List

def view(path: str) -> Dict[str, Any]:
    cfg = {}
    if os.path.isfile(path):
        try: cfg = json.loads(open(path, encoding="utf-8").read())
        except (ValueError, OSError): cfg = {}
    if not isinstance(cfg, dict): cfg = {"value": cfg}
    canon = json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    return {"path": path, "config": cfg, "keys": sorted(cfg.keys()), "digest": digest}

def get(cfg_view: Dict[str, Any], key: str, default: Any = None) -> Any:
    return cfg_view.get("config", {}).get(key, default)
