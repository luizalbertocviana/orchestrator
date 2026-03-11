#!/bin/bash
# Wrapper script to run the Python-based SDLC Orchestrator via uv

# Ensure we know the project root
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run the orchestrator via uv
# We set PYTHONPATH to src to allow imports to work correctly
# We use --project $DIR to ensure uv finds the project context
PYTHONPATH="$DIR/src" uv run --project "$DIR" "$DIR/src/orchestrator/main.py" run "$@"
