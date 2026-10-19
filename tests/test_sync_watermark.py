"""tests/test_sync_watermark.py

Tests for noesis_harness.sync_watermark (peer-scoped acknowledged sync).

Covers record identity, watermark forward-only movement and persistence,
time-tie boundary handling, export/commit ack gating, import dedupe with
namespaced ids, aggregate imports, and determinism.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from noesis_harness.sync_watermark import (
    DedupeLedger,
    ExportBatch,
    PeerWatermarks,
    SyncExchange,
    export_since,
    imported_id,
    record_identity,
    watermark_key,
)


def _record(harness: str, session_id: str, time: str) -> dict:
    return {"harness": harness, "session_id": session_id, "time": time}


class TestRecordIdentity(unittest.TestCase):
    def test_identity_shape(self) -> None:
        record = {"harness": "h1", "session_id": "s1", "time": "2026-01-01T00:00:00"}
        self.assertEqual(record_identity(record), "h1:s1:2026-01-01T00:00:00")

    def test_identity_missing_fields_are_unknown(self) -> None:
        self.assertEqual(record_identity({"harness": "h1"}), "h1:unknown:unknown")
        self.assertEqual(record_identity({}), "unknown:unknown:unknown")
        self.assertEqual(
            record_identity({"harness": None, "session_id": "s", "time": "t"}),
            "unknown:s:t",
        )

    def test_watermark_key_uses_nul_separator(self) -> None:
        self.assertEqual(watermark_key("peer", "src"), "peer\x00src")
        self.assertNotEqual(watermark_key("a:b", "c"), watermark_key("a", "b:c"))

    def test_imported_id_shape_and_determinism(self) -> None:
        identity = "h1:s1:t1"
        first = imported_id(identity)
        second = imported_id(identity)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("imported-"))
        self.assertEqual(len(first), len("imported-") + 12)
        self.assertNotEqual(imported_id(identity), imported_id("h1:s1:t2"))


class TestExportSince(unittest.TestCase):
    def test_excludes_records_at_or_below_watermark(self) -> None:
        records = [
            _record("h", "s", "2026-01-01T00:00:00"),
            _record("h", "s", "2026-01-02T00:00:00"),
            _record("h", "s", "2026-01-03T00:00:00"),
        ]
        watermark = "2026-01-02T00:00:00"
        selected, _boundary = export_since(records, watermark)
        times = [record["time"] for record in selected]
        self.assertEqual(times, ["2026-01-02T00:00:00", "2026-01-03T00:00:00"])

        acknowledged = [record_identity(records[1])]
        selected_acked, _boundary_acked = export_since(
            records, watermark, boundary=acknowledged
        )
        acked_times = [record["time"] for record in selected_acked]
        self.assertEqual(acked_times, ["2026-01-03T00:00:00"])

    def test_none_watermark_selects_everything(self) -> None:
        records = [
            _record("h", "s", "2026-01-01T00:00:00"),
            _record("h", "s", "2026-01-02T00:00:00"),
        ]
        selected, boundary = export_since(records, None)
        self.assertEqual(len(selected), 2)
        self.assertEqual(boundary, [record_identity(records[1])])

    def test_boundary_tie_included_then_excluded(self) -> None:
        records = [
            _record("h", "s", "2026-01-01T00:00:00"),
            _record("h", "s", "2026-01-02T00:00:00"),
        ]
        watermark = "2026-01-02T00:00:00"
        selected, boundary = export_since(records, watermark)
        self.assertEqual(len(selected), 1)
        self.assertEqual(boundary, [record_identity(records[1])])

        selected_again, _boundary_again = export_since(
            records, watermark, boundary=boundary
        )
        self.assertEqual(selected_again, [])

    def test_boundary_limit_caps_returned_identities(self) -> None:
        records = [
            _record("h", "s%d" % index, "2026-01-01T00:00:00") for index in range(5)
        ]
        _selected, boundary = export_since(
            records, "2026-01-01T00:00:00", boundary_limit=2
        )
        self.assertEqual(len(boundary), 2)


class TestPeerWatermarks(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "watermarks.json")

    def test_advance_and_get(self) -> None:
        watermarks = PeerWatermarks(self.path)
        self.assertIsNone(watermarks.get("p", "s"))
        watermarks.advance("p", "s", "t2")
        self.assertEqual(watermarks.get("p", "s"), "t2")

    def test_forward_only_ignores_smaller_or_equal(self) -> None:
        watermarks = PeerWatermarks(self.path)
        watermarks.advance("p", "s", "t5")
        self.assertIsNone(watermarks.advance("p", "s", "t3"))
        self.assertIsNone(watermarks.advance("p", "s", "t5"))
        self.assertEqual(watermarks.get("p", "s"), "t5")
        watermarks.advance("p", "s", "t9")
        self.assertEqual(watermarks.get("p", "s"), "t9")

    def test_persistence_roundtrip(self) -> None:
        watermarks = PeerWatermarks(self.path)
        watermarks.advance("p1", "s1", "t1")
        watermarks.advance("p2", "s2", "t2")
        watermarks.save()

        reloaded = PeerWatermarks(self.path)
        self.assertEqual(reloaded.get("p1", "s1"), "t1")
        self.assertEqual(reloaded.get("p2", "s2"), "t2")
        self.assertEqual(reloaded.all(), watermarks.all())

    def test_load_tolerates_corrupt_file(self) -> None:
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        watermarks = PeerWatermarks(self.path)
        self.assertEqual(watermarks.all(), {})


class TestDedupeLedger(unittest.TestCase):
    def test_add_returns_newness_and_keys_sorted(self) -> None:
        ledger = DedupeLedger()
        self.assertFalse(ledger.seen("b"))
        self.assertTrue(ledger.add("b"))
        self.assertFalse(ledger.add("b"))
        self.assertTrue(ledger.add("a"))
        self.assertTrue(ledger.seen("b"))
        self.assertEqual(ledger.keys(), ["a", "b"])

    def test_merge_counts_newly_added(self) -> None:
        ledger = DedupeLedger()
        self.assertEqual(ledger.merge(["a", "b", "a"]), 2)
        self.assertEqual(ledger.merge(["b", "c"]), 1)
        self.assertEqual(ledger.keys(), ["a", "b", "c"])


class TestSyncExchange(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "watermarks.json")
        self.watermarks = PeerWatermarks(self.path)
        self.ledger = DedupeLedger()
        self.exchange = SyncExchange(self.watermarks, self.ledger)

    def test_begin_export_does_not_advance(self) -> None:
        records = [_record("h", "s", "2026-01-01T00:00:00")]
        batch = self.exchange.begin_export("peer", "src", records)
        self.assertEqual(batch.cursor, "2026-01-01T00:00:00")
        self.assertEqual(len(batch.records), 1)
        self.assertIsNone(self.watermarks.get("peer", "src"))

    def test_commit_advances_watermark(self) -> None:
        records = [
            _record("h", "s", "2026-01-01T00:00:00"),
            _record("h", "s", "2026-01-02T00:00:00"),
        ]
        batch = self.exchange.begin_export("peer", "src", records)
        self.exchange.commit(batch)
        self.assertEqual(self.watermarks.get("peer", "src"), "2026-01-02T00:00:00")

    def test_re_export_after_commit_yields_no_echo(self) -> None:
        records = [
            _record("h", "s", "2026-01-01T00:00:00"),
            _record("h", "s", "2026-01-02T00:00:00"),
        ]
        batch = self.exchange.begin_export("peer", "src", records)
        self.exchange.commit(batch)
        again = self.exchange.begin_export("peer", "src", records)
        self.assertEqual(again.records, [])

    def test_import_batch_dedupes_duplicates(self) -> None:
        records = [
            _record("h", "s", "2026-01-01T00:00:00"),
            _record("h", "s", "2026-01-02T00:00:00"),
        ]
        batch = ExportBatch(
            peer="peer",
            source="src",
            cursor="2026-01-02T00:00:00",
            records=records,
            boundary=[],
        )
        first = self.exchange.import_batch(batch)
        self.assertEqual(first, {"accepted": 2, "skipped": 0, "cursor": batch.cursor})
        second = self.exchange.import_batch(batch)
        self.assertEqual(second, {"accepted": 0, "skipped": 2, "cursor": batch.cursor})

    def test_import_namespaces_ids(self) -> None:
        record = _record("h", "s", "2026-01-01T00:00:00")
        batch = ExportBatch(
            peer="peer",
            source="src",
            cursor=record["time"],
            records=[record],
            boundary=[],
        )
        self.exchange.import_batch(batch)
        expected = imported_id(record_identity(record))
        self.assertEqual(self.ledger.keys(), [expected])
        self.assertTrue(expected.startswith("imported-"))

    def test_import_advances_watermark_via_commit(self) -> None:
        record = _record("h", "s", "2026-01-01T00:00:00")
        batch = ExportBatch(
            peer="peer",
            source="src",
            cursor=record["time"],
            records=[record],
            boundary=[],
        )
        self.exchange.import_batch(batch)
        self.assertEqual(self.watermarks.get("peer", "src"), record["time"])

    def test_re_export_of_imported_records_no_echo(self) -> None:
        records = [
            _record("h", "s", "2026-01-01T00:00:00"),
            _record("h", "s", "2026-01-02T00:00:00"),
        ]
        outbound = self.exchange.begin_export("peer", "src", records)
        self.exchange.import_batch(outbound)
        round_trip = self.exchange.begin_export("peer", "src", records)
        self.assertEqual(round_trip.records, [])
        self.assertEqual(round_trip.boundary, outbound.boundary)

    def test_import_batches_aggregates(self) -> None:
        batch_one = ExportBatch(
            peer="p1",
            source="s1",
            cursor="t1",
            records=[_record("h", "s1", "t1")],
            boundary=[],
        )
        batch_two = ExportBatch(
            peer="p2",
            source="s2",
            cursor="t2",
            records=[
                _record("h", "s2", "t1"),
                _record("h", "s2", "t2"),
                _record("h", "s1", "t1"),
            ],
            boundary=[],
        )
        result = self.exchange.import_batches([batch_one, batch_two])
        self.assertEqual(result["accepted"], 3)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["cursor"], "t2")

    def test_determinism_across_independent_runs(self) -> None:
        records = [
            _record("h", "s1", "2026-01-01T00:00:00"),
            _record("h", "s2", "2026-01-01T00:00:00"),
            _record("h", "s3", "2026-01-02T00:00:00"),
        ]

        def run() -> tuple:
            with tempfile.TemporaryDirectory() as tmp:
                watermarks = PeerWatermarks(os.path.join(tmp, "wm.json"))
                ledger = DedupeLedger()
                exchange = SyncExchange(watermarks, ledger)
                batch = exchange.begin_export("peer", "src", records)
                exchange.import_batch(batch)
                return batch.cursor, batch.boundary, ledger.keys()

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
