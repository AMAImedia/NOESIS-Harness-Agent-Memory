# Release Readiness Verifier

`scripts/verify_release_readiness.py` независимо проверяет transferred `release-readiness.json` snapshot. Он читает один JSON file, проверяет deterministic digest и claim boundaries и не rerun-ит pipeline, не вызывает providers, не запускает child processes, не делает network requests и не выполняет artifacts.

```sh
./scripts/verify_release_readiness.sh \
  --snapshot reports/evidence-pipeline/release-readiness.json
```

```powershell
.\scripts\verify_release_readiness.ps1 `
  --snapshot reports\evidence-pipeline\release-readiness.json
```

Valid snapshot возвращает один JSON object со `status=passed` и exit code `0`. Missing, malformed, tampered или claim-inconsistent snapshots возвращают `status=blocked` и exit code `2`. Verifier не переинтерпретирует `not_run`, `blocked` или `unsupported` native/external states как passed.
