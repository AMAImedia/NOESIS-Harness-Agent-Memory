"""tests/test_extraction_queue.py

Unit tests for noesis_harness.extraction_queue.

Stdlib-only (unittest). Covers the single-writer claim, the throttle counter,
the single-slot trailing queue and the ExtractionWorker run loop, including
claim failure, trailing drain and release-on-exception behaviour.
"""

import unittest

from noesis_harness.extraction_queue import ExtractionCoordinator, ExtractionWorker


class TestExtractionCoordinator(unittest.TestCase):
    def test_claim_succeeds_when_free(self):
        coordinator = ExtractionCoordinator()
        self.assertTrue(coordinator.try_claim("s1"))
        self.assertTrue(coordinator.is_claimed("s1"))

    def test_second_claim_fails_while_held(self):
        coordinator = ExtractionCoordinator()
        self.assertTrue(coordinator.try_claim("s1"))
        self.assertFalse(coordinator.try_claim("s1"))

    def test_release_then_claim(self):
        coordinator = ExtractionCoordinator()
        self.assertTrue(coordinator.try_claim("s1"))
        self.assertTrue(coordinator.release("s1"))
        self.assertFalse(coordinator.is_claimed("s1"))
        self.assertTrue(coordinator.try_claim("s1"))

    def test_release_returns_false_when_not_claimed(self):
        coordinator = ExtractionCoordinator()
        self.assertFalse(coordinator.release("s1"))

    def test_throttle_blocks_too_soon_claim(self):
        coordinator = ExtractionCoordinator(throttle=5)
        coordinator.note_turn("s1")
        self.assertTrue(coordinator.try_claim("s1"))
        coordinator.record_extraction("s1")
        self.assertTrue(coordinator.release("s1"))
        self.assertFalse(coordinator.try_claim("s1"))

    def test_throttle_elapses_after_record_and_note_turn(self):
        coordinator = ExtractionCoordinator(throttle=2)
        coordinator.note_turn("s1")
        self.assertTrue(coordinator.try_claim("s1"))
        coordinator.record_extraction("s1")
        coordinator.release("s1")
        coordinator.note_turn("s1")
        self.assertFalse(coordinator.try_claim("s1"))
        coordinator.note_turn("s1")
        self.assertTrue(coordinator.try_claim("s1"))

    def test_note_turn_returns_running_counter(self):
        coordinator = ExtractionCoordinator()
        self.assertEqual(coordinator.note_turn("s1"), 1)
        self.assertEqual(coordinator.note_turn("s1"), 2)
        self.assertEqual(coordinator.note_turn("s2"), 1)

    def test_enqueue_replaces_previous_trailing(self):
        coordinator = ExtractionCoordinator()
        coordinator.enqueue_trailing("s1", "first")
        coordinator.enqueue_trailing("s1", "second")
        self.assertEqual(coordinator.stats("s1")["trailing"], True)
        self.assertEqual(coordinator.drain_trailing("s1"), "second")

    def test_drain_returns_payload_and_clears(self):
        coordinator = ExtractionCoordinator()
        coordinator.enqueue_trailing("s1", {"cue": 7})
        self.assertEqual(coordinator.drain_trailing("s1"), {"cue": 7})
        self.assertIsNone(coordinator.drain_trailing("s1"))
        self.assertEqual(coordinator.stats("s1")["trailing"], False)

    def test_drain_none_when_empty(self):
        coordinator = ExtractionCoordinator()
        self.assertIsNone(coordinator.drain_trailing("missing"))

    def test_is_claimed_tracks_claim_lifecycle(self):
        coordinator = ExtractionCoordinator()
        self.assertFalse(coordinator.is_claimed("s1"))
        coordinator.try_claim("s1")
        self.assertTrue(coordinator.is_claimed("s1"))
        coordinator.release("s1")
        self.assertFalse(coordinator.is_claimed("s1"))

    def test_pending_sorted(self):
        coordinator = ExtractionCoordinator()
        coordinator.enqueue_trailing("zeta", 1)
        coordinator.enqueue_trailing("alpha", 2)
        coordinator.enqueue_trailing("mu", 3)
        self.assertEqual(coordinator.pending(), ["alpha", "mu", "zeta"])

    def test_pending_empty_after_drain(self):
        coordinator = ExtractionCoordinator()
        coordinator.enqueue_trailing("s1", 1)
        coordinator.enqueue_trailing("s2", 2)
        coordinator.drain_trailing("s1")
        self.assertEqual(coordinator.pending(), ["s2"])

    def test_stats_fields(self):
        coordinator = ExtractionCoordinator()
        coordinator.note_turn("s1")
        coordinator.enqueue_trailing("s1", "x")
        before = coordinator.stats("s1")
        self.assertEqual(
            sorted(before.keys()), ["claimed", "extractions", "trailing", "turns"]
        )
        self.assertEqual(before["turns"], 1)
        self.assertEqual(before["extractions"], 0)
        self.assertEqual(before["claimed"], False)
        self.assertEqual(before["trailing"], True)
        coordinator.try_claim("s1")
        coordinator.record_extraction("s1")
        after = coordinator.stats("s1")
        self.assertEqual(after["extractions"], 1)
        self.assertEqual(after["claimed"], True)

    def test_invalid_throttle_raises(self):
        with self.assertRaises(ValueError):
            ExtractionCoordinator(throttle=0)
        with self.assertRaises(ValueError):
            ExtractionCoordinator(throttle=-3)


