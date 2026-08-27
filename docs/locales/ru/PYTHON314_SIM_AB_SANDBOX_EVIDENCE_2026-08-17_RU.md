# Python 3.14, simulated A/B и sandbox evidence — 2026-08-17

## Матрица доказательств

| Gate | Результат | Граница доказательства |
|---|---|---|
| Official CPython runtime | **PASS для Linux** | CPython 3.14.7 собран из официального Python.org source tarball; SHA-256 проверен против release page; source SPDX и Sigstore artifacts сохранены в `runtime/python-3.14.7/src/`. |
| NOESIS Python 3.14 suite | **PASS** | 250 тестов passed на CPython 3.14.7 Linux. Это реальное 3.14-доказательство, но не Windows/macOS. |
| Contract benchmark | **PASS** | 10/10 локальных contract cases passed на CPython 3.14.7. Измеряет только реализованные NOESIS primitives. |
| Simulated external A/B | **PASS as simulation** | `scripts/simulated_external_ab.py` формирует `noesis.simulated-external-ab.v1`; NOESIS local contract наблюдается, Hermes/OpenCode явно `not_run`. Никакого quality ranking не заявляется. |
| PyInstaller/Briefcase matrix | **FAIL-CLOSED as intended** | Python 3.14 принимается, но Linux корректно блокирует Windows/macOS target packaging. Это доказывает guard behavior, а не валидность native artifacts. |
| Bubblewrap backend | **PASS для Linux conformance subset** | `sandbox_bwrap.py` использует `--unshare-all`, read-only system mounts, workspace-only write binding, явный argv и bounded output. Conformance проверяет command execution, блокировку host project path и блокировку network connection. |
| Windows/macOS native evidence | **NOT RUN** | Требует соответствующие ОС и native Python 3.14 toolchains. |
| External Hermes/OpenCode execution | **NOT RUN** | Требует pinned external runners, точных ревизий и одинаковой model/provider. |

## Интерпретация

Локальные gates теперь материально сильнее: NOESIS имеет реальную CPython 3.14 Linux lane и реальную Linux Bubblewrap isolation lane. Ни один результат не должен продвигаться как native Windows/macOS или external competitor evidence. Отчёт external A/B остаётся protocol-level и fail-closed с `not_run` для Hermes и OpenCode вместо сфабрикованных метрик.

## Известные ограничения

Bubblewrap — это Linux backend, а не portable replacement для Windows Job Objects/AppContainer или macOS sandbox profiles. Текущий backend — это isolation adapter и conformance baseline; production deployment по-прежнему требует threat-model review, privilege audit, seccomp/cgroup policy review и native backend equivalents.

Вывод тестов Python включает не-failing `ResourceWarning` сообщения от существующего SQLite lifecycle кода. Они не валят suite, но остаются backlog item-ом по повышению надёжности и должны быть разрешены до claim на финальный релиз.

## Ссылки

[1]: https://www.python.org/downloads/release/python-3147/ "Python 3.14.7 official release page"
[2]: https://github.com/containers/bubblewrap "Bubblewrap project"
[3]: https://github.com/NousResearch/hermes-agent "Hermes Agent repository"
[4]: https://opencode.ai/docs/ "OpenCode official documentation"
