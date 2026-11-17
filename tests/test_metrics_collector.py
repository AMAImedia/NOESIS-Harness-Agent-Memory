from __future__ import annotations

import os
import tempfile
import unittest

from noesis_harness.metrics_collector import (
    MetricCollector,
    MetricError,
    MetricPoint,
    MetricReport,
    build_report,
    safe_series,
)


class MetricsCollectorTests(unittest.TestCase):
    def collector(self, source="collector"):
        return MetricCollector(tempfile.mkdtemp(), source=source)

    def test_emit_then_series_points_roundtrip(self):
        collector = self.collector()
        path = collector.emit("latency", 12.5, 100.0, {"host": "a"})
        self.assertTrue(path.endswith("latency.jsonl"))
        self.assertTrue(os.path.exists(path))
        points = collector.series_points("latency")
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].series, "latency")
        self.assertEqual(points[0].value, 12.5)
        self.assertEqual(points[0].at, 100.0)
        self.assertEqual(points[0].source, "collector")
        self.assertEqual(points[0].labels, {"host": "a"})

    def test_emit_is_append_only_and_ordered(self):
        collector = self.collector()
        collector.emit("s", 1.0, 1.0)
        collector.emit("s", 2.0, 2.0)
        collector.emit("s", 3.0, 3.0)
        self.assertEqual([p.value for p in collector.series_points("s")], [1.0, 2.0, 3.0])

    def test_latest_returns_last_valid_point(self):
        collector = self.collector()
        self.assertIsNone(collector.latest("s"))
        collector.emit("s", 1.0, 10.0)
        collector.emit("s", 9.0, 20.0)
        latest = collector.latest("s")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.value, 9.0)
        self.assertEqual(latest.at, 20.0)

    def test_mean_p50_p95_nearest_rank_known_data(self):
        collector = self.collector()
        for index, value in enumerate([1.0, 2.0, 3.0, 4.0]):
            collector.emit("s", value, float(index))
        self.assertEqual(collector.mean("s"), 2.5)
        self.assertEqual(collector.p50("s"), 2.0)
        self.assertEqual(collector.p95("s"), 4.0)

    def test_p95_nearest_rank_single_and_twenty(self):
        collector = self.collector()
        collector.emit("one", 7.0, 0.0)
        self.assertEqual(collector.p50("one"), 7.0)
        self.assertEqual(collector.p95("one"), 7.0)
        for index in range(1, 21):
            collector.emit("many", float(index), float(index))
        self.assertEqual(collector.p95("many"), 19.0)

    def test_empty_series_returns_none(self):
        collector = self.collector()
        self.assertIsNone(collector.mean("missing"))
        self.assertIsNone(collector.p50("missing"))
        self.assertIsNone(collector.p95("missing"))
        self.assertIsNone(collector.latest("missing"))
        self.assertEqual(collector.series_points("missing"), [])
        report = build_report(collector, "missing")
        self.assertEqual(report.count, 0)
        self.assertIsNone(report.mean)
        self.assertIsNone(report.p50)
        self.assertIsNone(report.p95)
        self.assertIsNone(report.latest)

    def test_window_bounds_are_inclusive(self):
        collector = self.collector()
        for at in (0.0, 5.0, 10.0, 15.0):
            collector.emit("s", at, at)
        points = collector.window("s", 5.0, 10.0)
        self.assertEqual([p.at for p in points], [5.0, 10.0])

    def test_window_preserves_input_order(self):
        collector = self.collector()
        for at in (30.0, 10.0, 20.0):
            collector.emit("s", at, at)
        points = collector.window("s", 0.0, 100.0)
        self.assertEqual([p.at for p in points], [30.0, 10.0, 20.0])

    def test_nan_and_inf_raise_metric_error(self):
        collector = self.collector()
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(MetricError):
                collector.emit("s", bad, 1.0)
        with self.assertRaises(MetricError):
            collector.emit("s", 1.0, float("nan"))
        self.assertEqual(collector.series_points("s"), [])

    def test_malformed_line_is_skipped(self):
        collector = self.collector()
        collector.emit("s", 1.0, 1.0)
        path = collector.series_path("s")
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("not json at all\n")
            handle.write('{"series": "s", "value": 2.0}\n')
            handle.write("\n")
        collector.emit("s", 3.0, 3.0)
        points = collector.series_points("s")
        self.assertEqual([p.value for p in points], [1.0, 3.0])

    def test_series_names_sorted(self):
        collector = self.collector()
        for name in ("Zulu", "alpha", "Mike"):
            collector.emit(name, 1.0, 1.0)
        self.assertEqual(collector.series_names(), ["Mike", "Zulu", "alpha"])

    def test_stats_counts_points_per_series_and_total(self):
        collector = self.collector()
        collector.emit("a", 1.0, 1.0)
        collector.emit("a", 2.0, 2.0)
        collector.emit("b", 3.0, 3.0)
        stats = collector.stats()
        self.assertEqual(stats["series"], {"a": 2, "b": 1})
        self.assertEqual(stats["series_count"], 2)
        self.assertEqual(stats["total_points"], 3)

    def test_metric_point_json_roundtrip_with_labels(self):
        point = MetricPoint(
            series="throughput",
            value=42.5,
            at=1234.0,
            source="collector",
            labels={"model": "qwen", "lang": "ru"},
        )
        line = point.to_json_line()
        self.assertEqual(line, json_dumps_sorted(point))
        restored = MetricPoint.from_json_line(line)
        self.assertEqual(restored, point)
        self.assertEqual(restored.labels, {"model": "qwen", "lang": "ru"})

    def test_metric_point_from_json_line_rejects_bad_input(self):
        with self.assertRaises(MetricError):
            MetricPoint.from_json_line("nope")
        with self.assertRaises(MetricError):
            MetricPoint.from_json_line("[1, 2, 3]")
        with self.assertRaises(MetricError):
            MetricPoint.from_json_line('{"series": "s", "value": 1.0}')

    def test_safe_series_sanitizes_and_rejects_traversal(self):
        self.assertEqual(safe_series("Some Metric!"), "Some-Metric")
        for bad in ("..", "../etc", "a/b", "a\\b", "", "   ", "..\\win"):
            with self.assertRaises(MetricError):
                safe_series(bad)

    def test_build_report_fields(self):
        collector = self.collector()
        for index, value in enumerate([10.0, 20.0, 30.0]):
            collector.emit("s", value, float(index))
        report = build_report(collector, "s")
        self.assertIsInstance(report, MetricReport)
        self.assertEqual(report.series, "s")
        self.assertEqual(report.count, 3)
        self.assertEqual(report.mean, 20.0)
        self.assertEqual(report.p50, 20.0)
        self.assertEqual(report.p95, 30.0)
        self.assertEqual(report.latest, 30.0)
        self.assertEqual(
            report.as_dict(),
            {
                "series": "s",
                "count": 3,
                "mean": 20.0,
                "p50": 20.0,
                "p95": 30.0,
                "latest": 30.0,
            },
        )

    def test_flush_is_a_noop_and_does_not_lose_data(self):
        collector = self.collector()
        collector.emit("s", 5.0, 1.0)
        collector.flush()
        collector.flush()
        self.assertEqual(len(collector.series_points("s")), 1)

    def test_determinism_identical_sequences_produce_identical_bytes(self):
        def run(root):
            collector = MetricCollector(root, source="collector")
            collector.emit("gamma", 3.0, 3.0, {"b": "2", "a": "1"})
            collector.emit("alpha", 1.0, 1.0)
            collector.emit("gamma", 2.0, 2.0)
            return [
                collector.series_path("gamma"),
                collector.series_path("alpha"),
            ]

        left_paths = run(tempfile.mkdtemp())
        right_paths = run(tempfile.mkdtemp())
        for left, right in zip(left_paths, right_paths):
            with open(left, "rb") as handle:
                left_bytes = handle.read()
            with open(right, "rb") as handle:
                right_bytes = handle.read()
            self.assertEqual(left_bytes, right_bytes)


def json_dumps_sorted(point):
    import json

    return json.dumps(
        {
            "series": point.series,
            "value": point.value,
            "at": point.at,
            "source": point.source,
            "labels": dict(point.labels),
        },
        sort_keys=True,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    unittest.main()
