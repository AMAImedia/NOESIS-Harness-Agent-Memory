# Standard Lifecycle Ingestion Wiring

`build_healthserver_wiring(adapter)` returns a bounded status provider and an operator action handler for `HealthServer`.

The standard handler supports `preflight`, `approve`, and `import`. `preflight` requires existing absolute bundle and lifecycle paths. It records `awaiting_approval`; it never imports automatically. `approve` binds the record to the authenticated operator identity and expiry. `import` requires the matching signed approval and records `accepted_audit_only`.

The status provider reports the latest durable record, or `not_run` before the first preflight. Every returned result preserves `execution_allowed=false`, `automatic_execution=false`, `automatic_import=false`, and `claim=false`. The wiring never executes providers or external lanes.
