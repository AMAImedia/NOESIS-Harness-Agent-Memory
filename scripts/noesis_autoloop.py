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


def run_local_proposal_cycle(root: Path, endpoint: str, prompt_path: Path, timeout: float, state_path: Path, log_path: Path) -> Dict[str, Any]:
    state = read_state(state_path)
    cycle = int(state.get("cycle", 0)) + 1
    started = now()
    prompt = prompt_path.read_text(encoding="utf-8")
    backend = LocalHTTPCodingBackend(endpoint, prompt, timeout_seconds=timeout)
    running = {"schema_version": SCHEMA, "cycle": cycle, "status": "running", "mode": "review_only_proposal", "started_at": started, "request_digest": backend.request_digest, "pid": os.getpid()}
    atomic_write(state_path, running)
    try:
        result = backend.run()
        artifact = root / ".noesis_autoloop" / "artifacts" / ("cycle-%06d.response.txt" % cycle)
        if result.status == "passed":
            _atomic_text(artifact, result.stdout)
        final = {"schema_version": SCHEMA, "cycle": cycle, "status": result.status, "mode": "review_only_proposal", "reason": result.reason, "request_digest": result.command_digest, "artifact": str(artifact.relative_to(root)) if result.status == "passed" else None, "started_at": started, "finished_at": now(), "pid": os.getpid()}
    except (OSError, UnicodeError) as exc:
        final = {"schema_version": SCHEMA, "cycle": cycle, "status": "failed", "mode": "review_only_proposal", "reason": type(exc).__name__, "request_digest": backend.request_digest, "started_at": started, "finished_at": now(), "pid": os.getpid()}
    with log_path.open("a", encoding="utf-8", newline="\n") as log:
        log.write("END " + canonical(final) + "\n")
        log.flush()
    atomic_write(state_path, dict(final, heartbeat_at=now()))
    return final


def run_cycle(root: Path, command: Optional[str], timeout: float, state_path: Path, log_path: Path) -> Dict[str, Any]:
    state = read_state(state_path)
    cycle = int(state.get("cycle", 0)) + 1
    previous_cycle = int(state.get("cycle", 0))
    recovered_previous_cycle = previous_cycle if state.get("status") == "running" else None
    started = now()
    interpreter = '"' + sys.executable.replace('"', '') + '"'
    if command:
        selected = command
    elif os.name == "nt":
        smoke = "tests.test_agent_loop tests.test_core tests.test_task_session_api tests.test_turn_checkpoint tests.test_external_identity tests.test_skill_manifest tests.test_skill_runtime tests.test_noesis_autoloop tests.test_admin_state_sqlite"
        selected = interpreter + " -X tracemalloc=10 -W error::ResourceWarning -m unittest " + smoke + " -q"
    else:
        selected = interpreter + " -X tracemalloc=10 -W error::ResourceWarning -m unittest discover -s tests -p test_*.py -q"
    record = {"schema_version": SCHEMA, "cycle": cycle, "status": "running", "started_at": started, "command": selected, "pid": os.getpid()}
    if recovered_previous_cycle is not None:
        record["recovered_previous_cycle"] = recovered_previous_cycle
    atomic_write(state_path, record)
    root.joinpath(".noesis_autoloop").mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as log:
        log.write("BEGIN " + canonical(record) + "\n")
        log.flush()
        try:
            completed = subprocess.run(selected, cwd=str(root), shell=True, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            status = "passed" if completed.returncode == 0 else "failed"
            result = {"schema_version": SCHEMA, "cycle": cycle, "status": status, "returncode": completed.returncode, "started_at": started, "finished_at": now(), "command_digest": digest(selected), "pid": os.getpid()}
            if recovered_previous_cycle is not None:
                result["recovered_previous_cycle"] = recovered_previous_cycle
        except subprocess.TimeoutExpired:
            result = {"schema_version": SCHEMA, "cycle": cycle, "status": "timeout", "started_at": started, "finished_at": now(), "command_digest": digest(selected), "pid": os.getpid()}
            if recovered_previous_cycle is not None:
                result["recovered_previous_cycle"] = recovered_previous_cycle
        except OSError as exc:
            result = {"schema_version": SCHEMA, "cycle": cycle, "status": "spawn_error", "error": type(exc).__name__, "started_at": started, "finished_at": now(), "command_digest": digest(selected), "pid": os.getpid()}
            if recovered_previous_cycle is not None:
                result["recovered_previous_cycle"] = recovered_previous_cycle
        log.write("END " + canonical(result) + "\n")
        log.flush()
    atomic_write(state_path, dict(result, heartbeat_at=now()))
    return result


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
                result = run_local_proposal_cycle(root, args.local_endpoint, Path(args.prompt_file).resolve(), max(1.0, args.timeout), state_path, log_path)
            else:
                result = run_cycle(root, args.command, max(1.0, args.timeout), state_path, log_path)
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
