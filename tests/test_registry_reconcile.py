"""Tests for noesis_harness.registry_reconcile."""

import os
import tempfile
import unittest

from noesis_harness.registry_reconcile import (
    Finding,
    Severity,
    prune_plan,
    reconcile_directories,
    reconcile_registry,
    summarize,
)


class TestFinding(unittest.TestCase):

    def test_finding_accepts_valid_fields(self):
        finding = Finding(
            severity=Severity.ERROR,
            path="a/b",
            message="boom",
            remediation="fix it",
        )
        self.assertEqual(finding.severity, Severity.ERROR)
        self.assertEqual(finding.path, "a/b")

    def test_finding_raises_on_empty_remediation(self):
        with self.assertRaises(ValueError):
            Finding(Severity.WARNING, "p", "m", "")
        with self.assertRaises(ValueError):
            Finding(Severity.WARNING, "p", "m", "   ")

    def test_finding_raises_on_empty_message(self):
        with self.assertRaises(ValueError):
            Finding(Severity.WARNING, "p", "", "fix")
        with self.assertRaises(ValueError):
            Finding(Severity.WARNING, "p", "   ", "fix")

    def test_finding_raises_on_empty_path(self):
        with self.assertRaises(ValueError):
            Finding(Severity.WARNING, "", "m", "fix")


class TestReconcileRegistry(unittest.TestCase):

    def test_no_drift_returns_empty(self):
        declared = {"alpha": "a.txt", "beta": "sub/b.txt"}
        actual = ["sub/b.txt", "a.txt"]
        self.assertEqual(reconcile_registry(declared, actual), [])

    def test_missing_is_error(self):
        findings = reconcile_registry({"alpha": "a.txt"}, [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, Severity.ERROR)
        self.assertEqual(findings[0].path, "a.txt")
        self.assertIn("create the missing artifact at a.txt", findings[0].remediation)

    def test_orphan_is_warning(self):
        findings = reconcile_registry({}, ["extra.txt"])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, Severity.WARNING)
        self.assertEqual(findings[0].path, "extra.txt")
        self.assertEqual(
            findings[0].remediation, "prune the orphan artifact or register it"
        )

    def test_duplicate_is_warning(self):
        declared = {"alpha": "shared/x", "beta": "shared/x"}
        findings = reconcile_registry(declared, ["shared/x"])
        dup = [f for f in findings if "multiple names" in f.message]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0].severity, Severity.WARNING)
        self.assertEqual(dup[0].path, "shared/x")
        self.assertEqual(dup[0].remediation, "assign a unique path")

    def test_trailing_slash_mismatch_is_info(self):
        declared = {"alpha": "dir/a", "beta": "dir/a/"}
        findings = reconcile_registry(declared, ["dir/a"])
        info = [f for f in findings if f.severity == Severity.INFO]
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0].path, "dir/a")
        self.assertEqual(info[0].remediation, "normalize path spelling")

    def test_case_and_backslash_mismatch_is_info(self):
        declared = {"alpha": "Dir\\A", "beta": "dir/a"}
        findings = reconcile_registry(declared, ["dir/a"])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, Severity.INFO)

    def test_trailing_slash_does_not_trigger_missing(self):
        findings = reconcile_registry({"alpha": "a/"}, ["a"])
        self.assertEqual(findings, [])

    def test_every_finding_has_remediation(self):
        declared = {"alpha": "missing/a", "beta": "dup/x", "gamma": "dup/x"}
        actual = ["dup/x", "orphan/y"]
        findings = reconcile_registry(declared, actual)
        self.assertTrue(findings)
        for finding in findings:
            self.assertIsInstance(finding.remediation, str)
            self.assertTrue(finding.remediation.strip())

    def test_sort_order_error_then_warning_then_info(self):
        declared = {"alpha": "AAA_missing", "beta": "bbb/keep", "gamma": "BBB/keep"}
        actual = ["ccc_orphan", "bbb/keep"]
        findings = reconcile_registry(declared, actual)
        severities = [f.severity for f in findings]
        self.assertEqual(
            severities,
            [Severity.ERROR, Severity.WARNING, Severity.INFO],
        )

    def test_sort_order_within_severity_by_path(self):
        findings = reconcile_registry({}, ["b_orphan", "a_orphan"])
        self.assertEqual([f.path for f in findings], ["a_orphan", "b_orphan"])

    def test_determinism_across_identical_calls(self):
        declared = {"alpha": "missing", "beta": "dup/x", "gamma": "dup/x"}
        actual = ["dup/x", "orph", "Orph"]
        first = reconcile_registry(declared, actual)
        second = reconcile_registry(declared, actual)
        self.assertEqual(first, second)


class TestPrunePlan(unittest.TestCase):

    def test_prune_plan_returns_only_orphans_sorted_unique(self):
        declared = {"alpha": "missing/a", "beta": "dup/x", "gamma": "dup/x"}
        actual = ["dup/x", "orphan_b", "orphan_a", "orphan_a"]
        findings = reconcile_registry(declared, actual)
        self.assertEqual(prune_plan(findings), ["orphan_a", "orphan_b"])

    def test_prune_plan_ignores_errors_and_info(self):
        declared = {"alpha": "dir/a", "beta": "dir/a/", "gamma": "gone"}
        actual = ["dir/a"]
        findings = reconcile_registry(declared, actual)
        self.assertEqual(prune_plan(findings), [])

    def test_prune_plan_empty_when_no_orphans(self):
        self.assertEqual(prune_plan([]), [])


class TestSummarize(unittest.TestCase):

    def test_summarize_counts(self):
        findings = [
            Finding(Severity.ERROR, "e1", "m", "r"),
            Finding(Severity.ERROR, "e2", "m", "r"),
            Finding(Severity.WARNING, "w1", "m", "r"),
            Finding(Severity.INFO, "i1", "m", "r"),
        ]
        self.assertEqual(
            summarize(findings),
            {"error": 2, "warning": 1, "info": 1, "total": 4},
        )

    def test_summarize_empty(self):
        self.assertEqual(
            summarize([]),
            {"error": 0, "warning": 0, "info": 0, "total": 0},
        )


class TestReconcileDirectories(unittest.TestCase):

    def test_tempdir_expected_and_extra(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "keep.txt"), "w") as handle:
                handle.write("keep")
            with open(os.path.join(root, "extra.txt"), "w") as handle:
                handle.write("extra")
            findings = reconcile_directories(root, {"keep": "keep.txt"})
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].severity, Severity.WARNING)
            self.assertEqual(findings[0].path, "extra.txt")
            self.assertTrue(os.path.exists(os.path.join(root, "keep.txt")))
            self.assertTrue(os.path.exists(os.path.join(root, "extra.txt")))

    def test_missing_root_yields_error(self):
        root = os.path.join(tempfile.gettempdir(), "noesis_missing_root_xyz")
        findings = reconcile_directories(root, {"a": "a.txt"})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, Severity.ERROR)
        self.assertEqual(findings[0].path, root)
        self.assertTrue(findings[0].remediation.strip())

    def test_does_not_create_anything(self):
        with tempfile.TemporaryDirectory() as root:
            before = sorted(os.listdir(root))
            reconcile_directories(root, {"missing": "not_there"})
            self.assertEqual(sorted(os.listdir(root)), before)


if __name__ == "__main__":
    unittest.main()
