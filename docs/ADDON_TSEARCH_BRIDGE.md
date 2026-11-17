# Addon: t-search-harness bridge

Optional, disabled-by-default integration of
[turbo-llm/t-search-harness](https://github.com/turbo-llm/t-search-harness)
(Apache-2.0, T-Search model) with NOESIS agent memory. Lives in `addons/`
and is NOT imported by the `noesis_harness/` core (zero-dependency rule).

## What it does

`t-search-harness` is a round-based retrieval/ranking lens: it runs up to N
rounds, each with a fresh context, and only chunks the model explicitly saves
via `save_and_advance` carry forward. It needs two operator-supplied pieces:

- an OpenAI-compatible LLM endpoint (the T-Search operating point),
- a search backend (the `SearchClient` contract: `search(query, top_k) -> str`).

NOESIS satisfies the search contract with `NoesisMemorySearchClient`, which
serves the **NOESIS event log itself as the corpus**. So `retrieve(query)`
ranks the most relevant events from the agent's own memory and returns a focused
context instead of the full projection.

## Integration point (Track C: memory long-context)

This is a pluggable retrieval callback (AGENTS.md rule 2: "if you add
compression, it must be a pluggable callback, not a hard dependency"). Core
recall stays deterministic and LLM-free; the t-search lens is used only when an
operator explicitly enables it and supplies an LLM endpoint. It augments — does
not replace — the existing replay projection.

## Honesty boundary

- Disabled by default (`TSearchBridgeConfig.enabled = False`).
- `retrieve` fails closed: `not_run` when disabled, `blocked` when the harness is
  not installed or no LLM endpoint is configured. It never claims the memory was
  improved or that a run succeeded when it did not.
- t-search-harness is tuned for the T-Search model; behavior on other models is
  best-effort and must not be advertised as parity or superiority.
- No native/external execution or competitor-superiority claims are made.

## Files

- `addons/t_search_bridge.py` — lazy imports `retriever_agent`; stdlib-only at
  import time.
- `tests/test_t_search_bridge.py` — 8 tests, all green without t-search-harness
  installed (guard paths + the NOESIS-memory search adapter).

## Future (optional)

- Swap `NoesisMemorySearchClient` for a real retriever (BM25 / embeddings) when
  an operator provides one; the bridge already speaks the `SearchClient`
  contract.
- When an OpenAI-compatible T-Search (or compatible) endpoint is available, run
  an end-to-end `retrieve` lane and record evidence under the existing honesty
  gates.
