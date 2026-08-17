# NOESIS world-class differentiation bets — 2026-08-17

## Правило проекта

NOESIS может называться лидирующей системой только по измеримым критериям на опубликованном протоколе. Нельзя считать количеством функций доказательство качества, а локальные unit tests — доказательством production isolation или превосходства над Hermes/OpenCode.

## Measurable bets

| Bet | Что должно стать лучше | Метрика | Anti-claim до доказательства |
|---|---|---|---|
| Provenance-aware memory | Память сохраняет не только текст, но и источник, scope, sensitivity, lineage и срок действия | Recall@k, stale-memory rate, provenance completeness, deletion correctness | «Память понимает контекст лучше всех» не заявляется без blind benchmark |
| Context firewall | Restricted observation не может попасть во внешний provider/tool без policy decision и approval | Unauthorized egress rate, taint precision/recall, red-team bypass count | Нельзя обещать zero leakage до adversarial evaluation |
| Zero-access agent OS | Агент стартует без capabilities; доступ выдаётся typed, scoped, expiring и видимым в UI | Deny-by-default pass rate, approval bypass count, capability overreach count | Bounded child process не называется VM/OS sandbox |
| Recovery-first execution | Kill, timeout, malformed output и partial writes приводят к recoverable state | Recovery success rate, lost-event rate, rollback correctness, mean resume time | Нельзя заявлять fault tolerance без chaos/kill tests |
| Explainable governance | Пользователь до side effect видит target, data lineage, capability, expiry, diff и rollback | Decision explanation completeness, approval error rate, review time | «Безопасно автоматически» не заявляется без human-review study |
| Agent specialization | Plan/Explore/Build/Review и delegates имеют непересекающиеся scope и leases | Cross-agent leakage, duplicate work, patch conflict rate, task success | Количество агентов не считается интеллектом |
| Portable trust | Один policy contract работает на local process, Docker/Podman и native OS backends | Backend conformance score, policy parity, artifact reproducibility | Linux simulation не является Windows/macOS evidence |
| Honest benchmark | Сравнение использует одинаковые prompts, model, budget, tools, sandbox и rubric | Task success, patch correctness, latency, token cost, violations, human burden | 10/10 local contracts не является победой над конкурентами |
| Documentation safety | Instructions and examples cannot accidentally leak or trigger dangerous action | Unsafe-example findings, credential findings, snippet pass rate | README completeness не заменяет secure documentation audit |

## Product direction

Сильнейший продуктовый контур — это **Trust Plane + Agent Plane + Workspace Plane**. Trust Plane отвечает за policy, credentials, capabilities, provenance и approvals. Agent Plane выполняет reasoning, provider calls, plans и delegation. Workspace Plane отвечает за snapshots, patches, worktrees, artifacts и recovery. Ни один plane не должен незаметно подменять другой.

Cloudflare-style UI должен быть не декоративной копией, а control surface доверия: каждая capability имеет объяснение, каждый output имеет lineage, каждый child process имеет budgets и network mode, а каждый write проходит через review/commit boundary.

## Next proof sequence

Сначала измеряется context firewall на adversarial corpus. Затем добавляются chaos tests для recovery. После этого запускается одинаковый task suite против NOESIS, Hermes и OpenCode в disposable environments. Только после нативной Windows/macOS проверки и external benchmark можно публиковать comparative claims.

## Non-negotiable anti-claims

Пока не доказано обратное, NOESIS не называется world-best, autonomous unrestricted, VM-isolated, zero-leak, production-ready native desktop app или superior-to-Hermes/OpenCode. Текущий корректный статус — private release candidate с сильными локально проверенными security/governance/memory/workspace primitives.
