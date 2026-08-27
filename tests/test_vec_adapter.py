"""tests/test_vec_adapter.py

Unit tests for addons/vec_adapter.py (optional vector-store adapter).

These tests run in an environment WITHOUT any ML/embedding dependency
installed, proving the module imports cleanly and never raises when the
backend is missing. A second group of tests exercises the functional path
with an injected pure-Python embedder (no third-party libs), satisfying the
"pluggable embedding search" contract without adding dependencies.
"""

from __future__ import annotations

import unittest

from addons.vec_adapter import VecStore, _disabled_result


class TestDisabledWhenMissing(unittest.TestCase):
    """The default store has no embedding lib; everything degrades to disabled."""

    def test_import_requires_no_ml_dep(self):
        # Importing the module must not pull any embedding library. If it did,
        # this import-time test would fail in a clean environment.
        import addons.vec_adapter as va  # noqa: F401
        self.assertTrue(hasattr(va, "VecStore"))

    def test_search_disabled_shape(self):
        store = VecStore()
        out = store.search("anything", top_k=3)
        self.assertEqual(out["status"], "disabled")
        self.assertEqual(out["results"], [])

    def test_index_texts_disabled_shape(self):
        store = VecStore()
        out = store.index_texts(["a", "b", "c"])
        self.assertEqual(out["status"], "disabled")
        self.assertEqual(out["results"], [])

    def test_disabled_never_raises(self):
        store = VecStore()
        # Calling both operations repeatedly must never raise.
        for _ in range(3):
            store.index_texts(["x"])
            store.search("y")


class TestPluggableEmbedder(unittest.TestCase):
    """Inject a trivial pure-Python embedder to exercise the functional path."""

    @staticmethod
    def _toy_embedder(texts):
        # Bag-of-words binary vector over a fixed vocabulary. Pure stdlib.
        vocab = ["apple", "banana", "cherry", "dog", "cat"]
        out = []
        for t in texts:
            vec = [1.0 if w in t.lower().split() else 0.0 for w in vocab]
            out.append(vec)
        return out

    def test_index_and_search_ok(self):
        store = VecStore(embedder=self._toy_embedder)
        idx = store.index_texts(["apple banana", "cherry dog", "cat dog"])
        self.assertEqual(idx["status"], "ok")
        self.assertEqual(idx["indexed"], 3)

        res = store.search("apple banana", top_k=2)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(len(res["results"]), 2)
        self.assertEqual(res["results"][0]["text"], "apple banana")
        self.assertGreater(res["results"][0]["score"], 0.0)

    def test_search_empty_index_ok(self):
        store = VecStore(embedder=self._toy_embedder)
        res = store.search("anything", top_k=5)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["results"], [])

    def test_top_k_bounds(self):
        store = VecStore(embedder=self._toy_embedder)
        store.index_texts(["apple banana", "cherry dog", "cat dog", "apple cat"])
        res = store.search("apple", top_k=1)
        self.assertEqual(len(res["results"]), 1)
        res_all = store.search("apple", top_k=99)
        self.assertLessEqual(len(res_all["results"]), 4)

    def test_dict_items_indexed(self):
        store = VecStore(embedder=self._toy_embedder)
        idx = store.index_texts([
            {"text": "apple banana", "id": 1},
            {"text": "cherry dog", "id": 2},
        ])
        self.assertEqual(idx["indexed"], 2)
        res = store.search("cherry", top_k=1)
        self.assertEqual(res["results"][0]["text"], "cherry dog")


if __name__ == "__main__":
    unittest.main()
