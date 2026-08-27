import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from noesis_harness.event_store import EventStore
from noesis_harness.schema_cli import build_inventory, main


def _write_log(path: Path, records):
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


class SchemaCliTests(unittest.TestCase):
    def test_empty_log_json_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            inventory = build_inventory(EventStore(str(log)).iter_events())
            self.assertEqual(inventory, {})
            self.assertIsInstance(inventory, dict)

    def test_type_inventory_groups_by_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            _write_log(log, [
                {"event_id": "a1", "type": "agent_registered", "payload": {"agent_id": "x", "role": "w"}, "seq": 1},
                {"event_id": "a2", "type": "agent_registered", "payload": {"agent_id": "y"}, "seq": 2},
                {"event_id": "a3", "type": "task_claimed", "payload": {"task_id": "t", "agent_id": "x"}, "seq": 3},
            ])
            inventory = build_inventory(EventStore(str(log)).iter_events())
            self.assertIn("agent_registered", inventory)
            self.assertIn("task_claimed", inventory)
            self.assertEqual(set(inventory["agent_registered"]), {"agent_id", "role"})

    def test_field_keys_union_and_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            _write_log(log, [
                {"event_id": "b1", "type": "evt", "payload": {"zeta": 1, "alpha": 2}, "seq": 1},
                {"event_id": "b2", "type": "evt", "payload": {"mid": 3}, "seq": 2},
            ])
            keys = build_inventory(EventStore(str(log)).iter_events())["evt"]
            self.assertEqual(keys, ["alpha", "mid", "zeta"])

    def test_cli_json_output_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            _write_log(log, [
                {"event_id": "c1", "type": "ping", "payload": {"value": 1}, "seq": 1},
            ])
            rc = main(["--events", str(log), "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(_capture_stdout(lambda: main(["--events", str(log), "--json"])))
            self.assertEqual(parsed, {"ping": ["value"]})

    def test_cli_text_output_lists_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            _write_log(log, [
                {"event_id": "d1", "type": "alpha", "payload": {"k": 1}, "seq": 1},
                {"event_id": "d2", "type": "beta", "payload": {"j": 2}, "seq": 2},
            ])
            out = _capture_stdout(lambda: main(["--events", str(log)]))
            self.assertIn("alpha:", out)
            self.assertIn("beta:", out)
            self.assertIn("k", out)

    def test_empty_log_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            rc = main(["--events", str(log), "--json"])
            self.assertEqual(rc, 0)
            out = _capture_stdout(lambda: main(["--events", str(log), "--json"]))
            self.assertEqual(json.loads(out), {})

    def test_read_only_does_not_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            _write_log(log, [
                {"event_id": "e1", "type": "note", "payload": {"x": 1}, "seq": 1},
            ])
            before = log.read_text(encoding="utf-8")
            main(["--events", str(log), "--json"])
            after = log.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_subprocess_invocation_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "events.jsonl"
            _write_log(log, [
                {"event_id": "f1", "type": "evt", "payload": {"a": 1, "b": 2}, "seq": 1},
            ])
            proc = subprocess.run(
                [sys.executable, "-m", "noesis_harness.schema_cli", "--events", str(log), "--json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(json.loads(proc.stdout), {"evt": ["a", "b"]})


def _capture_stdout(fn):
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue()


if __name__ == "__main__":
    unittest.main()
