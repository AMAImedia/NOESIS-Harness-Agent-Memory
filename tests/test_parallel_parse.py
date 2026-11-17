"""tests/test_parallel_parse.py

Unit tests for noesis_harness.parallel_parse.

Stdlib only. Run: python -m unittest tests.test_parallel_parse -q
"""

import concurrent.futures
import threading
import time
import unittest
from dataclasses import FrozenInstanceError
from unittest import mock

import noesis_harness.parallel_parse as parallel_parse
from noesis_harness.parallel_parse import (
    DEFAULT_WORKER_CAP,
    ParseFailure,
    bounded_fanout,
    ordered_fanout,
    parse_files_parallel,
)


class TestOrderedFanout(unittest.TestCase):
    def test_input_order_preserved_when_completion_order_differs(self):
        completion_order = []
        lock = threading.Lock()

        def parse_fn(item):
            if item == "a":
                time.sleep(0.20)
            elif item == "b":
                time.sleep(0.10)
            with lock:
                completion_order.append(item)
            return item.upper()

        result = ordered_fanout(["a", "b", "c"], parse_fn, workers=3)

        self.assertEqual([item for item, _ in result], ["a", "b", "c"])
        self.assertEqual([value for _, value in result], ["A", "B", "C"])
        self.assertNotEqual(completion_order, ["a", "b", "c"])
        self.assertEqual(completion_order[0], "c")

    def test_parse_fn_receives_exact_item(self):
        seen = []
        lock = threading.Lock()

        def parse_fn(item):
            with lock:
                seen.append(item)
            return len(item)

        items = ["alpha", "beta", "gamma", "delta"]
        result = ordered_fanout(items, parse_fn, workers=4)

        self.assertEqual(sorted(seen), sorted(items))
        self.assertEqual({item for item, _ in result}, set(items))

    def test_exceptions_do_not_abort_other_items(self):
        def parse_fn(item):
            if item == "x":
                raise ValueError("broken x")
            return item

        result = ordered_fanout(["a", "x", "b", "c"], parse_fn, workers=4)

        values = [value for _, value in result]
        failures = [v for v in values if isinstance(v, ParseFailure)]
        successes = [v for v in values if not isinstance(v, ParseFailure)]
        self.assertEqual(successes, ["a", "b", "c"])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].item, "x")

    def test_parse_failure_captured_per_item(self):
        def parse_fn(item):
            if item == "bad":
                raise ValueError("boom")
            return 1

        result = ordered_fanout(["ok", "bad"], parse_fn, workers=2)
        by_item = dict(result)

        failure = by_item["bad"]
        self.assertIsInstance(failure, ParseFailure)
        self.assertEqual(failure.item, "bad")
        self.assertEqual(failure.error, "boom")
        self.assertEqual(failure.error_type, "ValueError")
        self.assertEqual(by_item["ok"], 1)

    def test_mixed_ok_and_failed_ordering(self):
        def parse_fn(item):
            if item.startswith("bad"):
                raise RuntimeError("no " + item)
            return item.upper()

        result = ordered_fanout(["ok1", "bad1", "ok2", "bad2"], parse_fn, workers=4)

        self.assertEqual([item for item, _ in result],
                         ["ok1", "bad1", "ok2", "bad2"])
        self.assertIsInstance(result[1][1], ParseFailure)
        self.assertIsInstance(result[3][1], ParseFailure)
        self.assertEqual(result[0][1], "OK1")
        self.assertEqual(result[2][1], "OK2")

    def test_workers_one_works(self):
        def parse_fn(item):
            return item + "!"

        result = ordered_fanout(["a", "b", "c"], parse_fn, workers=1)
        self.assertEqual(result, [("a", "a!"), ("b", "b!"), ("c", "c!")])

    def test_workers_capped_at_32(self):
        captured = []
        real_executor = concurrent.futures.ThreadPoolExecutor

        def factory(max_workers=None, **kwargs):
            captured.append(max_workers)
            return real_executor(max_workers=max_workers)

        with mock.patch.object(parallel_parse, "ThreadPoolExecutor", factory):
            ordered_fanout(["a", "b", "c"], lambda item: item, workers=1000)

        self.assertEqual(captured, [32])

    def test_empty_input(self):
        self.assertEqual(ordered_fanout([], lambda item: item), [])
        self.assertEqual(bounded_fanout([], lambda item: item), [])

    def test_deterministic_across_two_runs(self):
        def parse_fn(item):
            return item[::-1]

        items = ["z", "y", "x", "w", "v", "u"]
        first = ordered_fanout(items, parse_fn, workers=3)
        second = ordered_fanout(items, parse_fn, workers=3)
        self.assertEqual(first, second)


