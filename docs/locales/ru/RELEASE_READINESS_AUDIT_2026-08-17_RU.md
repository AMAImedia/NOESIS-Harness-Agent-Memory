# NOESIS — Release-readiness audit

**Дата:** 2026-08-17  
**Репозиторий:** `AMAImedia/NOESIS-Harness-Agent-Memory`  
**Режим:** Private  
**Аудитор:** Manus AI

## Итог

Текущий private checkout проходит release-readiness gates для локального stdlib-only core и Portable Control Plane. Remote `main` совпадает с локальным `HEAD`, repository остаётся private, полный regression suite проходит, recall benchmark сохраняет accuracy 1.00, а AST audit не обнаружил фактических вызовов `eval` или `exec` в `noesis_harness/`.

> **Verdict:** локальная private release candidate готова для дальнейшего owner review, но не является публичным релизом и не должна называться hardened OS-level sandbox или нативным macOS arm64 artifact без соответствующих runner-проверок.

## Verified gates

| Gate | Результат | Доказательство |
|---|---:|---|
| Remote consistency | PASS | Local и remote SHA совпадают: `8f1e5b53f3c3f6efbf0042341a553dfc332175dc` |
| Repository visibility | PASS | GitHub API: `private: true`, default branch `main` |
| Full regression | PASS | `200/200` unittest tests |
| Recall benchmark | PASS | `20/20`, accuracy `1.00` |
| AST syntax audit | PASS | Syntax errors: `0` |
| Actual `eval`/`exec` calls | PASS | AST calls in core: `0` |
| Secret-like scan | PASS | Non-fixture secret-like hits: `0` |
| Synthetic security fixtures | EXPECTED | One private-key marker exists only in `security_holdouts.py` as a negative holdout case |
| Diff hygiene | PASS | `git diff --check` clean |
| Dynamic coding execution | INTENTIONALLY UNAVAILABLE | Adapter performs static AST checks only |
| Hardened OS sandbox | UNAVAILABLE | Not implemented and not claimed |
| Native macOS arm64 artifact | SIMULATED ONLY | macOS path/startup behavior simulated; native runner unavailable |

## Delivered capability surface

The repository now contains the versioned UI contract, read-only `/health`, `/models` and `/ui`, capability-aware provider and model selection, Hermes and DeepSeek declarative adapters, child-runtime supervision, cross-platform user-data separation, LAN auth boundaries, `.noesisskill` manifests, safe staged import, transactional rollback, declarative metadata translation, portable Windows/macOS launch boundaries, local gateway fixtures, and expanded static coding-task verification.

The security model remains deliberately conservative. Local runtimes bind to loopback by default. Non-loopback mode requires explicit opt-in, bearer authentication and warning acknowledgement. Skills and bridge metadata are validated as data; foreign presets, commands, credentials, model output and tool output are not silently executed or imported.

## Remaining owner decisions

| Decision | Current state | Required action |
|---|---|---|
| Branch protection | Waiting for owner | Decide required status checks and review policy for private `main` |
| Electron/Tauri wrapper | Waiting for owner | Choose only if a desktop shell is needed; current stdlib control plane remains framework-independent |
| Native macOS arm64 verification | Not available in current environment | Run native launch/data-preservation smoke tests on a macOS arm64 runner |
| Windows `.exe` artifact | Not claimed | Add a Windows packaging runner before claiming a compiled portable artifact |
| Public visibility | Waiting for owner | Keep private until explicit approval after release review |

## Release boundary

This audit approves the current implementation for continued private development and controlled local testing. It does not approve public release, credentials, external provider execution, unrestricted LAN exposure, automatic skill execution, or claims of OS-level sandboxing. Those boundaries remain explicit in the checklist and code paths.
