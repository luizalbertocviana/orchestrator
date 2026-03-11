# Message-Driven Multi-Agent Software Development Lifecycle (SDLC) System

## Overview
This document describes a complete multi-agent system designed to manage the full cycle of software development. Each agent has a specialized role, and they collaborate through **inter-agent messages** tracked in a shared task management system (**beads**) and version control (**Git**). 

**Key Architecture Change**: There is no central Orchestrator. Instead, agents are activated based on **message demand**—whichever agent has the most pending messages gets selected next. This creates a pull-based, decentralized workflow.

---

## Message-Driven Activation System

### How It Works

1. **Bootstrap**: At system startup, one initial message is created for each agent role.
2. **Selection**: The system counts pending (unclosed) messages per agent and selects the one with the most.
3. **Tie-Breaking**: If multiple agents have the same count, use SDLC role order:
   1. Requirements Analyst
   2. Architect/Designer
   3. Developer
   4. Tester
   5. Deployer
   6. Maintainer/Reviewer
   7. Refiner
   8. Git Maintainer
   9. Documentation Specialist
4. **Activation**: Selected agent receives messages in context, processes them, and outputs responses.
5. **Message Parsing**: System parses agent output for:
   - `MESSAGE: [Agent]→[Target]: content` - registers new messages
   - `MARK_READ: beads-XXX` - closes processed messages
6. **Termination**: System stops when no pending messages remain or max iterations reached.

### Message Format

**Sending Messages (in agent output):**
```
MESSAGE: [YourAgentName]→[TargetAgent]: <content>
```

**Marking Messages as Read (in agent output):**
```
MARK_READ: beads-123, beads-124, beads-125
```

**Message Display in Agent Context:**
```
[beads-123] MESSAGE: [Architect/Designer]→[Developer]: API specs in docs/api.md.
[beads-124] MESSAGE: [Requirements Analyst]→[Developer]: Priority features in specs.md section 3.
```

### Agent Messaging Requirements

Every agent **MUST**:
1. Review all messages addressed to them in their context
2. Act on the information/requests in those messages
3. Mark ALL processed messages as read using `MARK_READ: beads-<id>`
4. Send **at least one** `MESSAGE:` to another agent role

---

## Agent Roles and Prompts

Each agent prompt includes:
- Role purpose and responsibilities
- Available agents table (for messaging decisions)
- Inter-agent messaging instructions

### 1. Requirements Analyst

**Role Purpose:** Gather, analyze, and refine software requirements. Ensure clarity and completeness before design begins.

**Key Responsibilities:**
- Review specs.md and related documentation
- Identify functional and non-functional requirements
- Detect ambiguities, gaps, or conflicts
- Propose additional requirements for robustness

**Messaging:** Send messages to Architect/Designer (handoff), Documentation Specialist (document requirements), or other agents as needed.

---

### 2. Architect/Designer

**Role Purpose:** Design the system architecture, data models, and component structure based on finalized requirements.

**Key Responsibilities:**
- Review requirements from specs.md
- Design system architecture and data models
- Define API contracts and component diagrams
- Identify technology stack with justification

**Messaging:** Send messages to Developer (implementation tasks), Requirements Analyst (clarifications), or Documentation Specialist (architecture docs).

---

### 3. Developer

**Role Purpose:** Implement the design by writing code according to specifications and architecture.

**Key Responsibilities:**
- Review design documents and data models
- Implement code following architecture decisions
- Write clean, maintainable code with unit tests
- Report blockers or design issues

**Messaging:** Send messages to Tester (ready for testing), Architect/Designer (design clarifications), or other Developers (collaboration).

---

### 4. Tester

**Role Purpose:** Verify code quality, functionality, and compliance with requirements through comprehensive testing.

**Key Responsibilities:**
- Execute unit and integration tests
- Create test cases based on requirements
- Test edge cases and non-functional requirements
- Document bugs and issues found

**Messaging:** Send messages to Developer (bug reports), Deployer (ready for deployment), or Requirements Analyst (requirement clarifications).

---

### 5. Deployer

**Role Purpose:** Prepare the system for production deployment and manage the deployment process.

