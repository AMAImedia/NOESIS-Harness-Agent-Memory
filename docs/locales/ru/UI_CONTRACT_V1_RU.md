# NOESIS UI Contract v1

Статус: **реализован; P0-01/P0-02/P0-03 верифицированы локально**

Версия: `1.0`

## Назначение

Этот контракт — стабильная граница между NOESIS-ядром и опциональными адаптерами browser, desktop, Hermes WebUI и DeepSeek Harness. Контракт чисто data-only. Он не экспонирует provider credentials, не исполняет модельно-сгенерированный код и не подразумевает, что удалённый runtime имеет локальный workspace-доступ.

## Общий envelope

Каждый ответ использует следующие поля:

```json
{
  "contract_version": "1.0",
  "ok": true,
  "status": "ready",
  "request_id": "random-id",
  "data": {},
  "error": null,
  "capabilities": {},
  "unavailable_reasons": []
}
```

`status` может быть `ready`, `degraded`, `unavailable`, `denied`, `invalid_request` или `upstream_error`. У неуспешного ответа `ok=false` и структурированный объект `error`. У успешного ответа `ok=true` и нет error. Request ID — непрозрачные значения корреляции и не должны содержать секретов.

Secret-shaped ключи, такие как `token`, `secret`, `password`, `credential`, `authorization`, `api_key` и `private_key`, редактируются рекурсивно до JSON-сериализации. UI получает capability metadata и идентификаторы моделей, но не provider keys и не authorization headers.

## `GET /health`

Read-only health-ответ содержит:

```json
{
  "contract_version": "1.0",
  "ok": true,
  "status": "degraded",
  "data": {
    "runtime_version": "0.1.0",
    "readiness": "ready",
    "binding": "127.0.0.1:0"
  },
  "capabilities": {
    "ui_contract": "ready",
    "provider_registry": "unavailable",
    "hermes_adapter": "unavailable",
    "deepseek_adapter": "unavailable",
    "hardened_sandbox": "unavailable"
  },
  "unavailable_reasons": [
    "provider_registry_unavailable",
    "hermes_adapter_unavailable",
    "deepseek_adapter_unavailable",
    "hardened_sandbox_unavailable"
  ]
}
```

`readiness=ready` означает, что локальный NOESIS control-plane процесс жив. `status=degraded` означает отсутствие опциональных capabilities. Это различие предотвращает путаницу между отсутствующим Hermes/DeepSeek-адаптером или hardened sandbox и мёртвым сервером.

Первая реализация биндит на `127.0.0.1` и поддерживает случайный порт. Non-loopback binding требует отдельного явного адаптера с policy аутентификации и предупреждений. Endpoint read-only и не принимает model prompts или tool commands.

## Форма данных `GET /models`

Provider registry возвращает только метаданные моделей:

```json
{
  "models": [
    {
      "id": "local-model",
      "provider": "ollama",
      "endpoint_kind": "openai-compatible",
      "status": "ready",
      "capabilities": {
        "tools": false,
        "vision": false,
        "structured_output": true,
        "reasoning": false
      }
    }
  ]
}
```

Отсутствующий или несовместимый provider возвращает `status=unavailable` с пустым списком моделей и reason. Provider URL, API keys и authorization headers не входят в эту схему ответа.

## Примеры запуска P0-06

Из корня репозитория запустить metadata-only локальный control plane:

```text
python examples/run_control_plane.py --host 127.0.0.1 --port 8765
```

Сервер слушает только loopback по умолчанию. Во втором терминале следующие команды read-only и не отправляют provider credentials:

**Windows PowerShell**

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8765/health -Method Get | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri http://127.0.0.1:8765/models -Method Get | ConvertTo-Json -Depth 10
```

**Windows `curl.exe`**

```text
curl.exe http://127.0.0.1:8765/health
curl.exe http://127.0.0.1:8765/models
```

**macOS/Linux**

```text
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/models
```

Чтобы проверить fail-soft поведение без сконфигурированных provider-моделей, запустить с:

```text
python examples/run_control_plane.py --host 127.0.0.1 --port 8765 --empty-registry
```

Примеры используют только декларативные демо-метаданные. Они не запускают Hermes, DeepSeek, Ollama, LM Studio или любой модельный процесс.

## Endpoints телеметрийного dashboard

Read-only operator dashboard экспонирует три локальных телеметрийных маршрута:

| Endpoint | Метод | Назначение |
|---|---|---|
| `/api/telemetry` | `GET` | Редактированный snapshot SSE-потоков, child runtimes и счётчиков. |
| `/api/child-runtimes` | `GET` | Редактированный subset child-runtime. |
| `/api/telemetry/events` | `GET` | Один ограниченный snapshot SSE `event: telemetry`; клиенты переподключаются для обновления. |

Телеметрия редактируется рекурсивно по secret-shaped ключам и не может вызывать инструменты, провайдеры или команды. `HealthServer.set_telemetry()` атомарно заменяет snapshot. Dashboard по умолчанию loopback-only и наследует существующую аутентификацию и policy non-loopback предупреждений. Snapshot телеметрии — это не доказательство native sandbox isolation или исполнения внешнего провайдера.

## Граница адаптера

Hermes WebUI и DeepSeek Harness — опциональные адаптеры child-runtime. UI-контракт нормализует их метаданные model/profile/session, но не объединяет их приватную память неявно. Исполнение инструментов остаётся в workspace выбранного runtime, а его местоположение записывается в capability metadata. Доступ к удалённому runtime никогда не должен описываться как local hands.

## Тесты контракта

Контракт тестируется на: детерминированную сериализацию, редактирование секретов, валидные/невалидные статусы, обязательные поля модели, неподдерживаемые версии контракта и fail-soft unavailable ответы. P0-02 добавляет HTTP-тесты для loopback binding, read-only методов, неизвестных путей, ограниченных запросов и clean shutdown. P0-03 добавляет provider registry fixtures для Ollama, LM Studio, llama.cpp, vLLM и OpenAI-совместимых endpoints, а также HTTP-тесты `/models` для ready метаданных и явного unavailable состояния.