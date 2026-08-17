import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from noesis_harness.health_server import HealthServer


def percentile(values, fraction):
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
    return ordered[index]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=100)
    n = max(1, parser.parse_args().n)
    latencies = []
    errors = 0
    response_sizes = []
    with HealthServer(port=0) as server:
        url = f'http://{server.address[0]}:{server.address[1]}/health'
        for _ in range(n):
            start = time.perf_counter()
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    body = response.read()
                    if response.status != 200:
                        errors += 1
                    response_sizes.append(len(body))
                    payload = json.loads(body.decode('utf-8'))
                    if payload.get('contract_version') != '1.0':
                        errors += 1
            except Exception:
                errors += 1
            latencies.append((time.perf_counter() - start) * 1000)
    print('benchmark,n,metric,value')
    print(f'p0_health,{n},error_rate,{errors / n:.6f}')
    print(f'p0_health,{n},p50_ms,{percentile(latencies, 0.50):.6f}')
    print(f'p0_health,{n},p95_ms,{percentile(latencies, 0.95):.6f}')
    print(f'p0_health,{n},mean_ms,{statistics.mean(latencies):.6f}')
    print(f'p0_health,{n},response_bytes_mean,{statistics.mean(response_sizes):.2f}')


if __name__ == '__main__':
    main()