**Key Responsibilities:**
- Prepare deployment artifacts and configurations
- Set up staging and production environments
- Execute deployment with pre-checks
- Tag releases after successful deployment

**Messaging:** Send messages to Maintainer/Reviewer (handoff), Tester (deployment verification), or Documentation Specialist (deployment docs).

---

### 6. Maintainer/Reviewer

**Role Purpose:** Monitor, support, and maintain the deployed system. Handle issues, perform code reviews, and plan improvements.

**Key Responsibilities:**
- Monitor deployed system for issues
- Review production logs and respond to incidents
- Perform hot-fixes for critical issues
- Conduct code reviews and merge approved PRs

**Messaging:** Send messages to Developer (fixes needed), Refiner (improvement proposals), or Requirements Analyst (feature requests).

---

### 7. Documentation Specialist

**Role Purpose:** Create and maintain comprehensive documentation for developers, users, and operators.

**Key Responsibilities:**
- Create user-facing documentation and API docs
- Write technical documentation for developers
- Develop operational documentation and runbooks
- Ensure docs stay up-to-date with implementation

**Messaging:** Send messages to any agent for clarifications, or to all agents (→[All]) for documentation requests.

---

### 8. Refiner/Improvement Agent

**Role Purpose:** Analyze project status, identify improvement opportunities, and iterate on the system based on feedback and metrics.

**Key Responsibilities:**
- Review project lifecycle for technical debt
- Identify performance bottlenecks and weaknesses
- Propose iterative improvements and refactoring
- Prioritize improvements by impact and effort

**Messaging:** Send messages to Architect/Designer (architecture improvements), Developer (refactoring tasks), or Maintainer/Reviewer (priority decisions).

---

### 9. Git Maintainer

**Role Purpose:** Maintain repository hygiene, ensure master branch is checked out, and prepare the working state for the next iteration.

**Key Responsibilities:**
- Verify clean repository state
- Ensure master/main branch is checked out
- Create iteration tags to mark progress
- Report uncommitted changes or issues

**Messaging:** Send messages to any agent about uncommitted changes, or to all agents (→[All]) for repository status updates.

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│  SYSTEM START                                                │
│  ↓                                                           │
│  Create bootstrap message to each agent                     │
│  ↓                                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MESSAGE-DRIVEN LOOP                                 │   │
│  │  ↓                                                   │   │
│  │  Count pending messages per agent                   │   │
│  │  ↓                                                   │   │
│  │  Select agent with most messages                    │   │
│  │  (tie-break by role order)                          │   │
│  │  ↓                                                   │   │
│  │  Activate agent with messages in context            │   │
│  │  ↓                                                   │   │
│  │  Parse agent output:                                │   │
│  │  - MESSAGE: → register new messages                 │   │
│  │  - MARK_READ: → close processed messages            │   │
│  │  ↓                                                   │   │
│  │  Commit changes, tag iteration                      │   │
│  │  ↓                                                   │   │
│  │  Repeat until no pending messages                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ↓                                                           │
│  SYSTEM COMPLETE                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Tool Usage

### Beads Commands
- `bd list` - List all tasks/messages
- `bd ready` - Show tasks ready for work
- `bd show <id>` - Get details for specific task
- `bd prime` - Register project context for agents

### Git Commands
- `git status` - Check repository state
- `git add/commit/push` - Version control
- `git tag` - Mark iterations

---

## Summary

**Agent Roles (9 total):**
1. Requirements Analyst
2. Architect/Designer
3. Developer
4. Tester
5. Deployer
6. Maintainer/Reviewer
7. Documentation Specialist
8. Refiner
9. Git Maintainer

**Key Principles:**
- **No Orchestrator**: Decentralized, message-driven activation
- **Pull-Based**: Agents activated by message demand
- **Mandatory Messaging**: Every agent must send at least one message
- **Explicit Acknowledgment**: Agents mark messages as read with MARK_READ:
- **Graceful Termination**: System stops when no messages remain

**Tools:**
- `bd` (beads): Task tracking and message persistence
- `git`: Version control and collaboration
- AI agents: opencode, gemini, qwen, cline, codex (configured in config.py)
