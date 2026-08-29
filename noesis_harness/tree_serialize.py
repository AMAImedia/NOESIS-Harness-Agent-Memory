"""noesis_harness/tree_serialize.py — serialize/deserialize tree to JSON.

Patterns: LoopX tree serialization.
Stdlib only.
"""
from __future__ import annotations
import json
from typing import Any

def tree_to_dict(node: Any, children_attr: str = "children", value_attr: str = "value") -> dict:
    d = {value_attr: getattr(node, value_attr, None)}
    kids = getattr(node, children_attr, [])
    if kids: d[children_attr] = [tree_to_dict(c, children_attr, value_attr) for c in kids]
    return d
def tree_from_dict(d: dict, children_attr: str = "children", value_attr: str = "value") -> dict:
    node = {"value": d.get(value_attr)}
    kids = d.get(children_attr, [])
    if kids: node["children"] = [tree_from_dict(c, children_attr, value_attr) for c in kids]
    return node
