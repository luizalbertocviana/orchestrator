#!/bin/bash
# Wrapper script to run the Python-based SDLC Orchestrator via uv

# Ensure we are in the project root
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Run the orchestrator via uv
# We set PYTHONPATH to src to allow imports to work correctly
PYTHONPATH=src uv run src/orchestrator/main.py run "$@"
