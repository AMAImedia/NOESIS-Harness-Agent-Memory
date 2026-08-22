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
