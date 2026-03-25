# Message-Driven Multi-Agent SDLC System

A complete multi-agent system designed to manage the full cycle of software development. Each agent has a specialized role, and they collaborate through **inter-agent messages** managed by a **JSONL-based message broker**.

## Core Components

- **Message-Driven Activation**: Agents are selected by SDLC role order.
- **Agents**: Specialized AI agents (Requirements Analyst, Architect, Developer, Tester, etc.) that perform specific SDLC tasks.
- **Broker**: A lightweight JSONL-based message broker (`tools/broker`) for inter-agent communication.
- **Memory**: A JSONL-based memory tool (`tools/memory`) for unified knowledge storage (tasks, decisions, metrics).
- **Git**: Version control for code and documentation.

## Agent Roles

1.  **Requirements Analyst**: Gathers, analyzes, and refines project requirements.
2.  **Architect/Designer**: Designs system architecture, data models, and component structures.
3.  **Developer**: Implements the design and writes code according to specifications.
4.  **Tester**: Verifies code quality, functionality, and compliance with requirements.
5.  **Deployer**: Prepares and executes deployment to production/staging environments.
6.  **Maintainer/Reviewer**: Monitors the system, handles incidents, and performs code reviews.
7.  **Documentation Specialist**: Maintains comprehensive documentation for all stakeholders.
8.  **Refiner/Improvement Agent**: Analyzes project status and identifies improvement opportunities.
9.  **Git Maintainer**: Ensures repository hygiene and prepares for new iterations.

## Project Structure

```text
/
├── src/orchestrator/       # Core Python implementation
│   ├── main.py             # Main entry point (message-driven loop)
│   ├── agents.py           # Agent definitions and prompts
│   ├── broker_wrapper.py   # Broker integration logic
│   ├── memory_wrapper.py   # Memory integration logic
│   ├── config.py           # Configuration management
│   ├── service.py          # Orchestration service layer
│   └── utils.py            # Shared utility functions
├── tools/
│   ├── broker              # Shell-based message broker
│   └── memory              # Shell-based memory tool
├── tests/                  # Comprehensive test suite (99% coverage)
├── multi_agent_sdlc_system.md # Detailed agent prompts and system documentation
├── orchestrate_sdlc.sh     # Shell wrapper to run the system
├── AGENTS.md               # Agent instructions (broker usage)
└── README.md               # This file
```

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv) - Fast Python package and project manager.
- [jq](https://stedolan.github.io/jq/) - Command-line JSON processor (used by broker).
- Git - Version control.
- Bash - Shell environment for broker script.
- At least one CLI agent installed (see below).

### CLI Agent Configuration

**Important**: CLI agents must be configured to run in **non-interactive mode**. The orchestrator invokes agents with predefined flags to avoid hanging on confirmation prompts.

The following CLI agents are supported with their default flags:

| Agent | Default Flags | Description |
|-------|---------------|-------------|
| `opencode` | `run` | Runs in execution mode |
| `gemini` | `-y -p` | Auto-confirm and prompt mode |
| `qwen` | `-y` | Auto-confirm |
| `cline` | `-a -y` | Auto-accept and auto-confirm |
| `codex` | `--full-auto exec --skip-git-repo-check` | Full automation mode |

**Before using this project**, verify your preferred CLI agent works in non-interactive mode:

```bash
# Example for opencode - test code editing and shell execution
opencode run "Create a Python hello world script and run it"

# Example for gemini
gemini -y -p "Create a Python hello world script and run it"

# Example for qwen  
qwen -y "Create a Python hello world script and run it"
```

If the agent prompts for permissions or hangs, consult its documentation to configure non-interactive mode. The orchestrator expects agents to execute tasks autonomously without user intervention.

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd orchestrator
    ```

2.  Install dependencies and set up the environment:
    ```bash
    uv sync
    ```

3.  Ensure tools are executable:
    ```bash
    chmod +x tools/broker tools/memory
    ```

### Usage

The system can be run from any directory by calling the script with its full path:

```bash
/path/to/orchestrator/orchestrate_sdlc.sh [--max-iterations N]
```

This will start the message-driven SDLC process in your current working directory.

## Workflow

1.  **Initialization**: The system verifies prerequisites (Git, broker, memory tool, required CLI agents) and ensures a `specs.md` file exists.
2.  **Bootstrap**: One initial message is created for each agent role using `broker send`.
3.  **Message-Driven Cycle**:
    -   System selects agent with SDLC role order.
    -   The chosen agent receives enriched context (including `$BROKER_PATH` and `$MEMORY_PATH`), and calls tools directly:
        -   `broker read/send/ack` - handle communication
        -   `memory search/create/list/update` - manage knowledge
    -   System commits changes and tags iteration.
    -   Cycle repeats with the next agent selection.
4.  **Completion**: The process terminates when no pending messages remain (all messages processed) or max iterations is reached.

## Inter-Agent Messaging

Agents communicate through structured messages stored in `messages.jsonl`:

### Broker Commands

**Read Messages:**
```bash
$BROKER_PATH read "Agent Name"
$BROKER_PATH read "Agent Name" --all   # Include acknowledged
```

**Send Messages:**
```bash
$BROKER_PATH send --from "Developer" --to "Tester" --content "Code ready for testing"
```

**Acknowledge Messages:**
```bash
$BROKER_PATH ack msg_1234567890_a1b2c3d4
$BROKER_PATH ack msg_id1 msg_id2 msg_id3   # Multiple at once
```

### Knowledge Management (Memory)

Agents maintain shared state through the memory tool:

**Create Memory Item:**
```bash
$MEMORY_PATH create "Architectural Decision" --type decision --content "Use PostgreSQL"
```

**Search Memory:**
```bash
$MEMORY_PATH search "database"
```

### Context Injection

Agents receive enriched context in their activation:
- **Broker**: `$BROKER_PATH` (absolute path) + current message state summary.
- **Memory**: `$MEMORY_PATH` (absolute path) + current memory state summary (counts, blockers, metrics).
- **Onboard**: Full `onboard` documentation for BOTH broker and memory tools.
- **Iteration**: `$MEMORY_ITERATION` environment variable.

## Agent Selection Algorithm

1. First agent with pending (unacknowledged) messages
2. Use SDLC role order:
   1. Requirements Analyst
   2. Architect/Designer
   3. Developer
   4. Tester
   5. Deployer
   6. Maintainer/Reviewer
   7. Refiner
   8. Git Maintainer
   9. Documentation Specialist

## Collaboration and Persistence

This system is designed for multi-agent collaboration and long-term memory:

- **Message Persistence**: Messages stored in `messages.jsonl` (JSONL format with flock locking)
- **Git Integration**: All changes committed and tagged per iteration

## Testing

The system has comprehensive test coverage:

```bash
# Run tests with coverage
PYTHONPATH=src uv run pytest --cov=src/orchestrator --cov-report=term-missing

# Current coverage: 99% (125 tests)
```

## Architecture Notes

### Key Design Decisions

- **Absolute broker path**: `$BROKER_PATH` in context ensures agents work from any directory
- **Agent autonomy**: Each agent responsible for its own message handling

---
