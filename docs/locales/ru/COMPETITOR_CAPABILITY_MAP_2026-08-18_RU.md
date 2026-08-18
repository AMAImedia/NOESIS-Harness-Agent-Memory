# Capability map: Hermes, OpenCode и Cloudflare Project Think

Дата: 2026-08-18. Этот файл фиксирует только claims, подтверждённые официальными страницами; он не является comparative benchmark и не доказывает superiority NOESIS.

| Система | Подтверждённые capability | Что важно для NOESIS |
|---|---|---|
| Hermes Agent | Persistent memory, session search, learning loop/skill creation, terminal/TUI, messaging gateway, scheduled automations, isolated parallel delegates, multiple terminal backends и native Windows support заявлены в официальном README | Нужны durable experience reuse, skill lifecycle, multi-agent isolation, operator surfaces и native packaging; NOESIS уже имеет memory/recovery/parallel/control-plane primitives, но external quality/native evidence ещё не выполнены |
| OpenCode | Repo/home skill discovery, on-demand loading через native skill tool, YAML frontmatter contract и pattern-based skill permissions подтверждены официальной документацией | Следующий high-leverage local gate — versioned skill discovery/permission/explainability contract, чтобы skills были reusable, scoped и fail-closed |
| Cloudflare Project Think | Durable execution/fibers, isolated sub-agents with SQLite and typed RPC, persistent tree sessions with fork/compaction/search, sandboxed code execution и execution ladder подтверждены официальным announcement | NOESIS должен измерять не только storage size, а recovery correctness, lineage, isolation, bounded execution и explainable governance; это уже частично реализовано и требует дальнейших conformance tests |

## Remaining external boundary

Локально нельзя честно закрыть real pinned Hermes/OpenCode execution, native Windows/macOS builds/signing и external comparative A/B без соответствующих environments, exact revisions и operator approval. Поэтому capability map используется для выбора локальных improvements, а не для ranking.

## Sources

1. [Hermes Agent official repository](https://github.com/nousresearch/hermes-agent)
2. [OpenCode Agent Skills documentation](https://opencode.ai/docs/skills/)
3. [Cloudflare Project Think announcement](https://blog.cloudflare.com/project-think/)
