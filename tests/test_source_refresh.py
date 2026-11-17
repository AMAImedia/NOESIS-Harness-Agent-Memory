import json
import os
import tempfile
import unittest

from noesis_harness.source_refresh import (
    MANIFEST_VERSION,
    FileState,
    ManifestCache,
    observe,
    plan_all,
    plan_refresh,
    prefix_sample,
)


def write_bytes(path, data):
    with open(path, "wb") as handle:
        handle.write(data)


class SourceRefreshTests(unittest.TestCase):
    def dir(self):
        return tempfile.mkdtemp()

    def file(self, name="source.txt", data=b""):
        path = os.path.join(self.dir(), name)
        write_bytes(path, data)
        return path

    def state(self, path, size=1, prefix="sha256:x", mtime=1.0, safe_size=None):
        return FileState(
            path=path,
            size=size,
            mtime=mtime,
            safe_size=size if safe_size is None else safe_size,
            prefix_sample=prefix,
        )

    # -- prefix_sample ----------------------------------------------------
    def test_prefix_sample_missing_file_is_empty(self):
        missing = os.path.join(self.dir(), "nope.txt")
        self.assertEqual(prefix_sample(missing), "")

    def test_prefix_sample_digest_shape(self):
        path = self.file(data=b"hello world")
        sample = prefix_sample(path)
        self.assertTrue(sample.startswith("sha256:"))
        self.assertEqual(len(sample), len("sha256:") + 64)
        self.assertEqual(sample, prefix_sample(path))

    def test_prefix_sample_empty_file_differs_from_missing(self):
        path = self.file(data=b"")
        self.assertNotEqual(prefix_sample(path), "")
        self.assertTrue(prefix_sample(path).startswith("sha256:"))

    # -- plan_refresh -----------------------------------------------------
    def test_fresh_when_no_prior(self):
        path = self.file(data=b"abc")
        plan = plan_refresh(path, None, observe(path), appendable=True)
        self.assertEqual(plan.mode, "fresh")
        self.assertEqual(plan.offset, 0)

    def test_unchanged_when_size_and_prefix_match(self):
        path = self.file(data=b"abc")
        prior = observe(path)
        plan = plan_refresh(path, prior, observe(path), appendable=True)
        self.assertEqual(plan.mode, "unchanged")
        self.assertEqual(plan.offset, prior.size)
        self.assertEqual(plan.reason, "size and prefix match")

    def test_append_on_growth_with_matching_prefix(self):
        path = self.file(data=b"a" * 5000)
        prior = observe(path)
        with open(path, "ab") as handle:
            handle.write(b"b" * 50)
        observed = observe(path)
        plan = plan_refresh(path, prior, observed, appendable=True)
        self.assertEqual(plan.mode, "append")
        self.assertEqual(plan.offset, prior.size)
        self.assertEqual(plan.offset, 5000)

    def test_small_file_growth_changes_prefix_and_rewrites(self):
        # A prior file shorter than the sample window cannot prove a prefix,
        # so growth must be treated as a rewrite.
        path = self.file(data=b"a" * 100)
        prior = observe(path)
        with open(path, "ab") as handle:
            handle.write(b"b" * 50)
        plan = plan_refresh(path, prior, observe(path), appendable=True)
        self.assertEqual(plan.mode, "rewrite")
        self.assertEqual(plan.reason, "prefix sample changed (truncate and regrow)")

    def test_growth_not_appendable_is_rewrite(self):
        path = self.file(data=b"a" * 5000)
        prior = observe(path)
        with open(path, "ab") as handle:
            handle.write(b"b" * 50)
        plan = plan_refresh(path, prior, observe(path), appendable=False)
        self.assertEqual(plan.mode, "rewrite")
        self.assertEqual(plan.offset, 0)
        self.assertEqual(plan.reason, "growth but not appendable")

    def test_truncate_and_regrow_same_size_is_rewrite(self):
        path = self.file(data=b"A" * 5000)
        prior = observe(path)
        write_bytes(path, b"B" * 5000)
        observed = observe(path)
        self.assertEqual(observed.size, prior.size)
        plan = plan_refresh(path, prior, observed, appendable=True)
        self.assertEqual(plan.mode, "rewrite")
        self.assertEqual(plan.reason, "prefix sample changed (truncate and regrow)")

    def test_shrink_with_matching_prefix_is_rewrite(self):
        head = b"x" * 4096
        path = self.file(data=head + b"a" * 3904)
        prior = observe(path)
        write_bytes(path, head + b"a" * 904)
        observed = observe(path)
        self.assertLess(observed.size, prior.size)
        self.assertEqual(observed.prefix_sample, prior.prefix_sample)
        plan = plan_refresh(path, prior, observed, appendable=True)
        self.assertEqual(plan.mode, "rewrite")
        self.assertEqual(plan.reason, "size shrank")

    def test_rewrite_zeroes_offset(self):
        prior = self.state("/tmp/f", size=5000, prefix="sha256:aaa")
        observed = self.state("/tmp/f", size=10, prefix="sha256:bbb")
        plan = plan_refresh("/tmp/f", prior, observed, appendable=True)
        self.assertEqual(plan.mode, "rewrite")
        self.assertEqual(plan.offset, 0)

    # -- ManifestCache ----------------------------------------------------
    def test_manifest_save_load_roundtrip(self):
        cache = ManifestCache(os.path.join(self.dir(), "manifest.json"))
        state = self.state("/a/b.txt", size=42, prefix="sha256:cafe")
        cache.save({"/a/b.txt": state})
        reloaded = ManifestCache(cache.path).load()
        self.assertEqual(reloaded["/a/b.txt"], state)

    def test_corrupt_manifest_loads_empty(self):
        path = os.path.join(self.dir(), "manifest.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{not valid json")
        self.assertEqual(ManifestCache(path).load(), {})
        self.assertFalse(ManifestCache(path).is_valid())

    def test_version_mismatch_loads_empty(self):
        path = os.path.join(self.dir(), "manifest.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"version": MANIFEST_VERSION + 1, "files": {}}, handle)
        self.assertEqual(ManifestCache(path).load(), {})
        self.assertFalse(ManifestCache(path).is_valid())

    def test_manifest_missing_is_empty_and_invalid(self):
        cache = ManifestCache(os.path.join(self.dir(), "absent.json"))
        self.assertEqual(cache.load(), {})
        self.assertFalse(cache.is_valid())

    def test_update_and_get_roundtrip(self):
        cache = ManifestCache(os.path.join(self.dir(), "manifest.json"))
        state = self.state("/x/y.txt", size=7, prefix="sha256:beef")
        cache.update(state)
        self.assertEqual(cache.get("/x/y.txt"), state)
        fresh = ManifestCache(cache.path)
        self.assertEqual(fresh.get("/x/y.txt"), state)
        self.assertTrue(fresh.is_valid())

    def test_atomic_save_leaves_no_partial_file(self):
        directory = self.dir()
        path = os.path.join(directory, "manifest.json")
        cache = ManifestCache(path)
        cache.save({"/a": self.state("/a", size=3, prefix="sha256:aaa")})
        leftovers = [
            name
            for name in os.listdir(directory)
            if name != "manifest.json"
        ]
        self.assertEqual(leftovers, [])
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload["version"], MANIFEST_VERSION)

    # -- plan_all and digest ---------------------------------------------
    def test_plan_all_sorted_by_path(self):
        cache = ManifestCache(os.path.join(self.dir(), "manifest.json"))
        paths = []
        for name in ("zeta.txt", "alpha.txt", "mid.txt"):
            paths.append(self.file(name, data=b"data-" + name.encode("ascii")))
        plans = plan_all(cache, paths)
        self.assertEqual(
            [plan.path for plan in plans],
            sorted(paths),
        )
        self.assertTrue(all(plan.mode == "fresh" for plan in plans))

    def test_plan_all_mixed_modes(self):
        cache = ManifestCache(os.path.join(self.dir(), "manifest.json"))
        untouched = self.file("untouched.txt", data=b"same")
        growing = self.file("growing.txt", data=b"a" * 5000)
        cache.update(observe(untouched))
        prior = observe(growing)
        cache.update(prior)
        with open(growing, "ab") as handle:
            handle.write(b"b" * 20)
        plans = {plan.path: plan for plan in plan_all(cache, [untouched, growing])}
        self.assertEqual(plans[untouched].mode, "unchanged")
        self.assertEqual(plans[growing].mode, "append")
        self.assertEqual(plans[growing].offset, prior.size)

    def test_digest_is_stable_and_changes_with_state(self):
        cache = ManifestCache(os.path.join(self.dir(), "manifest.json"))
        state = self.state("/a", size=1, prefix="sha256:111")
        cache.save({"/a": state})
        first = ManifestCache(cache.path).digest()
        second = ManifestCache(cache.path).digest()
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("sha256:"))
        cache.update(self.state("/b", size=2, prefix="sha256:222"))
        self.assertNotEqual(first, cache.digest())

    def test_plan_never_reads_whole_file(self):
        # A prefix sample over a huge file stays cheap and deterministic.
        path = self.file(data=b"z" * (8 * 1024 * 1024))
        sample = prefix_sample(path, 4096)
        self.assertEqual(sample, prefix_sample(path, 4096))
        self.assertEqual(len(sample), len("sha256:") + 64)


if __name__ == "__main__":
    unittest.main()
