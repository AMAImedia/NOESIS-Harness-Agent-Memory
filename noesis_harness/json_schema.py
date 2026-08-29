"""noesis_harness/json_schema.py — minimal JSON schema validation.

Patterns: LoopX validation.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, Dict, List

def validate(data: Any, schema: dict) -> List[str]:
    errors: List[str] = []
    _check(data, schema, "", errors)
    return errors

def _check(data: Any, schema: dict, path: str, errors: List[str]) -> None:
    t = schema.get("type")
    if t == "string" and not isinstance(data, str): errors.append(f"{path}: expected string")
    elif t == "integer" and not isinstance(data, int): errors.append(f"{path}: expected integer")
    elif t == "number" and not isinstance(data, (int, float)): errors.append(f"{path}: expected number")
    elif t == "boolean" and not isinstance(data, bool): errors.append(f"{path}: expected boolean")
    elif t == "array":
        if not isinstance(data, list): errors.append(f"{path}: expected array")
        elif "items" in schema:
            for i, item in enumerate(data):
                _check(item, schema["items"], f"{path}[{i}]", errors)
    elif t == "object":
        if not isinstance(data, dict): errors.append(f"{path}: expected object")
        else:
            props = schema.get("properties", {})
            for key in schema.get("required", []):
                if key not in data: errors.append(f"{path+'.' if path else ''}{key}: required")
            for key, val in data.items():
                if key in props: _check(val, props[key], f"{path+'.' if path else ''}{key}", errors)
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: not in enum")
    if "minimum" in schema and isinstance(data, (int, float)) and data < schema["minimum"]:
        errors.append(f"{path}: below minimum")
    if "maximum" in schema and isinstance(data, (int, float)) and data > schema["maximum"]:
        errors.append(f"{path}: above maximum")
    if "minLength" in schema and isinstance(data, str) and len(data) < schema["minLength"]:
        errors.append(f"{path}: too short")
