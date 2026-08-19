# Standalone Reproducibility Verifier

## Назначение

`scripts/verify_reproducibility_receipt.py` независимо проверяет `reproducibility-receipt.json` после transfer evidence directory. Он читает только inventory, signed aggregate, chain summary и reproducibility receipt. Pipeline не запускается, providers не вызываются, child processes не создаются, network requests не выполняются, artifact payloads не исследуются.

## Command contract

```sh
./scripts/verify_reproducibility.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY"
```

```powershell
.\scripts\verify_reproducibility.ps1 `
  --root reports\evidence-pipeline `
  --key $env:NOESIS_EXTERNAL_EVIDENCE_KEY
```

Valid result возвращает один JSON object со `status=passed` и exit code `0`. Missing components, digest drift, wrong key, signature failure, malformed JSON или claim-boundary violations возвращают `status=blocked` и exit code `2`.

Для clean-room replay generated bundle используйте:

```sh
python scripts/replay_operator_evidence_pipeline.py \
  --expected-root reports/evidence-pipeline \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --evidence reports/hermes.json reports/opencode.json reports/deepseek-harness.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --replay-root reports/evidence-replay \
  --readiness-test-count 638 \
  --readiness-python-version 3.14.7
```

Replay root должен быть пустым до запуска. Команда заново создаёт bounded bundle из объявленных manifest и evidence inputs, проверяет runtime fingerprint receipt против активного interpreter и host, сравнивает SHA-256 bytes каждого generated component, затем запускает strict post-transfer и final release-gate verification. Dirty replay root, изменённый input, runtime drift, missing artifact, digest mismatch или environment/status inconsistency блокируются fail-closed. Clean-room replay не может повышать `native_host_status=passed` или `external_lanes_status=passed`; для этих статусов нужны отдельные host-bound receipts, они не синтезируются local replay.

Runtime fingerprint и contract versions receipt являются descriptive provenance. Signed payload исключает `observed_at` по declared timestamp policy, поэтому добавление observation time не изменяет receipt digest или signature. Verifier доказывает только reproducibility metadata и component binding; это не native-host, performance, external-execution или superiority evidence.
