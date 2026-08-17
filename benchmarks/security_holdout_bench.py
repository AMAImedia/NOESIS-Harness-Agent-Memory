import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from noesis_harness.security_holdouts import DEFAULT_HOLDOUTS, SecurityHoldoutSuite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=100)
    n = max(1, parser.parse_args().n)
    suite = SecurityHoldoutSuite()
    pass_rates = []
    latencies = []
    for _ in range(n):
        start = time.perf_counter()
        results = suite.evaluate()
        latencies.append((time.perf_counter() - start) * 1000)
        pass_rates.append(sum(1 for result in results if result.passed) / len(results))
    print('benchmark,n,metric,value')
    print(f'security_holdout,{n},case_count,{len(DEFAULT_HOLDOUTS)}')
    print(f'security_holdout,{n},pass_rate,{statistics.mean(pass_rates):.6f}')
    print(f'security_holdout,{n},min_pass_rate,{min(pass_rates):.6f}')
    print(f'security_holdout,{n},mean_scan_ms,{statistics.mean(latencies):.6f}')
    print(f'security_holdout,{n},max_scan_ms,{max(latencies):.6f}')


if __name__ == '__main__':
    main()
