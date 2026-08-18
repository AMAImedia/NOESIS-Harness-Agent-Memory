# Release Metadata / License / Provenance Evidence

**Статус:** локально verified  
**Runtime:** CPython 3.14.7 Linux  
**Machine-readable evidence:** `docs/PARALLEL_METADATA_EVIDENCE.json`  
**Evidence SHA-256:** `34cf5bfa3f74e909f041600e9dd147d2400711a90e68d5dc1290772ceeca0608`

## Parallel lanes

| Lane | Проверка | Результат |
|---|---|---|
| `release-metadata` | Required files, Python 3.14 policy, MIT alignment, private boundary, README/docs links, CHANGELOG freshness | `passed`; 7 required files, 9 checks |
| `license-provenance` | LICENSE/NOTICE/provenance parity and reference-only boundaries | `passed`; 5 upstream entries, code_copied=false, runtime_dependency=false |
| `changelog-docs` | `[Unreleased]`, dated 2026-08-18 snapshot, Python 3.14, checklist/native/provenance links | `passed`; missing markers `[]` |
| `portable-sbom` | Deterministic fixture build and manifest/SPDX/SHA verification | `passed`; 2 files; byte-identical ZIP SHA across repeated builds |

## Исправленные metadata gaps

README больше не заявляет только local Git baseline: он отражает private GitHub state и сохраняет owner-approved public release gate. В README добавлены прямые ссылки на `THIRD_PARTY_NOTICES.md` и provenance manifest. Docs index теперь включает checklist, native runbook, release audit, CI consistency и third-party provenance. CHANGELOG получил Unreleased snapshot с фактическими Trust Plane, command/parallel, native evidence и CI audit изменениями.

## Legal/provenance boundary

Cloudflare OS/Sandbox SDK, Hermes Agent и OpenCode остаются reference-only или benchmark/adapter candidates; `code_copied=false` и `runtime_dependency=false` для всех пяти declared upstreams. Claude Code явно отмечен как proprietary black-box benchmark reference. Этот audit не утверждает vendor code reuse и не заменяет отдельный license review при будущем vendoring.

## Ограничения

Проверка подтверждает metadata/provenance coverage и portable SBOM plumbing. Она не является доказательством внешнего A/B, native signing, notarization или публичного release approval.
