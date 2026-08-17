#!/usr/bin/env bash
# run_tests.sh - Run all tests with coverage

set -euo pipefail

echo "Running NOESIS-Harness-Agent-Memory tests..."

# Run unit tests
python -m unittest discover -s tests -v

# Run examples
echo "Running examples..."
python examples/botfarm_lead.py
python examples/multi_agent_swarm.py
python examples/memory_tiers.py
python examples/dag_actions.py

# Run integrations
echo "Running integration tests..."
python integrations/claude_code.py
python integrations/codex.py
python integrations/openclaw.py

# Run benchmarks (quick)
echo "Running benchmarks..."
python benchmarks/memory_bench.py --n 100

echo "All tests passed!"