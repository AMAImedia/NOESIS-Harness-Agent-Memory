# Контракт административных сессий и coordinated mutation journal

Этот контракт фиксирует bounded-local гарантии control plane для операторских сессий и reviewed administrative mutations. Он не заявляет интеграцию с внешним identity provider, cross-file atomicity, native parity или выполнение внешних провайдеров.

## Операторские сессии

`OperatorSessionRegistry.open()` идемпотентен только для той же активной identity и того же нормализованного набора scopes. Повторный вызов возвращает исходную запись и не продлевает первоначальный TTL. Повторное использование session ID с другим оператором или другими scopes fail-closed завершается `operator_session_conflict`. Для открытия используется стабильный event identity, а не суффикс на основе текущего числа событий.

Закрытая, истёкшая, отсутствующая или несовместимая по scopes сессия остаётся неаутентифицированной. Lifecycle сессии управляет только авторизацией и никогда сам не выполняет promotion или activation.

## Coordinated mutation journal

`CoordinatedMutationJournal` записывает явные состояния `prepared`, `committed` и `aborted`. Идентичный replay prepare является no-op. Изменение operation, target или receipt для уже существующего action ID отклоняется как `mutation_prepare_conflict`. Повторные terminal events идемпотентны. Commit после abort и abort после commit отклоняются fail-closed.

> Journal координирует и показывает incomplete state; он не заявляет atomicity между независимыми файлами или хранилищами.

Незавершённая prepared mutation является evidence для recovery и требует явного решения оператора. Control plane не делает silent promotion incomplete mutation и не выводит факт завершения cross-store side effect без подтверждения.

## Evidence и границы

Machine-readable evidence сохраняется в `docs/ADMIN_SESSION_IDEMPOTENCY_EVIDENCE.json` и `docs/COORDINATED_MUTATION_JOURNAL_EVIDENCE.json`. Фокусированные контракты тестируются под Python 3.14 с `ResourceWarning` как error. Native Windows/macOS, external identity providers и external A/B lanes остаются `not_run` до появления подходящих pinned environments и operator-approved evidence.
