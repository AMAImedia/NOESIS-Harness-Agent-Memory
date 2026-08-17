"""Pinned coding-task adapter with deterministic static verification.

The adapter intentionally parses source with ``ast`` but never executes a
submission. Dynamic execution is reported as ``unavailable``; this preserves
NOESIS's no-eval/no-exec and no-fake-sandbox contract while still providing a
small reproducible coding-task release gate.
"""
from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class PinnedCodingTask:
    task_id: str
    revision: str
    title: str
    required_function: str
    required_calls: Tuple[str, ...]
    required_keywords: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CodingVerification:
    task_id: str
    revision: str
    artifact_digest: str
    status: str
    execution_status: str
    passed_checks: Tuple[str, ...]
    failed_checks: Tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class CodingSuiteSummary:
    task_count: int
    passed: int
    failed: int
    unavailable: int
    pass_rate: float
    execution_status: str


PINNED_TASKS: Tuple[PinnedCodingTask, ...] = (
    PinnedCodingTask(
        "normalize-words-v1", "2026-08-17.1", "Normalize whitespace-delimited words", "normalize_words",
        ("strip", "split", "lower"),
    ),
    PinnedCodingTask(
        "safe-join-v1", "2026-08-17.1", "Join a path without escaping its root", "safe_join",
        ("resolve", "relative_to"),
    ),
    PinnedCodingTask(
        "canonical-json-v1", "2026-08-17.1", "Serialize JSON deterministically", "canonical_json",
        ("dumps",), ("sort_keys",),
    ),
)


_FORBIDDEN_CALLS = frozenset({
    "eval", "exec", "compile", "__import__", "system", "popen",
    "loads", "load", "run", "Popen",
})


class PinnedCodingTaskAdapter:
    """Verify a pinned coding task without executing untrusted source."""

    def __init__(self, tasks: Sequence[PinnedCodingTask] = PINNED_TASKS):
        self.tasks = {task.task_id: task for task in tasks}
        if not self.tasks:
            raise ValueError("at least one pinned task is required")

    @staticmethod
    def _digest(source: str) -> str:
        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    @staticmethod
    def _called_names(tree: ast.AST) -> Tuple[str, ...]:
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    names.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    names.append(node.func.attr)
        return tuple(sorted(set(names)))

    @staticmethod
    def _function_names(tree: ast.AST) -> Tuple[str, ...]:
        return tuple(sorted({node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}))

    def verify(self, task_id: str, source: str) -> CodingVerification:
        task = self.tasks.get(task_id)
        digest = self._digest(source if isinstance(source, str) else "")
        if task is None:
            return CodingVerification(task_id, "", digest, "unavailable", "unavailable", (), ("known_task",), "unknown pinned task")
        if not isinstance(source, str) or not source.strip():
            return CodingVerification(task_id, task.revision, digest, "failed", "unavailable", (), ("non_empty_source",), "source is empty or not text")
        try:
            tree = ast.parse(source, mode="exec")
        except (SyntaxError, ValueError, TypeError) as exc:
            return CodingVerification(task_id, task.revision, digest, "failed", "unavailable", (), ("parseable_python",), type(exc).__name__)
        called = set(self._called_names(tree))
        functions = set(self._function_names(tree))
        passed: List[str] = []
        failed: List[str] = []
        if task.required_function in functions:
            passed.append("required_function")
        else:
            failed.append("required_function")
        for name in task.required_calls:
            check = f"call:{name}"
            (passed if name in called else failed).append(check)
        source_lower = source.casefold()
        for keyword in task.required_keywords:
            check = f"keyword:{keyword}"
            (passed if keyword.casefold() in source_lower else failed).append(check)
        forbidden = sorted(called & _FORBIDDEN_CALLS)
        if forbidden:
            failed.append("forbidden_calls:" + ",".join(forbidden))
        else:
            passed.append("no_forbidden_calls")
        status = "passed" if not failed else "failed"
        reason = "static checks passed" if status == "passed" else "static checks failed"
        return CodingVerification(task.task_id, task.revision, digest, status, "unavailable", tuple(passed), tuple(failed), reason)

    def evaluate(self, submissions: Iterable[Tuple[str, str]]) -> Tuple[CodingVerification, ...]:
        return tuple(self.verify(task_id, source) for task_id, source in submissions)

    @staticmethod
    def summarize(results: Sequence[CodingVerification]) -> CodingSuiteSummary:
        passed = sum(result.status == "passed" for result in results)
        failed = sum(result.status == "failed" for result in results)
        unavailable = sum(result.status == "unavailable" for result in results)
        total = len(results)
        return CodingSuiteSummary(total, passed, failed, unavailable, passed / total if total else 1.0, "unavailable")


__all__ = ["CodingSuiteSummary", "CodingVerification", "PINNED_TASKS", "PinnedCodingTask", "PinnedCodingTaskAdapter"]
