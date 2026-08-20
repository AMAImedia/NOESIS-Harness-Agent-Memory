# Durable Turn Checkpoints — русская локализация

Это supplemental-описание English primary contract для crash-safe persistence каждого turn в local-first NOESIS loop. Checkpointing является **sequential, atomic, checksum-verified, recoverable и non-executing**.

## Contract

Каждый run начинается с `run_id`. Checkpoint может перейти только с `turn = n` на `turn = n + 1`; пропущенные и повторённые номера отклоняются. Record содержит schema version, идентификаторы run/turn, status, JSON state, output digest, state digest, previous state digest и creation time.

State сериализуется канонически: sorted keys и compact separators. Record digest — SHA-256 canonical payload. SQLite работает в WAL mode; checkpoint и обновление run projection записываются одной транзакцией. Connection закрывается на всех путях, включая commit и exception.

| Status | Значение | Recovery |
|---|---|---|
| `running` | Run принимает следующий sequential turn. | Возобновление с последнего проверенного checkpoint. |
| `checkpointed` | Turn durable записан, loop продолжается. | Продолжение с `turn + 1`. |
| `completed` | Последний turn завершил run. | Финальное state сохраняется. |
| `interrupted` | Loop остановлен между turn или cancellation. | Восстановление последнего проверенного state. |
| `corrupted` | Не прошёл checksum, schema, state digest или chain. | Fail-closed quarantine. |

Malformed payload, digest mismatch, chain discontinuity и неизвестная schema отклоняются. Interrupted write должен оставить либо предыдущий committed state, либо полностью записанный следующий record; half-record не принимается.

Store сохраняет только state и evidence. Он не запускает callbacks, не импортирует generated code, не выводит approvals и не активирует skills. Native host и external harness claims остаются `not_run` до matching environments.

English primary contract: [`DURABLE_TURN_CHECKPOINTS.md`](../../DURABLE_TURN_CHECKPOINTS.md).
