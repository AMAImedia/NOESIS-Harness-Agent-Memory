import unittest

from noesis_harness.external_identity import ExternalIdentityPreparation, ExternalIdentityPreparationError


class ExternalIdentityPreparationTests(unittest.TestCase):
    def setUp(self):
        self.clock = lambda: 1000.0
        self.preparer = ExternalIdentityPreparation(trusted_issuers=("https://issuer.example",), expected_audience="noesis-admin", clock=self.clock)
        self.claims = {"iss": "https://issuer.example", "sub": "operator-7", "aud": ["noesis-admin", "other"], "scope": "admin:session admin:reviewers", "exp": 1100}

    def test_prepare_binds_identity_and_context(self):
        prepared = self.preparer.prepare(self.claims, required_scopes=("admin:session",))
        self.assertEqual(prepared.subject, "operator-7")
        self.assertEqual(prepared.context("session-7").operator_id, "operator-7")
        self.assertEqual(prepared.context("session-7").scopes, ("admin:reviewers", "admin:session"))
        self.assertEqual(prepared.claims_digest, self.preparer.prepare(dict(reversed(tuple(self.claims.items())))).claims_digest)

    def test_denies_untrusted_issuer_audience_expiry_and_scope(self):
        cases = [
            ({**self.claims, "iss": "https://evil.example"}, (), "external_identity_issuer_denied"),
            ({**self.claims, "aud": "other"}, (), "external_identity_audience_denied"),
            ({**self.claims, "exp": 900}, (), "external_identity_expired"),
            (self.claims, ("admin:missing",), "external_identity_scope_denied"),
        ]
        for claims, scopes, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(ExternalIdentityPreparationError, expected):
                    self.preparer.prepare(claims, required_scopes=scopes)

    def test_readiness_is_explicitly_not_run(self):
        readiness = self.preparer.readiness()
        self.assertEqual(readiness["status"], "prepared_not_run")
        self.assertEqual(readiness["external_verification"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
