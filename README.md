# Message-Driven Multi-Agent SDLC System

A complete multi-agent system designed to manage the full cycle of software development. Each agent has a specialized role, and they collaborate through **inter-agent messages** managed by a **JSONL-based message broker**. Agents are activated based on message demand—whichever agent has the most pending messages gets selected next.

## Core Components

- **Message-Driven Activation**: Agents are selected dynamically based on pending message count, with tie-breaking by SDLC role order.
- **Agents**: Specialized AI agents (Requirements Analyst, Architect, Developer, Tester, etc.) that perform specific SDLC tasks.
- **Broker**: A lightweight JSONL-based message broker (`tools/broker`) for inter-agent communication.
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
│   ├── config.py           # Configuration management
│   ├── service.py          # Orchestration service layer
│   └── utils.py            # Shared utility functions
├── tools/
│   └── broker              # Shell-based message broker
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

3.  Ensure broker script is executable:
    ```bash
    chmod +x tools/broker
    ```

### Usage

The system can be run from any directory by calling the script with its full path:

```bash
/path/to/orchestrator/orchestrate_sdlc.sh [--max-iterations N]
```

This will start the message-driven SDLC process in your current working directory.

## Workflow

1.  **Initialization**: The system verifies prerequisites (Git, broker script, required CLI agents) and ensures a `specs.md` file exists.
2.  **Bootstrap**: One initial message is created for each agent role using `broker send`.
3.  **Message-Driven Cycle**:
    -   System selects the agent with the most pending messages (tie-break by SDLC role order).
    -   The chosen agent receives context (including `$BROKER_PATH`), and calls broker directly:
        -   `broker read` - reads pending messages
        -   `broker send` - sends messages to other agents
        -   `broker ack` - acknowledges processed messages
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

### Message Schema

```json
{
  "id": "msg_<timestamp>_<random>",
  "from": "agent-name",
  "to": "agent-name",
  "content": "message body",
  "timestamp_sent": "ISO8601",
  "timestamp_ack": "ISO8601 or null"
}
```

### Agent Messaging Requirements

Agents **MUST**:
- Call `broker read` to retrieve messages at the start of each activation
- Act on the information/requests in messages
- Send **at least one** `broker send` message to another agent per activation
- Call `broker ack` to acknowledge ALL processed messages

### Context Injection

Agents receive `$BROKER_PATH` in their context—an absolute path to the broker script. This ensures agents can call the broker from any working directory.

## Agent Selection Algorithm

1. Count pending (unacknowledged) messages per target agent
2. Select agent with highest count
3. If tie, use SDLC role order:
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

- **No MESSAGE:/MARK_READ: parsing**: Agents call broker directly, no output parsing needed
- **Absolute broker path**: `$BROKER_PATH` in context ensures agents work from any directory
- **Simplified orchestrator**: Only creates bootstrap messages and selects agents
- **Agent autonomy**: Each agent responsible for its own message handling

---
