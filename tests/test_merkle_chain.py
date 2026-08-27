"""Tests for noesis_harness/merkle_chain.py

Stdlib-only. Exercises append determinism, head advance, clean-chain verification,
tamper detection, and empty-chain invariants.
"""

import unittest

from noesis_harness.merkle_chain import HashChain, ZERO_DIGEST, _digest


class TestMerkleChain(unittest.TestCase):

    def test_empty_chain_head_is_zero(self):
        chain = HashChain()
        self.assertEqual(chain.head_digest(), ZERO_DIGEST)
        self.assertEqual(len(chain), 0)
        self.assertTrue(chain.verify())

    def test_append_returns_entry_id_equal_to_self_digest(self):
        chain = HashChain()
        entry_id = chain.append({"a": 1})
        self.assertEqual(entry_id, chain.head_digest())
        self.assertEqual(len(chain), 1)

    def test_append_determinism_same_payload_same_digest(self):
        c1 = HashChain()
        c2 = HashChain()
        d1 = c1.append({"k": "v", "n": 3})
        d2 = c2.append({"k": "v", "n": 3})
        self.assertEqual(d1, d2)

    def test_append_determinism_key_order_independent(self):
        c1 = HashChain()
        c2 = HashChain()
        d1 = c1.append({"b": 2, "a": 1})
        d2 = c2.append({"a": 1, "b": 2})
        self.assertEqual(d1, d2)

    def test_head_advances_with_each_append(self):
        chain = HashChain()
        d0 = chain.head_digest()
        d1 = chain.append({"x": 1})
        d2 = chain.append({"x": 2})
        self.assertEqual(d0, ZERO_DIGEST)
        self.assertNotEqual(d1, d2)
        self.assertEqual(chain.head_digest(), d2)
        self.assertEqual(len(chain), 2)

    def test_entries_carry_prev_and_self_digest(self):
        chain = HashChain()
        d1 = chain.append({"one": 1})
        d2 = chain.append({"two": 2})
        entries = chain.entries()
        self.assertEqual(entries[0]["prev_digest"], ZERO_DIGEST)
        self.assertEqual(entries[0]["self_digest"], d1)
        self.assertEqual(entries[1]["prev_digest"], d1)
        self.assertEqual(entries[1]["self_digest"], d2)

    def test_verify_true_on_clean_chain(self):
        chain = HashChain()
        for i in range(5):
            chain.append({"i": i, "data": "payload-%d" % i})
        self.assertTrue(chain.verify())
        self.assertEqual(len(chain), 5)

    def test_verify_false_after_payload_tamper(self):
        chain = HashChain()
        chain.append({"a": 1})
        chain.append({"b": 2})
        chain.append({"c": 3})
        entries = chain.entries()
        # Rebuild (mutate) one stored payload in place.
        entries[1]["payload"] = {"b": 999}
        self.assertFalse(chain.verify())

    def test_verify_false_after_self_digest_tamper(self):
        chain = HashChain()
        chain.append({"a": 1})
        chain.append({"b": 2})
        entries = chain.entries()
        # Corrupt a stored self_digest without touching the payload.
        entries[0]["self_digest"] = ZERO_DIGEST
        self.assertFalse(chain.verify())

    def test_tamper_propagates_to_subsequent_entries(self):
        chain = HashChain()
        for i in range(4):
            chain.append({"v": i})
        entries = chain.entries()
        entries[1]["payload"] = {"v": 999}
        # Even if later self_digests were unchanged, recomputation diverges at
        # the tampered entry and onward.
        self.assertFalse(chain.verify())

    def test_first_entry_chains_off_zero_digest(self):
        chain = HashChain()
        d1 = chain.append({"seed": True})
        self.assertEqual(_digest(ZERO_DIGEST, {"seed": True}), d1)
        self.assertEqual(chain.entries()[0]["prev_digest"], ZERO_DIGEST)

    def test_recompute_matches_entry_digest(self):
        chain = HashChain()
        payload = {"nested": {"x": [1, 2, 3]}, "s": "text"}
        d = chain.append(payload)
        entries = chain.entries()
        self.assertEqual(_digest(entries[0]["prev_digest"], payload), d)


if __name__ == "__main__":
    unittest.main()
