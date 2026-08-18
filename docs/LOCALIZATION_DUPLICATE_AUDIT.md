# Localization and Duplicate Audit

## Scope

This audit covers Markdown documentation under `docs/`, repository references to localized files, exact-content duplicates, and unintended Cyrillic text in the English primary layer.

## Structure

Russian documentation is stored under [`locales/ru/`](locales/ru/). The root `docs/` directory contains English primary contracts, architecture, reports, and navigation. The Russian master checklist is [`locales/ru/PROJECT_CHECKLIST_TODO_RU.md`](locales/ru/PROJECT_CHECKLIST_TODO_RU.md).

| Check | Result |
|---|---|
| Russian documents moved out of `docs/` root | `passed`; 38 files in `docs/locales/ru/` |
| English primary docs contain unintended Cyrillic | `passed`; zero findings in root docs, code, scripts, tests, and benchmarks |
| Old root localized-path references | `passed`; zero stale references after relocation |
| Broken local Markdown links | `passed` after relocation repair |
| Exact byte-identical Markdown duplicates | `passed`; zero duplicate hashes |
| English/Russian companion relationship | `passed`; primary pages link to locale companions where a companion exists |
| Machine-readable evidence language | `passed`; stable statuses remain English (`passed`, `failed`, `blocked`, `not_run`, `not_started`) |

## Interpretation

The Russian files are translations or localized runbooks, not parallel implementations. They do not define code-facing identifiers, API schemas, commands, or machine-readable evidence. The English files are the normative source for implementation and release decisions.

A localized document may intentionally summarize or expand its English counterpart. This is not treated as duplication unless the files are byte-identical or a stale path points to a removed root file. Future English contract changes must update the corresponding Russian localization or mark it as needing translation review.

## Review boundary

This audit checks repository structure and textual consistency. It does not claim translation-quality equivalence, native host execution, external runner execution, or comparative agent superiority. Those remain separate evidence gates.
