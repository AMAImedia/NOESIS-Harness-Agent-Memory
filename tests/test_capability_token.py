"""Tests for noesis_harness.capability_token.

The token primitive is deterministic and stdlib-only; these tests pin the
signing, framing, binding, permission and expiry contracts, plus the failure
modes that must never silently authorize an action.
"""

import unittest

from noesis_harness.capability_token import (
    Capability,
    TokenError,
    b64d,
    b64e,
    canonical_bytes,
    capability_grants,
    mint_capability,
    verify_capability,
)

SECRET = b"test-secret-key"


def make_capability(**overrides):
    fields = {
        "actor": "agent-alpha",
        "scope": "workspace:main",
        "scope_version": 3,
        "run_id": "run-123",
        "lease_token": "lease-abc",
        "permissions": ("read", "write"),
        "issued_at": 1000.0,
        "expires_at": 0.0,
    }
    fields.update(overrides)
    return Capability(**fields)


class TestMintVerify(unittest.TestCase):
    def test_mint_then_verify_roundtrip(self):
        capability = make_capability()
        token = mint_capability(SECRET, capability)
        recovered = verify_capability(SECRET, token)
        self.assertEqual(recovered, capability)

    def test_token_framing(self):
        capability = make_capability()
        token = mint_capability(SECRET, capability)
        parts = token.split(".")
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], "v1")

    def test_determinism(self):
        capability = make_capability()
        self.assertEqual(
            mint_capability(SECRET, capability),
            mint_capability(SECRET, capability),
        )

    def test_matches_claim_true(self):
        capability = make_capability()
        self.assertTrue(
            capability.matches_claim(
                "agent-alpha", "workspace:main", 3, "run-123", "lease-abc"
            )
        )

    def test_matches_claim_false(self):
        capability = make_capability()
        self.assertFalse(
            capability.matches_claim(
                "agent-beta", "workspace:main", 3, "run-123", "lease-abc"
            )
        )
        self.assertFalse(
            capability.matches_claim(
                "agent-alpha", "workspace:other", 3, "run-123", "lease-abc"
            )
        )
        self.assertFalse(
            capability.matches_claim(
                "agent-alpha", "workspace:main", 4, "run-123", "lease-abc"
            )
        )
        self.assertFalse(
            capability.matches_claim(
                "agent-alpha", "workspace:main", 3, "run-999", "lease-abc"
            )
        )
        self.assertFalse(
            capability.matches_claim(
                "agent-alpha", "workspace:main", 3, "run-123", "lease-zzz"
            )
        )


class TestVerificationFailures(unittest.TestCase):
    def test_signature_tamper_rejected(self):
        capability = make_capability()
        token = mint_capability(SECRET, capability)
        head, payload, signature = token.split(".")
        flipped = "A" if signature[0] != "A" else "B"
        tampered = ".".join([head, payload, flipped + signature[1:]])
        with self.assertRaises(TokenError):
            verify_capability(SECRET, tampered)

    def test_payload_tamper_rejected(self):
        capability = make_capability()
        token = mint_capability(SECRET, capability)
        head, payload, signature = token.split(".")
        forged = canonical_bytes(
            {
                "actor": "agent-omega",
                "scope": "workspace:main",
                "scope_version": 3,
                "run_id": "run-123",
                "lease_token": "lease-abc",
                "permissions": ["read", "write"],
                "issued_at": 1000.0,
                "expires_at": 0.0,
                "v": 1,
            }
        )
        tampered = ".".join([head, b64e(forged), signature])
        with self.assertRaises(TokenError):
            verify_capability(SECRET, tampered)

    def test_wrong_secret_rejected(self):
        capability = make_capability()
        token = mint_capability(SECRET, capability)
        with self.assertRaises(TokenError):
            verify_capability(b"a-different-secret", token)

    def test_malformed_token_raises(self):
        for bad in [
            "",
            "not-a-token",
            "v1.only-two-parts",
            "v2.abc.def",
            "v1.!!!.???",
        ]:
            with self.assertRaises(TokenError):
                verify_capability(SECRET, bad)

    def test_version_mismatch_raises(self):
        forged = canonical_bytes(
            {
                "actor": "agent-alpha",
                "scope": "workspace:main",
                "scope_version": 3,
                "run_id": "run-123",
                "lease_token": "lease-abc",
                "permissions": ["read"],
                "issued_at": 1000.0,
                "expires_at": 0.0,
                "v": 2,
            }
        )
        import hashlib
        import hmac

        signature = hmac.new(SECRET, forged, hashlib.sha256).digest()
        token = "v1." + b64e(forged) + "." + b64e(signature)
        with self.assertRaises(TokenError):
            verify_capability(SECRET, token)

    def test_different_length_token_rejected(self):
        capability = make_capability()
        token = mint_capability(SECRET, capability)
        truncated = token[:-4]
        self.assertNotEqual(len(truncated), len(token))
        with self.assertRaises(TokenError):
            verify_capability(SECRET, truncated)


