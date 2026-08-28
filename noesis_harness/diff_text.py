"""noesis_harness/diff_text.py — line diff (LCS based).

Patterns: LoopX diff.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Tuple

def diff_lines(a: List[str], b: List[str]) -> List[Tuple[str, str]]:
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if a[i] == b[j]: dp[i][j] = dp[i + 1][j + 1] + 1
            else: dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    out = []; i = j = 0
    while i < n and j < m:
        if a[i] == b[j]: out.append((" ", a[i])); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]: out.append(("-", a[i])); i += 1
        else: out.append(("+", b[j])); j += 1
    while i < n: out.append(("-", a[i])); i += 1
    while j < m: out.append(("+", b[j])); j += 1
    return out
