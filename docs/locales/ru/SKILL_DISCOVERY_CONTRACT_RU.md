# Skill Discovery и Permission Contract

`skill_discovery.py` добавляет безопасный read-only слой для reusable skills. Он совместим с моделью `SKILL.md`, но не импортирует и не исполняет содержимое skill. Исполнение executable skill остаётся отдельной операцией `ExecutableSkillRuntime` через Gatekeeper и ChildExecutionRuntime.

| Контракт | Acceptance criterion |
|---|---|
| Frontmatter | Первый блок обязан быть YAML-подобным `---` block; разрешены только `name`, `description`, `license`, `compatibility`, `metadata` |
| Name | Lowercase kebab-case; имя обязано совпадать с каталогом |
| Description | Непустое значение длиной не более 1024 символов |
| Discovery | Результаты сортируются детерминированно по path; malformed entries не скрываются, а возвращаются как `deny` с explainable reason |
| Integrity | Каждый descriptor содержит SHA-256 исходного `SKILL.md` |
| Permission | Без policy skill видим; с policy default — `deny`; matching patterns поддерживают `allow`, `deny`, `ask`, last matching pattern wins |
| Execution boundary | Discovery читает metadata/body как данные; она не запускает imports, subprocesses или model-generated code |

## Local verification

`tests/test_skill_discovery.py`: **4/4 passed** на CPython 3.14.7. Полный suite и security audits остаются обязательными перед checkpoint.

Это не утверждение совместимости с OpenCode runtime и не external benchmark; это локальный, stdlib-only contract, который делает skill catalog объяснимым и fail-closed.
