# NOESIS roadmap decision memo: arXiv:2608.13417

Date: 2026-08-17

## Verdict

The paper **Beyond Final Scores: A Systematic Evaluation of Agents for Long-Horizon AI Research and Development** is highly relevant to NOESIS-Harness-Agent-Memory. It should be adopted as an evaluation-design source, not copied as a complete benchmark. Its strongest contribution is the separation of final outcome from process competence, experience reuse and harness effects.

## Verified findings from the paper

The study evaluates seven frontier models on 36 long-horizon AI R&D tasks with three independent rollouts per model-task pair, producing 756 rollouts. It reports both average-of-three (`avg@3`) and best-of-three (`best@3`) outcomes. The paper finds that peak ability and repeatable ability differ materially: the strongest-to-weakest gap is 0.237 under `avg@3` but 0.122 under `best@3`.

The process view separates three deterministic dimensions derived from verifier outcomes and trajectory signals:

| Dimension | Meaning | NOESIS analogue |
|---|---|---|
| C1 Solution Framing | Whether the selected directions produce strong progress early in the normalized horizon | Plan quality, early verified progress and direction changes |
| C2 Execution | Whether proposed changes become runnable and correct deliverables | Command validity, checkpoint validity, test/build results and delivery gates |
| C3 Feedback Control | Whether the agent protects strong states and recovers from regressions | Best-state retention, regression detection, rollback and recovery latency |

The paper also treats experience as a meta-capability. Intra-task evaluation compares the next commit with and without retained experience after a controlled branch point. Inter-task evaluation compares a target task with and without extracted lessons while holding the model, harness, environment and resource limits constant. Experience generally helps, but can cause negative transfer, local-optimum anchoring and evaluator-specific shortcut reuse.

The harness comparison shows that harness choice primarily affects run-to-run stability rather than always raising the performance ceiling. Native or specialized harnesses can improve `avg@3` while leaving `best@3` and model ordering broadly similar, and the best harness can depend on the model and workload category.

The study also reports that genuine novelty is rare in this bounded optimization setting: 3 of 252 best-seed solutions were manually retained as novel approaches, while 16 exhibited evaluation-specific shortcuts. This supports adding anti-shortcut and evaluator-holdout checks to NOESIS rather than optimizing only a single final score.

## Changes to the NOESIS plan

The paper validates the already-planned legacy-vs-new A/B comparison and makes it more precise. The next evaluation layer should add a deterministic `ResearchLoopEvaluator` or equivalent adapter that records normalized trajectory checkpoints and computes C1/C2/C3 without an LLM judge. It should emit both aggregate scores and component scores.

The existing NOESIS evidence and context layers already support much of the required memory discipline: provenance, freshness, conflict proposals, bounded context, dropped-item audit and non-destructive history. The missing experiment is a controlled memory-ablation protocol with the same branch state, token budget, model, tools and environment. The protocol should measure positive transfer, negative transfer, first-commit gain, recovery after misleading evidence and consolidation precision.

The coordination and durable execution layers should add best-state protection as an explicit benchmark target. A future adapter should checkpoint every verified improvement, isolate risky candidates, reject or quarantine regressions, record rollback latency and verify that the final state is never worse than the best accepted state unless a human explicitly approves the change.

Harness effects should be measured with fixed model, task set, environment, token/wall-clock budget and at least three independent rollouts. For local development, begin with a small pinned task set and report `avg@3`, `best@3`, standard deviation, failure rate, cost proxy and process dimensions. Do not claim general superiority from microbenchmarks such as SQLite throughput.

Finally, every benchmark task should include an evaluator-holdout or shortcut probe where feasible. A high score that violates task semantics, uses hidden state, exploits verifier leakage or bypasses the intended objective must be classified as a failure, not as an improvement. Novelty claims should remain optional and require human review; they must not be mixed into deterministic core scores.

## Priority adjustment

| Priority | Action | Reason |
|---:|---|---|
| P0 | Add fixed-task trajectory schema and deterministic C1/C2/C3 evaluator | Converts final-only benchmarks into diagnosable evidence |
| P0 | Implement legacy-vs-new A/B with identical branch, budget and environment | Directly tests whether evidence/context layers improve decisions rather than merely storing more text |
| P0 | Add best-state/regression/rollback benchmark | Protects long-horizon runs from late destructive edits |
| P1 | Add intra-task and inter-task positive/negative transfer suite | Tests whether memory helps, misleads or anchors the agent |
| P1 | Add evaluator-holdout and shortcut-detection cases to adversarial corpus | Prevents fake progress and reward hacking |
| P2 | Add harness-variant comparison and task-aware policy experiments | Useful after the fixed baseline is stable |
| P2 | Add novelty analysis as a separate reviewed report | Expensive and partly judge-dependent; not suitable as a core deterministic metric |

## What not to copy

The paper’s 36-task, 756-rollout, frontier-model evaluation is too expensive and domain-specific for the first local NOESIS release. Its LLM-assisted novelty classification should not become a security or correctness oracle. Its reported gains should not be transplanted as expected NOESIS performance. NOESIS should reproduce the **experimental controls and diagnostic categories**, using a smaller pinned local task set first and publishing only measured local results.

## References

1. Li, Yiwei et al. “Beyond Final Scores: A Systematic Evaluation of Agents for Long-Horizon AI Research and Development.” arXiv:2608.13417v1, 13 Aug 2026. https://arxiv.org/abs/2608.13417
2. HTML full text: https://arxiv.org/html/2608.13417v1
