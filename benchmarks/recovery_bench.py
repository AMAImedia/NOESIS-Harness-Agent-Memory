import argparse
import tempfile
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from noesis_harness.best_state import BestStateStore
from noesis_harness.fibers import FiberStore
from noesis_harness.orchestration import WorkCoordinator
from noesis_harness.recovery import RecoveryCoordinator


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=100)
    n = max(1, ap.parse_args().n)
    with tempfile.TemporaryDirectory() as d:
        db = str(Path(d) / 'recovery.db')
        best, fibers, work = BestStateStore(db), FiberStore(db), WorkCoordinator(db)
        recovered = reclaimed = 0
        t0 = time.perf_counter()
        for i in range(n):
            run_id, task_id = f'run-{i}', f'task-{i}'
            fiber_id = fibers.register('research', {'i': i})
            work.add(task_id)
            work.claim('agent-a', ttl=1.0, now=100.0)
            winner = best.record_candidate(run_id, 0.9, {'i': i, 'state': 'verified'}, metadata={'fiber_step': 4})
            fibers.checkpoint(fiber_id, 4, {'i': i, 'state': 'verified'})
            best.record_candidate(run_id, 0.1, {'i': i, 'state': 'regression'}, metadata={'fiber_step': 5})
            fibers.checkpoint(fiber_id, 5, {'i': i, 'state': 'regression'})
            report = RecoveryCoordinator(best, fibers, work).recover_after_crash(run_id, fiber_id, task_id, now=102.0)
            recovered += report.recovery_status == 'recovered'
            reclaimed += report.reclaimed_leases
            assert report.best_state_id == winner.state.state_id
            assert report.fiber_step == 4
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print('benchmark,n,metric,value')
        print(f'recovery,{n},total_ms,{elapsed_ms:.3f}')
        print(f'recovery,{n},cycles_recovered,{recovered}')
        print(f'recovery,{n},leases_reclaimed,{reclaimed}')
        print(f'recovery,{n},avg_cycle_ms,{elapsed_ms/n:.3f}')


if __name__ == '__main__':
    main()
