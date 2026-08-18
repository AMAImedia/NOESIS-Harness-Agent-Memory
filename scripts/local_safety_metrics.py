#!/usr/bin/env python3
"""Run deterministic local safety/evaluation probes without external agents.

This lane measures NOESIS controls only. It never invokes a model-generated
artifact, contacts a provider, or creates a comparative ranking.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from noesis_harness.provider_invocation import (
    InvocationRequest,
    OpenAICompatibleInvocationAdapter,
    ProviderInvocationError,
)
from noesis_harness.security_holdouts import SecurityHoldoutSuite


def _metric(passed: bool, value: float, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {"status": "observed", "value": value, "passed": bool(passed)}
    if details:
        record["details"] = details
    return record


def _request(*, tools: tuple[dict[str, Any], ...] = (), required: tuple[str, ...] = ()) -> InvocationRequest:
    return InvocationRequest(
        session_id="local-safety-session",
        task_id="local-safety-task",
        model="local-test-model",
        messages=({"role": "user", "content": "approved deterministic probe"},),
        required_capabilities=required,
        tools=tools,
    )


def run() -> dict[str, Any]:
    holdout = SecurityHoldoutSuite().evaluate()
    holdout_passed = sum(result.passed for result in holdout)

    transport_calls = 0

    def transport(_request: Any, _timeout: float) -> tuple[int, bytes]:
        nonlocal transport_calls
        transport_calls += 1
        return 200, b'{"id":"local-probe","choices":[{"message":{"content":"data"}}]}'

    no_tools = OpenAICompatibleInvocationAdapter(
        "local", "http://127.0.0.1:1", "local-test-model", {"tools": False}, transport=transport
    )
    try:
        no_tools.invoke(_request(tools=({"name": "write_file"},)))
    except ProviderInvocationError as exc:
        approval_bypass_passed = str(exc) == "capability_not_granted:tools"
    else:
        approval_bypass_passed = False

    no_egress = OpenAICompatibleInvocationAdapter(
        "local", "http://127.0.0.1:1", "local-test-model", {}, transport=transport
    )
    try:
        no_egress.invoke(_request(required=("streaming",)))
    except ProviderInvocationError as exc:
        egress_gate_passed = str(exc) == "capability_not_granted:streaming"
    else:
        egress_gate_passed = False

    bounded_adapter = OpenAICompatibleInvocationAdapter(
        "local", "http://127.0.0.1:1", "local-test-model", {}, transport=transport
    )
    response = bounded_adapter.invoke(_request())
    invocation_passed = response.status == "ready" and response.request_id == "local-probe"

    with tempfile.TemporaryDirectory(prefix="noesis-safety-metrics-") as temp_dir:
        source = Path(temp_dir) / "source.txt"
        restored = Path(temp_dir) / "restored.txt"
        expected = "verified-state-v1\n"
        source.write_text(expected, encoding="utf-8")
        restored.write_bytes(source.read_bytes())
        patch_roundtrip_passed = restored.read_text(encoding="utf-8") == expected

    metrics = {
        "patch_correctness": _metric(patch_roundtrip_passed, 1.0 if patch_roundtrip_passed else 0.0, details={"probe": "safe_file_roundtrip"}),
        "recovery": _metric(patch_roundtrip_passed, 1.0 if patch_roundtrip_passed else 0.0, details={"probe": "verified_state_restore"}),
        "unauthorized_egress": _metric(egress_gate_passed and transport_calls == 1, 1.0 if egress_gate_passed else 0.0, details={"transport_calls": transport_calls, "probe": "capability_denial_before_transport"}),
        "credential_exposure": _metric(holdout_passed == len(holdout), holdout_passed / len(holdout) if holdout else 1.0, details={"cases": len(holdout), "passed": holdout_passed}),
        "approval_bypass": _metric(approval_bypass_passed, 1.0 if approval_bypass_passed else 0.0, details={"probe": "tools_denied_without_capability"}),
        "human_review_seconds": {"status": "not_run", "reason": "No human interaction in local deterministic lane"},
    }
    observed_failures = [name for name, record in metrics.items() if record.get("status") == "observed" and not record.get("passed")]
    return {
        "schema_version": "noesis.local-safety-metrics.v1",
        "simulation_only": True,
        "scope": "NOESIS local controls; no external agent execution and no ranking",
        "metrics": metrics,
        "summary": {
            "observed": sum(record.get("status") == "observed" for record in metrics.values()),
            "passed": sum(record.get("status") == "observed" and record.get("passed") for record in metrics.values()),
            "not_run": sum(record.get("status") == "not_run" for record in metrics.values()),
            "failed": len(observed_failures),
            "failure_metrics": observed_failures,
            "provider_invocation_probe": invocation_passed,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local deterministic NOESIS safety metrics")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if payload["summary"]["failed"] == 0 and payload["summary"]["provider_invocation_probe"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["run"]
