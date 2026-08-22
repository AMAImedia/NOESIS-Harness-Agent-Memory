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


def run_cycle(root: Path, command: Optional[str], timeout: float, state_path: Path, log_path: Path) -> Dict[str, Any]:
    state = read_state(state_path)
    cycle = int(state.get("cycle", 0)) + 1
    started = now()
    interpreter = '"' + sys.executable.replace('"', '') + '"'
    if command:
        selected = command
    elif os.name == "nt":
        smoke = "tests.test_agent_loop tests.test_core tests.test_task_session_api tests.test_turn_checkpoint tests.test_external_identity tests.test_skill_manifest tests.test_skill_runtime tests.test_noesis_autoloop"
        selected = interpreter + " -X tracemalloc=10 -W error::ResourceWarning -m unittest " + smoke + " -q"
    else:
        selected = interpreter + " -X tracemalloc=10 -W error::ResourceWarning -m unittest discover -s tests -p test_*.py -q"
    record = {"schema_version": SCHEMA, "cycle": cycle, "status": "running", "started_at": started, "command": selected, "pid": os.getpid()}
    atomic_write(state_path, record)
    root.joinpath(".noesis_autoloop").mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as log:
        log.write("BEGIN " + canonical(record) + "\n")
        log.flush()
        try:
            completed = subprocess.run(selected, cwd=str(root), shell=True, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            status = "passed" if completed.returncode == 0 else "failed"
            result = {"schema_version": SCHEMA, "cycle": cycle, "status": status, "returncode": completed.returncode, "started_at": started, "finished_at": now(), "command_digest": digest(selected), "pid": os.getpid()}
        except subprocess.TimeoutExpired:
            result = {"schema_version": SCHEMA, "cycle": cycle, "status": "timeout", "started_at": started, "finished_at": now(), "command_digest": digest(selected), "pid": os.getpid()}
        except OSError as exc:
            result = {"schema_version": SCHEMA, "cycle": cycle, "status": "spawn_error", "error": type(exc).__name__, "started_at": started, "finished_at": now(), "command_digest": digest(selected), "pid": os.getpid()}
        log.write("END " + canonical(result) + "\n")
        log.flush()
    atomic_write(state_path, dict(result, heartbeat_at=now()))
    return result


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded unattended NOESIS Harness validation cycles on Windows.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--command", default=os.environ.get("NOESIS_AUTOLOOP_COMMAND"))
    args = parser.parse_args(argv)
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
