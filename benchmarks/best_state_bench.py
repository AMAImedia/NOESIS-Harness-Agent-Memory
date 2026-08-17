import argparse
import tempfile
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from noesis_harness.best_state import BestStateStore


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=100); n=max(3, ap.parse_args().n)
    with tempfile.TemporaryDirectory() as d:
        store=BestStateStore(str(Path(d)/'best.db'))
        t0=time.perf_counter(); best_score=-1.0; best_id=None; regressions=0
        for i in range(n):
            score=0.05 if i == n - 1 else ((i / n) if i % 5 else max(0.0, (i - 4) / n))
            decision=store.record_candidate('bench-run', score, {'step': i})
            if decision.best_score is not None and decision.best_score > best_score:
                best_score=decision.best_score; best_id=decision.best_state_id
            if decision.status.value == 'accepted_not_best': regressions += 1
        record_ms=(time.perf_counter()-t0)*1000
        before=store.current('bench-run')
        t1=time.perf_counter(); recovery=store.recover('bench-run', 'benchmark-regression'); recovery_ms=(time.perf_counter()-t1)*1000
        after=store.current('bench-run')
        print('benchmark,n,metric,value')
        print(f'best_state,{n},record_candidates_ms,{record_ms:.3f}')
        print(f'best_state,{n},regressions_not_best,{regressions}')
        print(f'best_state,{n},best_score,{store.best("bench-run").score:.6f}')
        print(f'best_state,{n},pre_recovery_score,{before.score:.6f}')
        print(f'best_state,{n},post_recovery_score,{after.score:.6f}')
        print(f'best_state,{n},rollback_events,{store.rollback_count("bench-run")}')
        print(f'best_state,{n},recovery_status,{recovery.status.value}')
        print(f'best_state,{n},recovery_ms,{recovery_ms:.3f}')

if __name__=='__main__': main()