class TestExtractionWorker(unittest.TestCase):
    def _recording_extractor(self, calls):
        def extract(session_id, payload):
            calls.append((session_id, payload))
            return "ok"

        return extract

    def test_worker_processes_and_drains_trailing(self):
        coordinator = ExtractionCoordinator()
        calls = []
        worker = ExtractionWorker(coordinator, self._recording_extractor(calls))
        coordinator.enqueue_trailing("s1", "trailing")
        result = worker.run("s1", "primary")
        self.assertEqual(result, {"processed": 2, "trailing_remaining": False})
        self.assertEqual(calls, [("s1", "primary"), ("s1", "trailing")])
        self.assertEqual(coordinator.stats("s1")["extractions"], 2)
        self.assertFalse(coordinator.is_claimed("s1"))

    def test_worker_processes_without_trailing(self):
        coordinator = ExtractionCoordinator()
        calls = []
        worker = ExtractionWorker(coordinator, self._recording_extractor(calls))
        result = worker.run("s1", "primary")
        self.assertEqual(result, {"processed": 1, "trailing_remaining": False})
        self.assertEqual(calls, [("s1", "primary")])

    def test_worker_enqueues_when_claim_held(self):
        coordinator = ExtractionCoordinator()
        calls = []
        worker = ExtractionWorker(coordinator, self._recording_extractor(calls))
        self.assertTrue(coordinator.try_claim("s1"))
        result = worker.run("s1", "deferred")
        self.assertEqual(result, {"processed": 0, "trailing_remaining": True})
        self.assertEqual(calls, [])
        self.assertEqual(coordinator.pending(), ["s1"])
        self.assertEqual(coordinator.drain_trailing("s1"), "deferred")

    def test_worker_releases_claim_on_exception(self):
        coordinator = ExtractionCoordinator()

        def boom(session_id, payload):
            raise RuntimeError("extract failed")

        worker = ExtractionWorker(coordinator, boom)
        with self.assertRaises(RuntimeError):
            worker.run("s1", "primary")
        self.assertFalse(coordinator.is_claimed("s1"))
        self.assertTrue(coordinator.try_claim("s1"))

    def test_worker_does_not_record_failed_extraction(self):
        coordinator = ExtractionCoordinator()

        def boom(session_id, payload):
            raise ValueError("nope")

        worker = ExtractionWorker(coordinator, boom)
        with self.assertRaises(ValueError):
            worker.run("s1", "primary")
        self.assertEqual(coordinator.stats("s1")["extractions"], 0)


class TestDeterminism(unittest.TestCase):
    def _sequence(self, coordinator):
        worker_calls = []

        def extract(session_id, payload):
            worker_calls.append((session_id, payload))
            return payload

        worker = ExtractionWorker(coordinator, extract)
        coordinator.note_turn("s2")
        coordinator.note_turn("s1")
        results = [
            worker.run("s1", "a"),
            worker.run("s2", "b"),
            worker.run("s1", "c"),
        ]
        return results, coordinator.stats("s1"), coordinator.stats("s2"), coordinator.pending()

    def test_identical_sequences_yield_identical_state(self):
        first = self._sequence(ExtractionCoordinator(throttle=2))
        second = self._sequence(ExtractionCoordinator(throttle=2))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
