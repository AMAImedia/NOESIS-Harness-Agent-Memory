import argparse
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from noesis_harness.orchestration import WorkCoordinator
from noesis_harness.context_engine import BudgetedContextAssembler, ContextItem


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=100); n=max(1,ap.parse_args().n)
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)
        coord=WorkCoordinator(str(root/'coord.db'))
        for i in range(n): coord.add(f't{i}', deps=(f't{i-1}',) if i else ())
        t0=time.perf_counter(); now=1.0
        for i in range(n):
            claim=coord.claim('agent', now=now, ttl=100)
            if claim is None: raise RuntimeError(f'no claim at {i}')
            if not coord.complete(claim.task_id, 'agent', {'step':i}): raise RuntimeError('completion failed')
            now += 0.001
        coord_ms=(time.perf_counter()-t0)*1000
        assembler=BudgetedContextAssembler(n*10)
        items=[ContextItem(f'i{i}', 'evidence '*10, priority=float(n-i), source_ids=(f's{i}',)) for i in range(n)]
        t0=time.perf_counter(); result=assembler.assemble(items); context_ms=(time.perf_counter()-t0)*1000
        print('benchmark,n,metric,value')
        print(f'coordination,{n},chain_claim_complete_ms,{coord_ms:.3f}')
        print(f'coordination,{n},completed_tasks,{n}')
        print(f'context_engine,{n},assemble_ms,{context_ms:.3f}')
        print(f'context_engine,{n},used_tokens,{result.used_tokens}')
        print(f'context_engine,{n},dropped_items,{len(result.dropped_ids)}')

if __name__=='__main__': main()
