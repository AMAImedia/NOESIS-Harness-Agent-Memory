"""noesis_harness/paginator.py — pagination helper.

Patterns: LoopX pagination.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Any

def page(items: List[Any], page_size: int, page_num: int) -> List[Any]:
    if page_size < 1: raise ValueError("page_size >=1")
    if page_num < 0: raise ValueError("page_num >=0")
    start = page_num * page_size
    return items[start:start + page_size]
def total_pages(items: List[Any], page_size: int) -> int:
    if page_size < 1: raise ValueError("page_size >=1")
    return (len(items) + page_size - 1) // page_size
