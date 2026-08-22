# Локальный inference proposal-loop

Windows worker поддерживает **явно настроенный локальный HTTP inference endpoint** через `NOESIS_AUTOLOOP_LOCAL_ENDPOINT` и `NOESIS_AUTOLOOP_PROMPT_FILE`. Ядро остаётся Python stdlib-only: HTTP transport использует `urllib`, а текст, созданный моделью, не импортируется, не исполняется и не публикуется автоматически.

Если заданы обе настройки, каждый ограниченный цикл отправляет запрос по локальному NOESIS chat contract:

```json
{"message":"...","preset":"code","max_tokens":768,"temperature":0.2}
```

Ответ должен быть JSON с текстовым полем `response`, `reply`, `answer`, `text`, `content` или `message.content`. Неизвестная либо повреждённая схема приводит к fail-closed результату. Ответ ограничивается output budget и атомарно сохраняется в `.noesis_autoloop/artifacts/`. В state record сохраняются `mode: review_only_proposal`, номер цикла, request digest, reason и путь к artifact.

Этот режим является **только proposal**. Он не применяет patch, не исполняет сгенерированный код, не объединяет ветки, не публикует skill и не обходит human-governed promotion. Для активации изменения по-прежнему нужен отдельный governed review/import pipeline.

## Настройка Windows

Endpoint и prompt file задаются явно в окружении SYSTEM task или startup wrapper. Endpoint не должен обнаруживаться автоматически. Для существующего локального NOESIS server contract доступен через `POST http://127.0.0.1:8810/api/chat`; readiness и наличие загруженной модели проверяются отдельно.

```powershell
[Environment]::SetEnvironmentVariable(
  'NOESIS_AUTOLOOP_LOCAL_ENDPOINT',
  'http://127.0.0.1:8810/api/chat',
  'Machine'
)
[Environment]::SetEnvironmentVariable(
  'NOESIS_AUTOLOOP_PROMPT_FILE',
  'B:\\path\\to\\review_prompt.txt',
  'Machine'
)
```

Endpoint должен быть loopback либо явно доверенным оператором. Adapter допускает bearer authentication, если она включена server-side; credential должен храниться только в защищённой конфигурации task и не попадать в evidence или logs.

## Проверенная граница

Adapter и proposal path реализованы локально и покрыты детерминированными Windows-compatible tests. Реальный unattended coding run остаётся **environment-gated**, пока endpoint не подтверждён под SYSTEM account: модель должна загрузиться, вернуть bounded response и создать reviewable artifact. До этого worker должен оставаться на validation-only cycles, без заявления о готовности автономного coding.

## Постоянный worker и агентская сессия

Windows Scheduled Task является постоянно работающим **worker**, но не постоянно работающей сессией Manus-агента. После завершения чата worker может выполнять заранее настроенный bounded validation/recovery loop, однако он не получает новый план, не пишет новый код по собственной инициативе и не выполняет интерактивную синхронизацию GitHub между сессиями агента. Поэтому эта граница должна сообщаться явно.

Проверка capability не захватывает worker lock:

```powershell
py -3.11 scripts\noesis_autoloop.py --status
```

Команда возвращает `noesis.autoloop-capabilities.v1`. Инвариантные поля: `agent_session_continuity: false`, `autonomous_code_promotion: false`, `autonomous_protected_admin_mutation: false`. Без явно заданных endpoint и prompt-файла статус равен `validation_only`; при наличии обоих параметров он становится `review_only`, но promotion и выполнение сгенерированного кода всё равно запрещены.

Зелёный heartbeat worker доказывает только завершение настроенного worker cycle. Он не доказывает, что агентская сессия продолжала писать код, обновлять документацию или синхронизировать GitHub после завершения чата.

## Evidence contract

