# Signed Release-Readiness Receipt

Schema `noesis.signed-release-readiness-receipt.v1` связывает release-readiness snapshot, verified full-chain `release-gate.json`, validated test count, использованный для создания snapshot, и для generated operator bundles digest `execution-conformance.json`. Receipt содержит Python version, native/external status fields, deterministic `receipt_digest` и HMAC-SHA256 signature.

Receipt создаётся только после проверки inputs:

```sh
python scripts/readiness_receipt_cli.py \
  --snapshot reports/evidence-pipeline/release-readiness.json \
  --gate-artifact reports/evidence-pipeline/release-gate.json \
  --test-count 630 \
  --python-version 3.14.7 \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output reports/evidence-pipeline/signed-readiness-receipt.json
```

Verification fail-closed блокируется при signature, digest, snapshot, gate-artifact, conformance-artifact, status или test-count drift. Receipt с `conformance_digest` требует matching `execution-conformance.json`; conformance digest проверяется до принятия receipt binding. Receipt записывает `native_execution=false`, `external_execution_claim=false` и `claim_boundary=signed_release_readiness_summary_only`. Это evidence локально связанных readiness metadata, а не native-host execution, external-lane execution, performance или worldwide superiority.
