# P4-03 Desktop Wrapper Decision Memo

The desktop-wrapper decision is documented as a separate release gate. The current local-first core remains stdlib-only and portable; native `.exe` and `.app` packaging requires target-host Python 3.14 verification, signing, and installer/runtime evidence.

No desktop wrapper is represented as native-ready solely because a source artifact or launcher exists. The detailed Russian decision memo is available in [`DECISION_MEMO_P4-03_DESKTOP_WRAPPER_2026-08-17_RU.md`](locales/ru/DECISION_MEMO_P4-03_DESKTOP_WRAPPER_2026-08-17_RU.md).