Capability probe теперь возвращает `boundary_version: protected-actions.v1`, явные флаги `local_endpoint_configured`, `prompt_file_configured` и `arbitrary_command_configured`, а также детерминированный `evidence_digest` по публичной capability payload. URL endpoint, пути prompt, текст command и credentials намеренно не попадают в payload и digest. Пустая или состоящая только из пробелов конфигурация считается незаданной и не включает proposal mode.

Стабильные claims: `worker_heartbeat_only`, `no_agent_session_continuity` и `no_protected_admin_mutation`. Это capability claims, а не доказательство загрузки модели или безопасности promotion сгенерированного кода.

## Crash-safe recovery cycle

Если процесс завершился после атомарной записи состояния `running`, но до записи `END`, следующий cycle не перезаписывает это evidence молча. Он увеличивает номер cycle и записывает `recovered_previous_cycle` в `BEGIN`, финальное state и `END`. Так сохраняется детерминированная связь между прерванным turn и recovery attempt, а event log остаётся append-only.

Recovery marker доказывает обнаружение прерванного worker cycle; он не утверждает, что прерванный child process завершился или что proposal был опубликован.

Recovery evidence также содержит детерминированный `recovery_digest`, рассчитанный только по номеру предыдущего cycle и его статусу `running`. Command text, endpoint, prompt path и credentials намеренно исключены. У нормально завершённого cycle recovery digest отсутствует, поэтому факт recovery нельзя заявить ошибочно.

## Durable log writes

Worker сначала записывает evidence lines `BEGIN` и `END`, затем выполняет `flush` и `fsync`, и только после этого продолжает цикл. Это уменьшает crash window: для сохранённого `running` state существует durable `BEGIN`, а для завершённого результата — durable `END` до публикации финального state. Гарантии filesystem и power-loss остаются host boundary; worker не заявляет транзакционную durability сверх контракта файловой системы хоста.

## Redaction command evidence

Для validation cycles durable state и evidence `BEGIN` больше не содержат текст настроенной command. Сохраняются только `command_digest` и `command_configured`. Это не допускает попадания token или других секретов командной строки в state и logs, сохраняя детерминированную идентичность выбранной command.

## Durable proposal queue

Опциональный `NOESIS_AUTOLOOP_STEPS_FILE` может содержать JSON-массив ограниченных review-only steps. Worker детерминированно выбирает `proposal_step_index`, повторяет тот же step после failed proposal и увеличивает индекс только после passed response, атомарно сохранённого как artifact. Исчерпанная очередь даёт явный результат `idle`: worker не выдумывает работу и не запускает скрытую fallback command. Повреждённая очередь или неверный индекс приводят к fail-closed.

Queue влияет только на выбор proposal. Она не применяет patch, не исполняет сгенерированный код, не публикует skill, не объединяет branch и не меняет защищённую администраторскую задачу.

## Capability-scoped proposal lease

Каждый queued proposal step получает короткоживущий lease, ограниченный queue index и worker cycle. Активный lease запрещает duplicate claim; истёкший lease можно reclaim после crash recovery. Identity lease содержит случайный stdlib nonce и хранится только как digest. Lease управляет лишь dispatch proposal и никогда не даёт права изменять защищённые задачи, публиковать code или исполнять model output.

Lease state transitions явно сохраняются в durable state: `claimed` до dispatch, `released` после backend result и `exhausted`, если queue step больше нет. Это audit markers, а не authorization grants. Lease никогда не включает применение patch, выполнение generated code, promotion, merge branch или protected administrator mutation.

## Fresh-session handoff

После каждого bounded cycle worker атомарно записывает `.noesis_autoloop/handoff.json`. Manifest содержит source cycle, digest результата, один безопасный next action, allowlist для code/tests/docs/private GitHub и denylist для protected mutation, promotion, выполнения generated code и credential changes. В нём нет command, endpoint, prompt или secret text. Свежая scheduled task может прочитать manifest перед выбором следующего increment; это handoff contract, а не доказательство непрерывной agent-сессии.
