#!/usr/bin/env bash
# make_release.sh - Build and package release

set -euo pipefail

VERSION=$(grep '^version = ' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')
echo "Building release $VERSION..."

# Clean
rm -rf dist build *.egg-info

# Run tests
python -m unittest discover -s tests -q

# Build
python -m build

# Verify
echo "Built artifacts:"
ls -la dist/

# Check package
python -m pip check

echo "Release $VERSION built successfully!"
echo "To upload: twine upload dist/*"