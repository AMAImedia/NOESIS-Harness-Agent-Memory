"""Unattended NOESIS Harness worker for Windows.

Patterns adapted from NOESIS durable turn checkpoints, runtime supervisor,
agent-teams loop guards, and Hermes bounded turn execution. The worker is
stdlib-only, performs one bounded cycle at a time, persists state atomically,
and never executes an unconfigured arbitrary command by default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from noesis_harness.coding_backend import LocalHTTPCodingBackend

SCHEMA = "noesis.windows-autoloop.v1"
DEFAULT_INTERVAL = 3600.0
DEFAULT_TIMEOUT = 900.0


class WorkerError(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def now() -> float:
    return time.time()


def capability_status(local_endpoint: Optional[str] = None, prompt_file: Optional[str] = None, command: Optional[str] = None) -> Dict[str, Any]:
    """Return the honest boundary between the persistent worker and an agent session."""
    endpoint_configured = isinstance(local_endpoint, str) and bool(local_endpoint.strip())
    prompt_configured = isinstance(prompt_file, str) and bool(prompt_file.strip())
    command_configured = isinstance(command, str) and bool(command.strip())
    proposal_ready = endpoint_configured and prompt_configured
    payload = {
        "schema_version": "noesis.autoloop-capabilities.v1",
        "boundary_version": "protected-actions.v1",
        "worker_persistent": True,
        "worker_modes": ["validation_recovery", "review_only_proposal"] if proposal_ready else ["validation_recovery"],
        "agent_session_continuity": False,
        "autonomous_code_promotion": False,
        "autonomous_protected_admin_mutation": False,
        "arbitrary_command_configured": command_configured,
        "local_endpoint_configured": endpoint_configured,
        "prompt_file_configured": prompt_configured,
        "local_inference_configured": proposal_ready,
        "status": "review_only" if proposal_ready else "validation_only",
        "evidence_claims": ["worker_heartbeat_only", "no_agent_session_continuity", "no_protected_admin_mutation"],
    }
    payload["evidence_digest"] = digest(payload)
    return payload


def atomic_write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def read_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA, "cycle": 0, "status": "new", "last_result": None}
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise WorkerError("state_corrupt") from exc
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA:
        raise WorkerError("state_schema_invalid")
    return value


def acquire_lock(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = open(path, "x", encoding="ascii")
    except FileExistsError:
        try:
            raw = path.read_text(encoding="ascii").strip().split(" ", 1)
            int(raw[0])
            created_at = int(raw[1])
        except (OSError, ValueError, IndexError) as exc:
            raise WorkerError("lock_invalid") from exc
        if now() - created_at < 6 * 60 * 60:
            raise WorkerError("worker_already_running")
        try:
            path.unlink()
        except OSError as exc:
            raise WorkerError("lock_stale_but_unremovable") from exc
        handle = open(path, "x", encoding="ascii")
    with handle:
        handle.write(str(os.getpid()) + " " + str(int(now())) + "\n")
    return os.getpid()


def release_lock(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _durable_log_line(log: Any, value: str) -> None:
    """Append one evidence line and force it to the host before continuing."""
    log.write(value + "\n")
    log.flush()
    os.fsync(log.fileno())


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def read_proposal_queue(path: Path) -> list:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise WorkerError("proposal_queue_corrupt") from exc
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise WorkerError("proposal_queue_invalid")
    return value


def select_proposal_step(queue: list, state: Dict[str, Any]) -> Any:
    index = int(state.get("proposal_step_index", 0))
    if index < 0 or index > len(queue):
        raise WorkerError("proposal_queue_index_invalid")
    return queue[index] if index < len(queue) else None


def claim_proposal_step(state: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    """Claim one proposal step without allowing a live duplicate claim."""
    expires_at = float(state.get("proposal_lease_expires_at", 0.0) or 0.0)
    if state.get("status") == "running" and expires_at > now():
        raise WorkerError("proposal_step_lease_active")
    index = int(state.get("proposal_step_index", 0))
    cycle = int(state.get("cycle", 0))
    started = now()
    lease = {"proposal_step_index": index, "proposal_lease_id": digest({"cycle": cycle, "index": index, "lease_nonce": uuid.uuid4().hex}), "proposal_lease_expires_at": started + max(1.0, float(timeout))}
    return lease


def run_local_proposal_cycle(root: Path, endpoint: str, prompt_path: Path, timeout: float, state_path: Path, log_path: Path, proposal_step: Optional[str] = None, proposal_step_index: Optional[int] = None, lease: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    state = read_state(state_path)
    cycle = int(state.get("cycle", 0)) + 1
    started = now()
    prompt = prompt_path.read_text(encoding="utf-8")
    if proposal_step is not None:
        prompt += "\n\nNext bounded review-only step:\n" + proposal_step
    backend = LocalHTTPCodingBackend(endpoint, prompt, timeout_seconds=timeout)
    running = {"schema_version": SCHEMA, "cycle": cycle, "status": "running", "mode": "review_only_proposal", "started_at": started, "request_digest": backend.request_digest, "pid": os.getpid()}
    if lease:
        running.update(lease)
        running["proposal_lease_state"] = "claimed"
    atomic_write(state_path, running)
    try:
        result = backend.run()
        artifact = root / ".noesis_autoloop" / "artifacts" / ("cycle-%06d.response.txt" % cycle)
        if result.status == "passed":
            _atomic_text(artifact, result.stdout)
        final = {"schema_version": SCHEMA, "cycle": cycle, "status": result.status, "mode": "review_only_proposal", "reason": result.reason, "request_digest": result.command_digest, "artifact": str(artifact.relative_to(root)) if result.status == "passed" else None, "started_at": started, "finished_at": now(), "pid": os.getpid()}
        if proposal_step_index is not None:
            final["proposal_step_index"] = proposal_step_index + (1 if result.status == "passed" else 0)
        if lease:
            final["proposal_lease_id"] = lease["proposal_lease_id"]
            final["proposal_lease_state"] = "released"
    except (OSError, UnicodeError) as exc:
        final = {"schema_version": SCHEMA, "cycle": cycle, "status": "failed", "mode": "review_only_proposal", "reason": type(exc).__name__, "request_digest": backend.request_digest, "started_at": started, "finished_at": now(), "pid": os.getpid()}
    with log_path.open("a", encoding="utf-8", newline="\n") as log:
        _durable_log_line(log, "END " + canonical(final))
    atomic_write(state_path, dict(final, heartbeat_at=now()))
    return final


def run_cycle(root: Path, command: Optional[str], timeout: float, state_path: Path, log_path: Path) -> Dict[str, Any]:
    state = read_state(state_path)
    cycle = int(state.get("cycle", 0)) + 1
    previous_cycle = int(state.get("cycle", 0))
    recovered_previous_cycle = previous_cycle if state.get("status") == "running" and previous_cycle > 0 else None
    recovery_digest = digest({"cycle": previous_cycle, "status": "running"}) if recovered_previous_cycle is not None else None
    started = now()
    interpreter = '"' + sys.executable.replace('"', '') + '"'
    if command:
        selected = command
    elif os.name == "nt":
        smoke = "tests.test_agent_loop tests.test_core tests.test_task_session_api tests.test_turn_checkpoint tests.test_external_identity tests.test_skill_manifest tests.test_skill_runtime tests.test_noesis_autoloop tests.test_admin_state_sqlite"
        selected = interpreter + " -X tracemalloc=10 -W error::ResourceWarning -m unittest " + smoke + " -q"
    else:
        selected = interpreter + " -X tracemalloc=10 -W error::ResourceWarning -m unittest discover -s tests -p test_*.py -q"
    record = {"schema_version": SCHEMA, "cycle": cycle, "status": "running", "started_at": started, "command_digest": digest(selected), "command_configured": bool(command), "pid": os.getpid()}
    if recovered_previous_cycle is not None:
        record["recovered_previous_cycle"] = recovered_previous_cycle
        record["recovery_digest"] = recovery_digest
    atomic_write(state_path, record)
    root.joinpath(".noesis_autoloop").mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as log:
        _durable_log_line(log, "BEGIN " + canonical(record))
        try:
            completed = subprocess.run(selected, cwd=str(root), shell=True, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            status = "passed" if completed.returncode == 0 else "failed"
            result = {"schema_version": SCHEMA, "cycle": cycle, "status": status, "returncode": completed.returncode, "started_at": started, "finished_at": now(), "command_digest": digest(selected), "pid": os.getpid()}
            if recovered_previous_cycle is not None:
                result["recovered_previous_cycle"] = recovered_previous_cycle
                result["recovery_digest"] = recovery_digest
        except subprocess.TimeoutExpired:
            result = {"schema_version": SCHEMA, "cycle": cycle, "status": "timeout", "started_at": started, "finished_at": now(), "command_digest": digest(selected), "pid": os.getpid()}
            if recovered_previous_cycle is not None:
                result["recovered_previous_cycle"] = recovered_previous_cycle
                result["recovery_digest"] = recovery_digest
        except OSError as exc:
            result = {"schema_version": SCHEMA, "cycle": cycle, "status": "spawn_error", "error": type(exc).__name__, "started_at": started, "finished_at": now(), "command_digest": digest(selected), "pid": os.getpid()}
            if recovered_previous_cycle is not None:
                result["recovered_previous_cycle"] = recovered_previous_cycle
                result["recovery_digest"] = recovery_digest
        _durable_log_line(log, "END " + canonical(result))
    atomic_write(state_path, dict(result, heartbeat_at=now()))
    return result


def read_handoff(path: Path) -> Dict[str, Any]:
    """Read a strict, secret-free handoff manifest for a fresh session."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise WorkerError("handoff_corrupt") from exc
    required = {"schema_version", "source_cycle", "source_status", "source_result_digest", "next_action", "allowed", "forbidden", "created_at"}
    if not isinstance(value, dict) or set(value) != required:
        raise WorkerError("handoff_schema_invalid")
    if value["schema_version"] != "noesis.autoloop-handoff.v1":
        raise WorkerError("handoff_schema_invalid")
    if not isinstance(value["source_cycle"], int) or value["source_cycle"] < 0:
        raise WorkerError("handoff_cycle_invalid")
    if not isinstance(value["source_result_digest"], str) or len(value["source_result_digest"]) != 64:
        raise WorkerError("handoff_digest_invalid")
    if not isinstance(value["allowed"], list) or not isinstance(value["forbidden"], list):
        raise WorkerError("handoff_policy_invalid")
    return value


