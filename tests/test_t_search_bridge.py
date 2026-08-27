"""Tests for the optional t-search bridge.

These run without t-search-harness installed. They verify:
  - the NOESIS-memory search adapter returns a valid JSON SearchClient shape,
  - retrieve() fails closed (not_run / blocked) when disabled or unconfigured,
  - the bridge module imports cleanly even when retriever_agent is absent.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from noesis_harness.event_store import EventStore

from addons.t_search_bridge import (
    NoesisMemorySearchClient,
    TSearchBridgeConfig,
    retrieve,
)


class NoesisMemorySearchClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "events.jsonl")
        store = EventStore(self.path)
        store.append("note", {"text": "the quick brown fox jumps"}, event_id="e1")
        store.append("note", {"text": "lazy dog sleeps all day"}, event_id="e2")
        store.append("note", {"text": "quick silver fox runs"}, event_id="e3")

    def test_search_returns_json_list_with_required_keys(self):
        client = NoesisMemorySearchClient(self.path)
        raw = client.search("quick fox", top_k=10)
        data = json.loads(raw)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) >= 1)
        for item in data:
            self.assertIn("docid", item)
            self.assertIn("snippet", item)
            self.assertIn("score", item)
            self.assertIsInstance(item["score"], float)

    def test_search_ranks_matching_events_first(self):
        client = NoesisMemorySearchClient(self.path)
        data = json.loads(client.search("quick fox", top_k=10))
        docids = [d["docid"] for d in data]
        self.assertEqual(docids[0], "e1")  # both 'quick' and 'fox'

    def test_search_empty_query_no_crash(self):
        client = NoesisMemorySearchClient(self.path)
        data = json.loads(client.search("", top_k=5))
        self.assertIsInstance(data, list)

    def test_search_missing_log_returns_empty_list(self):
        client = NoesisMemorySearchClient(os.path.join(self.tmp, "nope.jsonl"))
        self.assertEqual(json.loads(client.search("x", 5)), [])


class BridgeGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "events.jsonl")
        EventStore(self.path).append("note", {"text": "hello"}, event_id="e1")

    def test_disabled_returns_not_run(self):
        cfg = TSearchBridgeConfig(enabled=False)
        res = retrieve("q", cfg, self.path)
        self.assertEqual(res["status"], "not_run")
        self.assertEqual(res["documents"], [])

    def test_enabled_without_llm_returns_blocked(self):
        # t-search-harness is not installed in CI, so this exercises the
        # blocked path regardless; with endpoints it would also fail closed
        # on the missing harness import.
        cfg = TSearchBridgeConfig(enabled=True, llm_endpoints=[])
        res = retrieve("q", cfg, self.path)
        self.assertEqual(res["status"], "blocked")

    def test_enabled_with_llm_but_no_harness_returns_blocked(self):
        cfg = TSearchBridgeConfig(enabled=True, llm_endpoints=["http://localhost:8000/v1"])
        res = retrieve("q", cfg, self.path)
        # retriever_agent is not installed here -> blocked, never ok.
        self.assertEqual(res["status"], "blocked")
        self.assertIn("t-search-harness", res["reason"])

    def test_config_defaults_are_safe(self):
        cfg = TSearchBridgeConfig()
        self.assertFalse(cfg.enabled)
        self.assertEqual(cfg.llm_endpoints, [])


if __name__ == "__main__":
    unittest.main()
