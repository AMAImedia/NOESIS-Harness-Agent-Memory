# Standard wiring lifecycle ingestion

`build_healthserver_wiring(adapter)` возвращает bounded status provider и operator action handler для `HealthServer`.

Standard handler поддерживает `preflight`, `approve` и `import`. `preflight` требует existing absolute bundle и lifecycle paths. Он записывает `awaiting_approval` и никогда не выполняет automatic import. `approve` связывает record с authenticated operator identity и expiry. `import` требует matching signed approval и записывает `accepted_audit_only`.

Status provider показывает последний durable record или `not_run` до первого preflight. Каждый result сохраняет `execution_allowed=false`, `automatic_execution=false`, `automatic_import=false` и `claim=false`. Wiring не запускает providers или external lanes.
