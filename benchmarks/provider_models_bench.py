import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from noesis_harness.health_server import HealthServer
from noesis_harness.provider_registry import ModelDescriptor, ProviderDescriptor, ProviderRegistry


def fixture_registry():
    kinds = ("ollama", "lm_studio", "llama_cpp", "vllm", "openai_compatible")
    return ProviderRegistry(tuple(
        ProviderDescriptor(
            provider_id=f"{kind}-fixture",
            kind=kind,
            status="ready",
            models=(ModelDescriptor(model_id=f"{kind}-model", provider=kind, endpoint_kind="openai-compatible", capabilities={"tools": True, "vision": False, "structured_output": True}),),
        )
        for kind in kinds
    ))


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=100)
    n = max(1, parser.parse_args().n)
    registry = fixture_registry()
    serialization = []
    http_latencies = []
    errors = 0
    with HealthServer(port=0, provider_registry=registry) as server:
        url = f'http://{server.address[0]}:{server.address[1]}/models'
        for _ in range(n):
            start = time.perf_counter()
            payload = registry.envelope().to_json()
            serialization.append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    body = response.read()
                    if response.status != 200 or json.loads(body.decode('utf-8')).get('status') != 'ready':
                        errors += 1
            except Exception:
                errors += 1
            http_latencies.append((time.perf_counter() - start) * 1000)
    print('benchmark,n,metric,value')
    print(f'provider_models,{n},error_rate,{errors / n:.6f}')
    print(f'provider_models,{n},serialization_p50_ms,{percentile(serialization, 0.50):.6f}')
    print(f'provider_models,{n},serialization_p95_ms,{percentile(serialization, 0.95):.6f}')
    print(f'provider_models,{n},http_p50_ms,{percentile(http_latencies, 0.50):.6f}')
    print(f'provider_models,{n},http_p95_ms,{percentile(http_latencies, 0.95):.6f}')
    print(f'provider_models,{n},http_mean_ms,{statistics.mean(http_latencies):.6f}')


if __name__ == '__main__':
    main()