def write_handoff(root: Path, result: Dict[str, Any]) -> None:
    """Publish a secret-free handoff for the next bounded agent session."""
    payload = {
        "schema_version": "noesis.autoloop-handoff.v1",
        "source_cycle": result.get("cycle"),
        "source_status": result.get("status"),
        "source_result_digest": digest(result),
        "next_action": "inspect_state_then_take_one_bounded_safe_increment",
        "allowed": ["stdlib_code", "tests", "en_ru_docs", "private_github_sync"],
        "forbidden": ["protected_admin_mutation", "promotion", "generated_code_execution", "credential_changes"],
        "created_at": now(),
    }
    atomic_write(root / ".noesis_autoloop" / "handoff.json", payload)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded unattended NOESIS Harness validation cycles on Windows.")
    parser.add_argument("--root", default=str(PROJECT_ROOT))
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--status", action="store_true", help="Print the persistent-worker capability boundary and exit.")
    parser.add_argument("--command", default=os.environ.get("NOESIS_AUTOLOOP_COMMAND"))
    parser.add_argument("--local-endpoint", default=os.environ.get("NOESIS_AUTOLOOP_LOCAL_ENDPOINT"))
    parser.add_argument("--prompt-file", default=os.environ.get("NOESIS_AUTOLOOP_PROMPT_FILE"))
    parser.add_argument("--steps-file", default=os.environ.get("NOESIS_AUTOLOOP_STEPS_FILE"), help="Optional JSON array of bounded review-only proposal steps.")
    args = parser.parse_args(argv)
    if args.status:
        print(canonical(capability_status(args.local_endpoint, args.prompt_file, args.command)))
        return 0
    root = Path(args.root).resolve()
    state_path = root / ".noesis_autoloop" / "state.json"
    lock_path = root / ".noesis_autoloop" / "worker.lock"
    log_path = root / ".noesis_autoloop" / "worker.log"
    try:
        acquire_lock(lock_path)
    except WorkerError as exc:
        print("NOESIS worker blocked: " + str(exc), file=sys.stderr)
        return 2
    try:
        while True:
            if args.local_endpoint and args.prompt_file:
                proposal_step = None
                proposal_step_index = None
                if args.steps_file:
                    queue = read_proposal_queue(Path(args.steps_file).resolve())
                    current_state = read_state(state_path)
                    proposal_step_index = int(current_state.get("proposal_step_index", 0))
                    proposal_step = select_proposal_step(queue, current_state)
                    lease = claim_proposal_step(current_state, max(1.0, args.timeout)) if proposal_step is not None else {}
                    if proposal_step is None:
                        result = {"schema_version": SCHEMA, "cycle": int(current_state.get("cycle", 0)), "status": "idle", "mode": "review_only_proposal", "reason": "proposal_queue_exhausted", "proposal_step_index": proposal_step_index, "proposal_lease_state": "exhausted"}
                        atomic_write(state_path, dict(result, heartbeat_at=now()))
                    else:
                        result = run_local_proposal_cycle(root, args.local_endpoint, Path(args.prompt_file).resolve(), max(1.0, args.timeout), state_path, log_path, proposal_step, proposal_step_index, lease)
                else:
                    result = run_local_proposal_cycle(root, args.local_endpoint, Path(args.prompt_file).resolve(), max(1.0, args.timeout), state_path, log_path)
            else:
                result = run_cycle(root, args.command, max(1.0, args.timeout), state_path, log_path)
            write_handoff(root, result)
            print(canonical(result), flush=True)
            if args.once:
                return 0 if result.get("status") == "passed" else 1
            time.sleep(max(5.0, args.interval))
    except KeyboardInterrupt:
        return 130
    except WorkerError as exc:
        atomic_write(state_path, {"schema_version": SCHEMA, "status": "blocked", "reason": str(exc), "heartbeat_at": now()})
        print("NOESIS worker blocked: " + str(exc), file=sys.stderr)
        return 3
    finally:
        release_lock(lock_path)


if __name__ == "__main__":
    raise SystemExit(main())
