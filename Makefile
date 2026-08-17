# Makefile for NOESIS-Harness-Agent-Memory

.PHONY: install test examples bench build clean release

# Default target
all: test

install:
	pip install -e .

test:
	python -m unittest discover -s tests -v

examples:
	python examples/botfarm_lead.py
	python examples/multi_agent_swarm.py
	python examples/memory_tiers.py
	python examples/dag_actions.py

bench:
	python benchmarks/run_bench.py --all

bench-quick:
	python benchmarks/memory_bench.py --n 1000

build:
	rm -rf dist build *.egg-info
	python -m build

clean:
	rm -rf dist build *.egg-info __pycache__ */__pycache__ tests/__pycache__
	find . -name "*.pyc" -delete

release: test
	@VERSION=$$(grep '^version = ' pyproject.toml | sed 's/.*"\(.*\)".*/\1/'); \
	echo "Building release $$VERSION..."; \
	rm -rf dist build *.egg-info; \
	python -m build; \
	echo "Release built!"; ls -la dist/

lint:
	pyflakes noesis_harness/ examples/ integrations/ benchmarks/

# Quick validation
check: test
	python -c "import noesis_harness; print('Import OK')"
	python examples/botfarm_lead.py
	python examples/multi_agent_swarm.py

# Install in development mode
develop:
	pip install -e .[dev]

# Run all integration tests
integration:
	python integrations/claude_code.py
	python integrations/codex.py
	python integrations/openclaw.py

# Run benchmarks
benchmark:
	python benchmarks/run_bench.py --all

# Full CI pipeline
ci: lint test bench build

# Default
.DEFAULT_GOAL := test