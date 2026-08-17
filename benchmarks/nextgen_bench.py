import argparse
import tempfile
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from noesis_harness.nextgen import AgentManifest, AuditChain, ContextManager, IsolationBroker
from noesis_harness.governance import DAGPlanner
from noesis_harness.fibers import FiberStore
from noesis_harness.evidence import EvidenceStore
from noesis_harness.security import SecurityScanner


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=100)
    args = ap.parse_args()
    n = max(1, args.n)
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        chain = AuditChain(str(root/'audit.jsonl'))
        t0 = time.perf_counter()
        for i in range(n): chain.append('bench', 'event', {'i': i})
        audit_ms = (time.perf_counter()-t0)*1000
        ctx = ContextManager(str(root/'context.db'))
        sid = ctx.create_session('bench')
        for i in range(n): ctx.add(sid, 'user', f'fact {i}', source_ids=(f's{i}',))
        t0 = time.perf_counter(); packed = ctx.pack(sid, n*30, agent_id='bench'); context_ms=(time.perf_counter()-t0)*1000
        dag=DAGPlanner(max_parallel=8)
        for i in range(n): dag.add(f't{i}', (f't{i-1}',) if i else ())
        t0=time.perf_counter(); stages=dag.stages(); dag_ms=(time.perf_counter()-t0)*1000
        broker=IsolationBroker(str(root/'broker.db'))
        for i in range(min(n, 10)):
            broker.register(AgentManifest(f'a{i}', 'worker', private_scope=f'private:a{i}', readable_scopes=('shared',)))
        t0=time.perf_counter()
        for i in range(1, min(n, 10)): broker.send('a0', f'a{i}', f't{i}', {'i':i})
        broker_ms=(time.perf_counter()-t0)*1000
        fibers=FiberStore(str(root/'fibers.db'))
        t0=time.perf_counter()
        for i in range(n):
            fid=fibers.register('bench', {'i':i})
            fibers.checkpoint(fid, 1, {'done':True}, done=True)
        fiber_ms=(time.perf_counter()-t0)*1000
        evidence=EvidenceStore(str(root/'evidence.db'))
        t0=time.perf_counter()
        for i in range(n): evidence.add(f'agent fact {i}', [f's{i}'], confidence=0.5)
        evidence.search('agent fact', limit=10)
        evidence_ms=(time.perf_counter()-t0)*1000
        scanner=SecurityScanner()
        t0=time.perf_counter()
        for i in range(n): scanner.scan('ordinary safe text')
        security_ms=(time.perf_counter()-t0)*1000
        print('benchmark,n,metric,value')
        print(f'audit,{n},events_per_second,{n/(audit_ms/1000):.2f}')
        print(f'context,{n},pack_ms,{context_ms:.3f}')
        print(f'context,{n},selected_chars,{packed["used_chars"]}')
        print(f'dag,{n},plan_ms,{dag_ms:.3f}')
        print(f'dag,{n},stages,{len(stages)}')
        print(f'broker,{min(n,10)},send_ms,{broker_ms:.3f}')
        print(f'fibers,{n},register_checkpoint_ms,{fiber_ms:.3f}')
        print(f'evidence,{n},add_search_ms,{evidence_ms:.3f}')
        print(f'security,{n},safe_scan_ms,{security_ms:.3f}')

if __name__ == '__main__':
    main()
