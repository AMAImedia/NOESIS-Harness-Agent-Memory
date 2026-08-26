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
    jail_blocked_hosts: tuple = ()
    jail_allowed_count: int = 0


def _redact(value) -> str:
    text = value.decode("utf-8", "replace") if isinstance(value, bytes) else (value if isinstance(value, str) else "")
    return _SECRET.sub(r"\1=[REDACTED]", text)


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
    inherited = {name: os.environ[name] for name in ("PATH", "SystemRoot", "SystemDrive", "TEMP", "TMP", "COMSPEC", "PATHEXT") if name in os.environ}
    environment = {**inherited, "NOESIS_EXTERNAL_RUNNER": "1"}
    credential_names = spec.get("credentials_env")
    if isinstance(credential_names, Sequence) and not isinstance(credential_names, str):
        for name in credential_names:
            if isinstance(name, str) and name in os.environ:
                environment[name] = os.environ[name]
    return list(argv), root, environment


def validate(spec: Mapping[str, object], workspace: str) -> tuple[list[str], Path, dict[str, str]]:
    """Validate a runner plan without granting execution approval."""
    return _validate_spec(spec, workspace)


def prepare(spec: Mapping[str, object], workspace: str, approval: bool = False) -> tuple[list[str], Path, dict[str, str]]:
    if not approval:
        raise RunnerExecutionDenied("explicit runner approval is required")
    return _validate_spec(spec, workspace)


def execute(spec: Mapping[str, object], workspace: str, approval: bool = False, timeout: float = 120.0, *, allowlisted_hosts=None) -> RunnerOutcome:
    argv, root, environment = prepare(spec, workspace, approval)
    jail = None
    if spec.get("task_execution_class") == "model_task":
        if not allowlisted_hosts:
            raise RunnerExecutionDenied("model_task_requires_allowlisted_hosts")
        from noesis_harness.proxy_jail import AllowlistProxy

        jail = AllowlistProxy(allowlisted_hosts)
        jail.start()
        environment.update(jail.env_overrides())
    try:
        completed = subprocess.run(argv, cwd=root, env=environment, capture_output=True, text=True, timeout=timeout, check=False, shell=False)
    except subprocess.TimeoutExpired as exc:
        outcome = RunnerOutcome("failed", None, _redact(exc.stdout or ""), _redact(exc.stderr or ""), True)
    else:
        outcome = RunnerOutcome("passed" if completed.returncode == 0 else "failed", completed.returncode, _redact(completed.stdout), _redact(completed.stderr), False)
    finally:
        if jail is not None:
            from dataclasses import replace

            outcome = replace(outcome, jail_blocked_hosts=tuple(jail.blocked_hosts), jail_allowed_count=jail.allowed_count)
            jail.stop()
    return outcome


__all__ = ["RunnerConfigurationError", "RunnerExecutionDenied", "RunnerOutcome", "execute", "prepare", "validate"]
