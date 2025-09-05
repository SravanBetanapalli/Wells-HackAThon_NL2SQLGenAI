#!/bin/bash

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Remove existing virtual environment if it exists
rm -rf .venv

# Create new UV virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies using UV
uv pip install -e .

# Install dev dependencies
uv pip install pytest pytest-cov black isort mypy ruff

echo "✅ UV environment setup complete!"
echo "To activate the environment, run: source .venv/bin/activate"
