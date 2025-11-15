#!/bin/bash
# Quick script to run hospital CLI commands with proper environment

# Activate virtual environment
source .venv/bin/activate

# Set Python path
export PYTHONPATH="$(pwd):$(pwd)/provider"

# Run the command passed as arguments
python -m provider.hospital.cli "$@"
