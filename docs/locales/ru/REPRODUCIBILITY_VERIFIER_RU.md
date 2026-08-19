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

Runtime fingerprint и contract versions receipt являются descriptive provenance. Signed payload исключает `observed_at` по declared timestamp policy, поэтому добавление observation time не изменяет receipt digest или signature. Verifier доказывает только reproducibility metadata и component binding; это не native-host, performance, external-execution или superiority evidence.
