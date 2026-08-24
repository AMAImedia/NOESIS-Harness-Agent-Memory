# Operator Runbook нативного Windows/macOS parity

Этот runbook описывает operator-controlled подготовку Gate 6 и не создаёт native evidence на Linux.

| Цель | Команда | Требуемый host | Текущий Linux status |
|---|---|---|---|
| Windows | `pwsh -NoProfile -File scripts/run_native_parity.ps1` | Windows с Python 3.14.x | `not_run` |
| macOS | `zsh scripts/run_native_parity_macos.sh` | macOS с Python 3.14.x | `not_run` |

Bundle запускает существующий Python 3.14 test suite, сохраняет environment manifest, пишет parity results и требует network-off и отсутствия credentials. Target lane может стать `passed` только после запуска на matching host и появления `environment.json`, `parity-results.json`, `sha256sums.txt` и `sbom.json`.

После завершения bundle operator обязан запустить `python3.14 scripts/validate_native_parity.py --target windows --evidence-dir artifacts/native/windows` (для macOS заменить `windows` на `macos`). CLI вызывает `validate_native_artifacts(target, evidence_dir)`. Validator отклоняет missing/malformed artifacts, нарушенные environment guards, неуспешный parity result, неполный SBOM, пустой SHA-256 manifest и несовпадение SHA-256. `passed` означает только внутренне согласованные artifacts matching host, а не превосходство во внешнем benchmark.

Linux dry-run или static inspection остаются `not_run` и никогда не превращаются в native success. Machine-readable contract находится в [`CROSS_PLATFORM_RELEASE_GATE_MATRIX.json`](../../CROSS_PLATFORM_RELEASE_GATE_MATRIX.json), а preparation API — в `noesis_harness.native_parity`.

## Примечание о Windows recovery write-path

Recovery JSON writer сохраняет atomic replacement и обрабатывает read-only regular destination на Windows: при необходимости временно возвращается write permission, выполняется `os.replace`, затем прежний mode восстанавливается также при failure cleanup. Symlink targets отклоняются. Focused regressions `test_atomic_json_replace_preserves_read_only_mode` и `test_repair_chain_rotates_monotonically_and_rejects_reorder` прошли на CPython 3.11 при `ResourceWarning=0`. Полный native Python 3.14 parity и signed package validation остаются host-gated и здесь не объявляются успешными.

Полный discovery `tests.test_execution_recovery` на этом Windows lane остаётся bounded diagnostic concern; отдельные repair/finalization cases проходят, а timeout считается incomplete evidence, не успехом.
