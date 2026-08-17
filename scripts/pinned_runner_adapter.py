#!/usr/bin/env python3
"""Execute an explicitly approved pinned runner without shell interpolation."""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from scripts.external_runner_contract import REQUIRED_FIELDS, validate_result

_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|bearer)\s*[:=]?\s*[^\s,;]+")


class RunnerExecutionDenied(PermissionError):
    pass


class RunnerConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class RunnerOutcome:
    status: str
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool


def _redact(value: str) -> str:
    return _SECRET.sub(r"\1=[REDACTED]", value)


def _validate_spec(spec: Mapping[str, object], workspace: str) -> tuple[list[str], Path, dict[str, str]]:
    missing = [field for field in REQUIRED_FIELDS if field not in spec]
    if missing:
        raise RunnerConfigurationError("missing spec fields: " + ",".join(missing))
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise RunnerConfigurationError("disposable workspace must already exist")
    policy = spec.get("workspace")
    if not isinstance(policy, Mapping) or policy.get("mode") != "disposable" or policy.get("outside_access") != "deny" or policy.get("credentials") != "absent":
        raise RunnerConfigurationError("runner workspace policy is not disposable/deny/credential-free")
    argv = spec.get("argv")
    if isinstance(argv, str) or not isinstance(argv, Sequence) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise RunnerConfigurationError("runner argv must be a non-empty string array")
    environment = {"PATH": os.environ.get("PATH", ""), "NOESIS_EXTERNAL_RUNNER": "1"}
    return list(argv), root, environment


def validate(spec: Mapping[str, object], workspace: str) -> tuple[list[str], Path, dict[str, str]]:
    """Validate a runner plan without granting execution approval."""
    return _validate_spec(spec, workspace)


def prepare(spec: Mapping[str, object], workspace: str, approval: bool = False) -> tuple[list[str], Path, dict[str, str]]:
    if not approval:
        raise RunnerExecutionDenied("explicit runner approval is required")
    return _validate_spec(spec, workspace)


def execute(spec: Mapping[str, object], workspace: str, approval: bool = False, timeout: float = 120.0) -> RunnerOutcome:
    argv, root, environment = prepare(spec, workspace, approval)
    try:
        completed = subprocess.run(argv, cwd=root, env=environment, capture_output=True, text=True, timeout=timeout, check=False, shell=False)
    except subprocess.TimeoutExpired as exc:
        return RunnerOutcome("failed", None, _redact(exc.stdout or ""), _redact(exc.stderr or ""), True)
    return RunnerOutcome("passed" if completed.returncode == 0 else "failed", completed.returncode, _redact(completed.stdout), _redact(completed.stderr), False)


__all__ = ["RunnerConfigurationError", "RunnerExecutionDenied", "RunnerOutcome", "execute", "prepare", "validate"]
