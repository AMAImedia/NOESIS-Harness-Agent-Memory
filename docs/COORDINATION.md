
## Strict one-agent-one-lease mode

`Leases(..., one_lease_per_holder=True)` enforces one active task lease per agent holder. A second task claim by the same holder fails closed with `reason: holder_lease_active`; reacquiring the same task remains idempotent. The default remains legacy task-exclusive mode for compatibility, so coordinators that require one agent per delegation loop must explicitly enable strict mode. Shared workspaces and shared capabilities remain denied by `SafeParallelExecutor`; final integration belongs to the coordinator.
