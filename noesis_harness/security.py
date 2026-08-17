"""Deterministic security checks and execution contracts for NOESIS.

This module scans untrusted text and creates execution plans; it does not execute
commands or claim that a subprocess is a security sandbox.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class SecurityFinding:
    rule: str
    severity: str
    evidence_digest: str
    message: str


class SecurityScanner:
    RULES = (
        ("prompt_injection", "high", re.compile(r"(?i)(ignore|override|disregard)\s+(all\s+)?(previous|prior|system)\s+instructions")),
        ("exfiltration", "high", re.compile(r"(?i)(send|upload|print|reveal|exfiltrat).{0,80}(token|secret|password|key)")),
        ("api_token", "critical", re.compile(r"(?:hf|sk|ghp|github_pat)_[A-Za-z0-9_-]{12,}")),
        ("aws_key", "critical", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("private_key", "critical", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
        ("invisible_unicode", "high", re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\u2066-\u2069\ufeff]")),
        ("dangerous_eval", "high", re.compile(r"(?i)\b(eval|exec)\s*\(")),
        ("unsafe_deserialization", "high", re.compile(r"(?i)\b(?:pickle\.loads|yaml\.load|marshal\.loads)\s*\(")),
        ("capability_bypass", "high", re.compile(r"(?i)(?:bypass|disable|skip)\s+(?:the\s+)?(?:capability|approval|permission|security)")),
        ("cross_agent_scope_request", "high", re.compile(r"(?i)(?:read|copy|share|expose).{0,60}(?:another|other|all)\s+agent(?:'s|s)?\s+(?:memory|scope|secrets?)")),
        ("shell_secret_access", "high", re.compile(r"(?i)(?:cat|type|grep|find|read).{0,80}(?:\.env|id_rsa|credentials|secret)")),
    )

    def scan(self, text: str) -> List[SecurityFinding]:
        findings=[]
        for rule, severity, pattern in self.RULES:
            match = pattern.search(text or "")
            if match:
                digest = hashlib.sha256(match.group(0).encode("utf-8", "replace")).hexdigest()
                findings.append(SecurityFinding(rule, severity, digest, f"blocked pattern: {rule}"))
        return findings

    def allowed(self, text: str) -> bool:
        return not any(f.severity in ("high", "critical") for f in self.scan(text))


def safe_path(root: str, requested: str) -> Path:
    base = Path(root).expanduser().resolve()
    candidate = (base / requested).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        raise PermissionError("path escapes capability root")
    return candidate


@dataclass(frozen=True)
class ExecutionPlan:
    command: Tuple[str, ...]
    cwd: str
    env_keys: Tuple[str, ...]
    network: bool
    status: str
    reason: str
    sandboxed: bool = False


class LocalExecutionContract:
    """Plans local execution only after explicit policy; never runs the command."""

    def __init__(self, allowed_roots: Sequence[str] = (), allowed_env: Sequence[str] = (), allow_network: bool = False):
        self.allowed_roots = tuple(str(Path(x).expanduser().resolve()) for x in allowed_roots)
        self.allowed_env = set(allowed_env)
        self.allow_network = allow_network

    def plan(self, command: Sequence[str], cwd: str, env_keys: Sequence[str] = (), network: bool = False) -> ExecutionPlan:
        if not command or any(not isinstance(x, str) or not x.strip() for x in command):
            return ExecutionPlan(tuple(command), cwd, tuple(env_keys), network, "denied", "empty_or_invalid_command")
        try:
            workdir = Path(cwd).expanduser().resolve()
            if self.allowed_roots and not any(self._under(workdir, Path(root)) for root in self.allowed_roots):
                return ExecutionPlan(tuple(command), str(workdir), tuple(env_keys), network, "denied", "cwd_outside_allowed_roots")
        except (OSError, ValueError):
            return ExecutionPlan(tuple(command), cwd, tuple(env_keys), network, "denied", "invalid_cwd")
        if network and not self.allow_network:
            return ExecutionPlan(tuple(command), str(workdir), tuple(env_keys), network, "denied", "network_not_granted")
        unknown = sorted(set(env_keys) - self.allowed_env)
        if unknown:
            return ExecutionPlan(tuple(command), str(workdir), tuple(env_keys), network, "denied", "env_not_granted:" + unknown[0])
        return ExecutionPlan(tuple(command), str(workdir), tuple(env_keys), network, "planned", "explicit_capabilities_only", sandboxed=False)

    @staticmethod
    def _under(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False


__all__ = ["SecurityFinding", "SecurityScanner", "safe_path", "ExecutionPlan", "LocalExecutionContract"]
