import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from noesis_harness.coding_adapter import PinnedCodingTaskAdapter
from noesis_harness.isolation_holdouts import CrossAgentLeakageSuite


NORMALIZE = "def normalize_words(text): return [word.lower() for word in text.strip().split()]"
SAFE_JOIN = "from pathlib import Path\ndef safe_join(root, name):\n base=Path(root).resolve(); candidate=(base/name).resolve(); candidate.relative_to(base); return candidate"
CANONICAL = "import json\ndef canonical_json(value): return json.dumps(value, sort_keys=True)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=100)
    n = max(1, parser.parse_args().n)
    coding = PinnedCodingTaskAdapter()
    coding_times = []
    coding_rates = []
    isolation_times = []
    isolation_rates = []
    submissions = (("normalize-words-v1", NORMALIZE), ("safe-join-v1", SAFE_JOIN), ("canonical-json-v1", CANONICAL))
    for _ in range(n):
        start = time.perf_counter(); results = coding.evaluate(submissions); coding_times.append((time.perf_counter()-start)*1000)
        coding_rates.append(sum(result.status == 'passed' for result in results) / len(results))
        start = time.perf_counter(); suite_results = CrossAgentLeakageSuite().evaluate(); isolation_times.append((time.perf_counter()-start)*1000)
        isolation_rates.append(sum(result.passed for result in suite_results) / len(suite_results))
    print('benchmark,n,metric,value')
    print(f'coding,{n},task_count,3')
    print(f'coding,{n},pass_rate,{statistics.mean(coding_rates):.6f}')
    print(f'coding,{n},mean_static_verify_ms,{statistics.mean(coding_times):.6f}')
    print(f'coding,{n},max_static_verify_ms,{max(coding_times):.6f}')
    print(f'coding,{n},dynamic_execution_status,unavailable')
    print(f'isolation,{n},case_count,8')
    print(f'isolation,{n},pass_rate,{statistics.mean(isolation_rates):.6f}')
    print(f'isolation,{n},mean_suite_ms,{statistics.mean(isolation_times):.6f}')
    print(f'isolation,{n},max_suite_ms,{max(isolation_times):.6f}')


if __name__ == '__main__':
    main()
