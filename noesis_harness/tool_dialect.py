"""Per-harness tool dialect table treated as data, not code.

Patterns borrowed from:
- deja-vu (Go): the tool dialect table in ``internal/sources/util.go`` plus the
  Copilot and Qwen source adapters (``internal/sources/copilot.go``,
  ``internal/sources/qwen.go``). Each coding harness names the same conceptual
  tool arguments differently (for example Claude uses ``file_path`` and
  ``Bash``, while Cursor uses ``path`` and ``Shell``). Rather than branching on
  the harness in code, the mapping is expressed as a frozen table that is
  looked up at runtime.

This module is pure and stdlib-only: it has no I/O, no state, and no LLM
calls. Every function is deterministic for a given input, and the dialect
lookup is case-insensitive and fails soft to the default dialect rather than
raising.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

__all__ = [
    "ToolDialect",
    "DIALECTS",
    "DEFAULT_DIALECT_NAME",
    "CANONICAL_KEYS",
    "dialect_for",
    "normalize_tool_args",
    "denormalize_tool_args",
    "dialects",
    "tool_name_for",
]


@dataclass(frozen=True)
class ToolDialect:
    """Naming contract a single harness uses for shared tool arguments.

    Attributes:
        name: Canonical lower-case dialect identifier.
        path_key: Argument name for a filesystem path.
        shell_tool: Tool name that runs a shell command.
        old_string_key: Argument name for the search side of a text edit.
        command_key: Argument name for the command string.
    """

    name: str
    path_key: str
    shell_tool: str
    old_string_key: str
    command_key: str


DIALECTS: Dict[str, ToolDialect] = {
    "claude": ToolDialect(
        name="claude",
        path_key="file_path",
        shell_tool="Bash",
        old_string_key="old_string",
        command_key="command",
    ),
    "cursor": ToolDialect(
        name="cursor",
        path_key="path",
        shell_tool="Shell",
        old_string_key="old_str",
        command_key="command",
    ),
    "copilot": ToolDialect(
        name="copilot",
        path_key="file_path",
        shell_tool="shell",
        old_string_key="old_str",
        command_key="command",
    ),
    "codex": ToolDialect(
        name="codex",
        path_key="path",
        shell_tool="shell",
        old_string_key="old_string",
        command_key="cmd",
    ),
    "qwen": ToolDialect(
        name="qwen",
        path_key="file_path",
        shell_tool="Bash",
        old_string_key="old_string",
        command_key="command",
    ),
}

DEFAULT_DIALECT_NAME = "claude"

CANONICAL_KEYS = ("path", "old_string", "command")


def dialect_for(name: str) -> ToolDialect:
    """Return the dialect for ``name``, falling back to the default.

    The lookup is case-insensitive. Unknown, empty, or non-string names do
    not raise; they resolve to ``DIALECTS[DEFAULT_DIALECT_NAME]``.
    """
    key = name.lower() if isinstance(name, str) else ""
    return DIALECTS.get(key, DIALECTS[DEFAULT_DIALECT_NAME])


def _ordered(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Return ``mapping`` ordered canonical keys first, then sorted rest."""
    out: Dict[str, Any] = {}
    for key in CANONICAL_KEYS:
        if key in mapping:
            out[key] = mapping[key]
    for key in sorted(k for k in mapping if k not in CANONICAL_KEYS):
        out[key] = mapping[key]
    return out


def normalize_tool_args(harness: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Rewrite a harness's tool arguments into canonical key names.

    Maps the dialect's ``path_key`` to ``"path"``, ``old_string_key`` to
    ``"old_string"`` and ``command_key`` to ``"command"``. Keys that are not
    part of the dialect are preserved unchanged. The input is never mutated.
    The returned dict is deterministic: canonical keys appear first in
    ``CANONICAL_KEYS`` order, then any remaining keys sorted alphabetically.
    """
    dialect = dialect_for(harness)
    key_map = {
        dialect.path_key: "path",
        dialect.old_string_key: "old_string",
        dialect.command_key: "command",
    }
    translated: Dict[str, Any] = {}
    for key in sorted(args):
        translated[key_map.get(key, key)] = args[key]
    return _ordered(translated)


def denormalize_tool_args(harness: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Rewrite canonical tool arguments back into a harness's key names.

    This is the inverse of :func:`normalize_tool_args` for the three
    canonical keys only. Other keys are preserved unchanged and the input is
    never mutated. The returned dict is deterministic for a given input.
    """
    dialect = dialect_for(harness)
    key_map = {
        "path": dialect.path_key,
        "old_string": dialect.old_string_key,
        "command": dialect.command_key,
    }
    translated: Dict[str, Any] = {}
    for key in sorted(args):
        translated[key_map.get(key, key)] = args[key]
    return translated


def dialects() -> List[str]:
    """Return all known dialect names sorted alphabetically."""
    return sorted(DIALECTS.keys())


def tool_name_for(harness: str, canonical: str) -> str:
    """Return the harness's name for a canonical tool name.

    The canonical name ``"shell"`` maps to the dialect's ``shell_tool``. Any
    other name is returned unchanged.
    """
    if canonical == "shell":
        return dialect_for(harness).shell_tool
    return canonical
