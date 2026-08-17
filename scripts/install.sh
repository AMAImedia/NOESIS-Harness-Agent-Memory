#!/usr/bin/env bash
# install.sh - Install NOESIS-Harness-Agent-Memory locally

set -euo pipefail

echo "Installing NOESIS-Harness-Agent-Memory..."

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.9"
if [[ $(echo "$python_version < $required_version" | bc -l) -eq 1 ]]; then
    echo "Error: Python $required_version+ required, found $python_version"
    exit 1
fi

echo "Python $python_version OK"

# Install in development mode
pip install -e .

# Run tests to verify
python -m unittest discover -s tests -v

echo "Installation complete!"
echo "Run examples: python examples/botfarm_lead.py"
echo "Run benchmarks: python benchmarks/run_bench.py --all"