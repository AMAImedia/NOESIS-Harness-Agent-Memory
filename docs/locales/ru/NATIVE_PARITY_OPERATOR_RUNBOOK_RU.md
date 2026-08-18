# Operator Runbook нативного Windows/macOS parity

Этот runbook описывает operator-controlled подготовку Gate 6 и не создаёт native evidence на Linux.

| Цель | Команда | Требуемый host | Текущий Linux status |
|---|---|---|---|
| Windows | `pwsh -NoProfile -File scripts/run_native_parity.ps1` | Windows с Python 3.14.x | `not_run` |
| macOS | `zsh scripts/run_native_parity_macos.sh` | macOS с Python 3.14.x | `not_run` |

Bundle запускает существующий Python 3.14 test suite, сохраняет environment manifest, пишет parity results и требует network-off и отсутствия credentials. Target lane может стать `passed` только после запуска на matching host и появления `environment.json`, `parity-results.json`, `sha256sums.txt` и `sbom.json`.

Linux dry-run или static inspection остаются `not_run` и никогда не превращаются в native success. Machine-readable contract находится в [`CROSS_PLATFORM_RELEASE_GATE_MATRIX.json`](../../CROSS_PLATFORM_RELEASE_GATE_MATRIX.json), а preparation API — в `noesis_harness.native_parity`.
