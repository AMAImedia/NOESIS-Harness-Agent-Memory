# Parallel Agent Tracks 2

Четыре изолированных локальных track покрыли следующие control-plane surfaces.

| Track | Статус | Измеренное покрытие |
|---|---|---|
| A — task/session API, SSE и recovery | `passed` | 28 тестов: session 11, task 6, stream 4, recovery 7. |
| B — child runtime и sandbox | `passed` | Sandbox 7 и child 12 тестов; Linux Bubblewrap conformance passed. macOS и Windows backends на Linux — `not_run`. |
| C — memory, provenance и governance | `passed` | Memory 3 и governance 5 тестов; security audit `CLEAN`. |
| D — release/UI/operator contract | `passed` | UI 11 и portable 12 тестов; links и release metadata passed. |

Некоторые filename globs не нашли test file. Такие результаты записаны как neutral `0` coverage, а не как выдуманный pass. Machine evidence: [`PARALLEL_AGENT_TRACKS_2_EVIDENCE.json`](../../PARALLEL_AGENT_TRACKS_2_EVIDENCE.json).

Все track были local-only с отключёнными network и credentials. Этот run не создаёт native Windows/macOS или external Hermes/OpenCode/DeepSeek Harness execution evidence.

Нормативная English-версия: [`PARALLEL_AGENT_TRACKS_2.md`](../../PARALLEL_AGENT_TRACKS_2.md).
