# Multi-Agent SDLC Orchestration System

A complete multi-agent system designed to manage the full cycle of software development. Each agent has a specialized role, and they collaborate through a shared task management system (**Beads**) and version control (**Git**). An **Orchestrator** coordinates the flow between agents based on project state.

## Core Components

- **Orchestrator**: The central controller that analyzes project state and decides which agent to activate next.
- **Agents**: Specialized AI agents (Requirements Analyst, Architect, Developer, Tester, etc.) that perform specific SDLC tasks.
- **Beads**: A task-tracking and project management tool for agent coordination.
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
│   ├── main.py             # Main entry point for the orchestrator
│   ├── agents.py           # Agent definitions and registry
│   ├── beads.py            # Beads integration logic
│   ├── config.py           # Configuration management
│   ├── service.py          # Orchestration service layer
│   └── utils.py            # Shared utility functions
├── tests/                  # Comprehensive test suite
├── AGENTS.md               # Detailed agent descriptions and prompts
├── multi_agent_sdlc_system.md # Theoretical overview of the system
├── orchestrate_sdlc.sh     # Convenient shell wrapper to run the system
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

### Usage

To start the multi-agent SDLC orchestration:

```bash
./orchestrate_sdlc.sh
```

This will activate the Orchestrator, which will start the SDLC process by evaluating the current state and invoking the appropriate agents.

## Workflow

1.  **Initialization**: The Orchestrator verifies prerequisites and initializes Beads.
2.  **Orchestration Cycle**:
    -   Orchestrator decides which agent to activate.
    -   The chosen agent performs its task, updates Beads, and commits changes to Git.
    -   Orchestrator tags the iteration and proceeds to the next cycle.
3.  **Completion**: The process continues until the Orchestrator determines the project is complete.

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

---