class TestParseFilesParallel(unittest.TestCase):
    def test_ok_and_failed_split_ordering(self):
        def parse_fn(item):
            if item.startswith("bad"):
                raise ValueError(item)
            return item

        output = parse_files_parallel(
            ["a", "bad2", "b", "bad1"], parse_fn, workers=4
        )

        self.assertEqual(list(output["ok"].keys()), ["a", "b"])
        self.assertEqual(output["ok"], {"a": "a", "b": "b"})
        self.assertEqual([f.item for f in output["failed"]], ["bad1", "bad2"])
        self.assertEqual([f.error_type for f in output["failed"]],
                         ["ValueError", "ValueError"])

    def test_empty_input(self):
        output = parse_files_parallel([], lambda item: item)
        self.assertEqual(output["ok"], {})
        self.assertEqual(output["failed"], [])

    def test_deterministic_across_two_runs(self):
        def parse_fn(item):
            if item == "bad":
                raise KeyError("bad")
            return len(item)

        paths = ["one", "bad", "three", "four"]
        first = parse_files_parallel(paths, parse_fn, workers=2)
        second = parse_files_parallel(paths, parse_fn, workers=2)
        self.assertEqual(first["ok"], second["ok"])
        self.assertEqual(first["failed"], second["failed"])
        self.assertEqual(list(first["ok"].keys()), ["one", "three", "four"])


class TestBoundedFanout(unittest.TestCase):
    def test_deadline_marks_remaining_without_calling_parse(self):
        calls = []

        def parse_fn(item):
            calls.append(item)
            return item

        result = bounded_fanout(
            ["a", "b", "c"],
            parse_fn,
            workers=2,
            deadline=0.0,
            now=lambda: 1.0,
        )

        self.assertEqual(calls, [])
        self.assertEqual([item for item, _ in result], ["a", "b", "c"])
        for _, value in result:
            self.assertIsInstance(value, ParseFailure)
            self.assertEqual(value.error, "deadline exceeded")
            self.assertEqual(value.error_type, "DeadlineExceeded")

    def test_deadline_not_exceeded_runs_all(self):
        calls = []
        lock = threading.Lock()

        def parse_fn(item):
            with lock:
                calls.append(item)
            return item * 2

        result = bounded_fanout(
            ["a", "b", "c"],
            parse_fn,
            workers=2,
            deadline=100.0,
            now=lambda: 0.0,
        )

        self.assertEqual(sorted(calls), ["a", "b", "c"])
        self.assertEqual([value for _, value in result], ["aa", "bb", "cc"])

    def test_deadline_none_behaves_like_ordered_fanout(self):
        items = ["p", "q", "r"]

        def parse_fn(item):
            return item.upper()

        self.assertEqual(
            bounded_fanout(items, parse_fn, workers=2),
            ordered_fanout(items, parse_fn, workers=2),
        )


class TestParseFailureAndConstants(unittest.TestCase):
    def test_parse_failure_is_frozen(self):
        failure = ParseFailure(item="a", error="e", error_type="E")
        with self.assertRaises(FrozenInstanceError):
            failure.item = "b"

    def test_default_worker_cap_constant(self):
        self.assertEqual(DEFAULT_WORKER_CAP, 32)
        self.assertEqual(parallel_parse.DEFAULT_WORKER_CAP, 32)


if __name__ == "__main__":
    unittest.main()