class TestExpiry(unittest.TestCase):
    def test_expiry_honored_with_injected_now(self):
        capability = make_capability(issued_at=100.0, expires_at=200.0)
        token = mint_capability(SECRET, capability)
        self.assertEqual(
            verify_capability(SECRET, token, now=150.0), capability
        )
        with self.assertRaises(TokenError):
            verify_capability(SECRET, token, now=250.0)

    def test_expiry_boundary_is_inclusive(self):
        capability = make_capability(issued_at=100.0, expires_at=200.0)
        token = mint_capability(SECRET, capability)
        self.assertEqual(
            verify_capability(SECRET, token, now=200.0), capability
        )

    def test_no_expiry_token_is_valid(self):
        capability = make_capability(expires_at=0.0)
        token = mint_capability(SECRET, capability)
        self.assertEqual(
            verify_capability(SECRET, token, now=10 ** 12), capability
        )


class TestGrants(unittest.TestCase):
    def test_permission_grant_true(self):
        token = mint_capability(SECRET, make_capability())
        self.assertTrue(
            capability_grants(
                SECRET, token, make_capability(), "read"
            )
        )

    def test_permission_grant_false(self):
        token = mint_capability(SECRET, make_capability())
        self.assertFalse(
            capability_grants(
                SECRET, token, make_capability(), "delete"
            )
        )

    def test_empty_permissions_denies(self):
        capability = make_capability(permissions=())
        token = mint_capability(SECRET, capability)
        self.assertFalse(
            capability_grants(
                SECRET, token, make_capability(permissions=()), "read"
            )
        )

    def test_claim_mismatch_denies(self):
        token = mint_capability(SECRET, make_capability())
        mismatched = make_capability(lease_token="lease-other")
        self.assertFalse(
            capability_grants(SECRET, token, mismatched, "read")
        )

    def test_expired_token_denies(self):
        token = mint_capability(
            SECRET, make_capability(issued_at=100.0, expires_at=200.0)
        )
        self.assertFalse(
            capability_grants(
                SECRET, token, make_capability(), "read", now=250.0
            )
        )


class TestCanonical(unittest.TestCase):
    def test_canonical_bytes_stable_across_key_order(self):
        first = canonical_bytes({"b": 2, "a": 1, "c": [3, 4]})
        second = canonical_bytes({"c": [3, 4], "a": 1, "b": 2})
        self.assertEqual(first, second)
        self.assertEqual(first, b'{"a":1,"b":2,"c":[3,4]}')

    def test_canonical_bytes_preserves_unicode(self):
        encoded = canonical_bytes({"name": "hello-\u03c9"})
        self.assertEqual(encoded.decode("utf-8"), '{"name":"hello-\u03c9"}')

    def test_base64_helpers_roundtrip(self):
        raw = b"\x00\x01\x02\xfb\xff payload"
        self.assertEqual(b64d(b64e(raw)), raw)
        self.assertNotIn("=", b64e(raw))


if __name__ == "__main__":
    unittest.main()
