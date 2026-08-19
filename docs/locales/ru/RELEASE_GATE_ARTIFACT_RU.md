# Release-Gate Artifact

Optional `release-gate.json` artifact использует schema `noesis.release-gate-artifact.v1`. Он хранит отдельные outputs post-transfer и release-readiness stages, deterministic `artifact_digest` и fixed claim boundaries.

Создание через release gate:

```sh
./scripts/release_gate.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --snapshot reports/evidence-pipeline/release-readiness.json \
  --output reports/evidence-pipeline/release-gate.json
```

Проверка после transfer без rerun gate:

```sh
./scripts/verify_release_gate_artifact.sh \
  --artifact reports/evidence-pipeline/release-gate.json
```

Valid artifact возвращает `passed` и exit `0`; missing, malformed, tampered или claim-inconsistent artifacts возвращают `blocked` и exit `2`. Artifact является optional в transfer composition, но если присутствует, принимается только под exact filename `release-gate.json`. Он суммирует только integrity/readiness evidence и не доказывает native execution, external execution, performance или worldwide superiority.
