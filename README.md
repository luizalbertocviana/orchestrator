# Message-Driven Multi-Agent SDLC System

A complete multi-agent system designed to manage the full cycle of software development. Each agent has a specialized role, and they collaborate through **inter-agent messages** tracked in a shared task management system (**Beads**) and version control (**Git**). Agents are activated based on message demand—whichever agent has the most pending messages gets selected next.

## Core Components

- **Message-Driven Activation**: Agents are selected dynamically based on pending message count, with tie-breaking by SDLC role order.
- **Agents**: Specialized AI agents (Requirements Analyst, Architect, Developer, Tester, etc.) that perform specific SDLC tasks.
- **Beads**: A task-tracking and project management tool for agent coordination and message persistence.
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
│   ├── beads.py            # Beads integration logic
│   ├── config.py           # Configuration management
│   ├── service.py          # Orchestration service layer
│   └── utils.py            # Shared utility functions
├── tests/                  # Comprehensive test suite (96% coverage)
├── multi_agent_sdlc_system.md # Detailed agent prompts and system documentation
├── orchestrate_sdlc.sh     # Shell wrapper to run the system
└── README.md               # This file
```

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv) - Fast Python package and project manager.
- [beads](https://github.com/steveyegge/beads) - Task management for agents.
- Git - Version control.

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

3.  Initialize Beads in your project repository:
    ```bash
    # Navigate to your project directory (where you want to run the SDLC)
    bd init
    ```

### Usage

The system can be run from any directory by calling the script with its full path:

```bash
/path/to/orchestrator/orchestrate_sdlc.sh [--max-iterations N]
```

This will start the message-driven SDLC process in your current working directory.

## Workflow

1.  **Initialization**: The system verifies prerequisites (Git, Beads, required CLI agents) and ensures a `specs.md` file exists.
    -   **Note**: If Beads is not initialized, you will be prompted to run `bd init` manually.
2.  **Bootstrap**: One initial message is created for each agent role to kickstart the system.
3.  **Message-Driven Cycle**:
    -   System selects the agent with the most pending messages (tie-break by SDLC role order).
    -   The chosen agent receives messages in its context, processes them, and outputs:
        -   `MESSAGE: [AgentName]→[TargetAgent]: <content>` - sends messages to other agents
        -   `MARK_READ: beads-XXX` - marks processed messages as read
    -   System parses agent output, registers new messages, and closes read messages.
    -   Cycle repeats with the next agent selection.
4.  **Completion**: The process terminates when no pending messages remain (all messages processed) or max iterations is reached.

## Inter-Agent Messaging

Agents communicate through structured messages stored in Beads:

### Message Format (Agent Output)
```
MESSAGE: [YourAgentName]→[TargetAgent]: <content>
```

Example:
```
MESSAGE: [Developer]→[Tester]: Code ready for testing. Unit tests passing.
MESSAGE: [Tester]→[Developer]: BUG: Login fails with empty password.
```

### Mark Messages as Read
```
MARK_READ: beads-123, beads-124, beads-125
```

Agents **MUST**:
- Send at least one MESSAGE to another agent per activation
- Mark all processed messages as read using MARK_READ: with bead IDs

### Message Display in Agent Context
Agents receive messages in this format:
```
[beads-123] MESSAGE: [Architect/Designer]→[Developer]: API specs in docs/api.md.
[beads-124] MESSAGE: [Requirements Analyst]→[Developer]: Priority features in specs.md section 3.
```

## Agent Selection Algorithm

1. Count pending (unclosed) MESSAGE: beads per target agent
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

## Task Tracking with Beads

This project uses `beads` for all task tracking. Use the following commands to interact with the project state:

- `bd list`: List all tasks.
- `bd ready`: Show tasks ready for work.
- `bd show <id>`: Get details for a specific task.
- `bd prime`: Register project usage aspects (essential for agent context).

## Collaboration and Persistence

This system is designed for multi-agent collaboration and long-term memory:

- **Syncing**: Use `bd dolt pull` and `bd dolt push` to synchronize task state with a Dolt remote.
- **Memories**: Use `bd remember "insight"` to store persistent knowledge that agents can access in future sessions.
- **Search**: Use `bd memories <keyword>` to find stored insights.

## Testing

The system has comprehensive test coverage:

```bash
# Run tests with coverage
PYTHONPATH=src uv run pytest --cov=src/orchestrator --cov-report=term-missing

# Current coverage: 96% (65 tests)
```

---
