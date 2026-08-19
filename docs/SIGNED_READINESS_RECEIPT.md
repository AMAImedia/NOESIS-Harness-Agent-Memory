# Signed Release-Readiness Receipt

The schema `noesis.signed-release-readiness-receipt.v1` binds a release-readiness snapshot, a verified full-chain `release-gate.json`, the validated test count used to produce the snapshot, and, for generated operator bundles, the `execution-conformance.json` digest. It includes Python version, native/external status fields, deterministic `receipt_digest`, and an HMAC-SHA256 signature.

The receipt is generated only after the inputs have been verified:

```sh
python scripts/readiness_receipt_cli.py \
  --snapshot reports/evidence-pipeline/release-readiness.json \
  --gate-artifact reports/evidence-pipeline/release-gate.json \
  --test-count 630 \
  --python-version 3.14.7 \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output reports/evidence-pipeline/signed-readiness-receipt.json
```

Verification fails closed on signature, digest, snapshot, gate-artifact, conformance-artifact, status, or test-count drift. A receipt containing `conformance_digest` requires the matching `execution-conformance.json`; the conformance digest is verified before the receipt binding is accepted. The receipt records `native_execution=false`, `external_execution_claim=false`, and `claim_boundary=signed_release_readiness_summary_only`. It is evidence of locally bound readiness metadata, not native-host execution, external-lane execution, performance, or worldwide superiority.
