"""Run the local NOESIS control plane with declarative demo metadata only."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from noesis_harness.health_server import HealthServer
from noesis_harness.provider_registry import ModelDescriptor, ProviderDescriptor, ProviderRegistry


def demo_registry() -> ProviderRegistry:
    return ProviderRegistry((
        ProviderDescriptor(
            provider_id="local-demo",
            kind="openai_compatible",
            status="ready",
            models=(ModelDescriptor(
                model_id="local-demo-model",
                provider="openai_compatible",
                endpoint_kind="demo-metadata-only",
                capabilities={"tools": False, "vision": False, "structured_output": True},
            ),),
        ),
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NOESIS local read-only control plane")
    parser.add_argument("--host", default="127.0.0.1", help="loopback host; non-loopback is rejected")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--empty-registry", action="store_true", help="show explicit unavailable provider state")
    args = parser.parse_args()
    registry = ProviderRegistry() if args.empty_registry else demo_registry()
    server = HealthServer(host=args.host, port=args.port, provider_registry=registry)
    server.start()
    print(f"NOESIS control plane listening at http://{server.address[0]}:{server.address[1]}", flush=True)
    print("GET /health and GET /models are read-only; press Ctrl+C to stop.", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()


if __name__ == "__main__":
    main()
