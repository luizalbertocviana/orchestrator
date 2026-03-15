#!/usr/bin/env bash
# Wrapper script to run the Python-based SDLC Orchestrator via uv

# Store the current working directory (target project)
TARGET_PROJECT_DIR="$(pwd)"

# Get the orchestrator directory
ORCHESTRATOR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run the orchestrator via uv
# We set PYTHONPATH to src to allow imports to work correctly
# We change to the target project directory so messages.jsonl is created there
cd "$TARGET_PROJECT_DIR"
PYTHONPATH="$ORCHESTRATOR_DIR/src" uv run --project "$ORCHESTRATOR_DIR" "$ORCHESTRATOR_DIR/src/orchestrator/main.py" run "$@"
