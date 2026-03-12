# Message-Driven Multi-Agent Software Development Lifecycle (SDLC) System

## Overview
This document describes a complete multi-agent system designed to manage the full cycle of software development. Each agent has a specialized role, and they collaborate through **inter-agent messages** managed by a **JSONL-based message broker** and version control (**Git**).

**Key Architecture**: There is no central Orchestrator controlling message flow. Instead:
- Agents are activated based on **message demand**—whichever agent has the most pending messages gets selected next
- Agents communicate **directly via the broker script** (`tools/broker`)
- The orchestrator only creates bootstrap messages and selects which agent to activate

This creates a pull-based, decentralized workflow.

---

## Message-Driven Activation System

### How It Works

1. **Bootstrap**: At system startup, one initial message is created for each agent role using `broker send`.
2. **Selection**: The system counts pending (unacknowledged) messages per agent and selects the one with the most.
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
4. **Activation**: Selected agent receives context (including `$BROKER_PATH`), processes messages, and calls broker directly.
5. **Agent Actions**: Agents call broker commands directly:
   - `broker read` - to read their pending messages
   - `broker send` - to send messages to other agents
   - `broker ack` - to acknowledge processed messages
6. **Termination**: System stops when no pending messages remain or max iterations reached.

### Broker Commands

**Read Messages:**
```bash
$BROKER_PATH read "Agent Name"
$BROKER_PATH read "Agent Name" --all   # Include acknowledged messages
```

**Send Messages:**
```bash
$BROKER_PATH send --from "SenderAgent" --to "TargetAgent" --content "message content"
```

**Acknowledge Messages:**
```bash
$BROKER_PATH ack msg_1234567890_a1b2c3d4
$BROKER_PATH ack msg_id1 msg_id2 msg_id3   # Multiple at once
```

### Message Schema

Messages are stored as JSONL (JSON Lines) with this schema:
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

Every agent **MUST**:
1. Call `broker read` to retrieve messages addressed to them
2. Act on the information/requests in those messages
3. Call `broker ack` to acknowledge ALL processed messages
4. Call `broker send` to send **at least one** message to another agent role

---

## Agent Roles and Prompts

Each agent prompt includes:
- Role purpose and responsibilities
- Available agents table (for messaging decisions)
- Broker command instructions

### 1. Requirements Analyst

**Role Purpose:** Gather, analyze, and refine software requirements. Ensure clarity and completeness before design begins.

**Key Responsibilities:**
- Review specs.md and related documentation
- Identify functional and non-functional requirements
- Detect ambiguities, gaps, or conflicts
- Propose additional requirements for robustness

**Messaging:** Use broker to send messages to Architect/Designer (handoff), Documentation Specialist (document requirements), or other agents as needed.

---

### 2. Architect/Designer

**Role Purpose:** Design the system architecture, data models, and component structure based on finalized requirements.

**Key Responsibilities:**
- Review requirements from specs.md
- Design system architecture and data models
- Define API contracts and component diagrams
- Identify technology stack with justification

**Messaging:** Use broker to send messages to Developer (implementation tasks), Requirements Analyst (clarifications), or Documentation Specialist (architecture docs).

---

### 3. Developer

**Role Purpose:** Implement the design by writing code according to specifications and architecture.

**Key Responsibilities:**
- Review design documents and data models
- Implement code following architecture decisions
- Write clean, maintainable code with unit tests
- Report blockers or design issues

**Messaging:** Use broker to send messages to Tester (ready for testing), Architect/Designer (design clarifications), or other Developers (collaboration).

---

### 4. Tester

**Role Purpose:** Verify code quality, functionality, and compliance with requirements through comprehensive testing.

**Key Responsibilities:**
- Execute unit and integration tests
- Create test cases based on requirements
- Test edge cases and non-functional requirements
- Document bugs and issues found

**Messaging:** Use broker to send messages to Developer (bug reports), Deployer (ready for deployment), or Requirements Analyst (requirement clarifications).

---

### 5. Deployer

**Role Purpose:** Prepare the system for production deployment and manage the deployment process.

**Key Responsibilities:**
- Prepare deployment artifacts and configurations
- Set up staging and production environments
- Execute deployment with pre-checks
- Tag releases after successful deployment

**Messaging:** Use broker to send messages to Maintainer/Reviewer (handoff), Tester (deployment verification), or Documentation Specialist (deployment docs).

---

### 6. Maintainer/Reviewer

**Role Purpose:** Monitor, support, and maintain the deployed system. Handle issues, perform code reviews, and plan improvements.

**Key Responsibilities:**
- Monitor deployed system for issues
- Review production logs and respond to incidents
- Perform hot-fixes for critical issues
- Conduct code reviews and merge approved PRs

**Messaging:** Use broker to send messages to Developer (fixes needed), Refiner (improvement proposals), or Requirements Analyst (feature requests).

---

### 7. Documentation Specialist

**Role Purpose:** Create and maintain comprehensive documentation for developers, users, and operators.

**Key Responsibilities:**
- Create user-facing documentation and API docs
- Write technical documentation for developers
- Develop operational documentation and runbooks
- Ensure docs stay up-to-date with implementation

**Messaging:** Use broker to send messages to any agent for clarifications.

---

### 8. Refiner/Improvement Agent

**Role Purpose:** Analyze project status, identify improvement opportunities, and iterate on the system based on feedback and metrics.

**Key Responsibilities:**
- Review project lifecycle for technical debt
- Identify performance bottlenecks and weaknesses
- Propose iterative improvements and refactoring
- Prioritize improvements by impact and effort

**Messaging:** Use broker to send messages to Architect/Designer (architecture improvements), Developer (refactoring tasks), or Maintainer/Reviewer (priority decisions).

---

### 9. Git Maintainer

**Role Purpose:** Maintain repository hygiene, ensure master branch is checked out, and prepare the working state for the next iteration.

**Key Responsibilities:**
- Verify clean repository state
- Ensure master/main branch is checked out
- Create iteration tags to mark progress
- Report uncommitted changes or issues

**Messaging:** Use broker to send messages to any agent about uncommitted changes.

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│  SYSTEM START                                                │
│  ↓                                                           │
│  Create bootstrap messages via broker send                  │
│  ↓                                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MESSAGE-DRIVEN LOOP                                 │   │
│  │  ↓                                                   │   │
│  │  Count pending messages per agent                   │   │
│  │  ↓                                                   │   │
│  │  Select agent with most messages                    │   │
│  │  (tie-break by role order)                          │   │
│  │  ↓                                                   │   │
│  │  Activate agent with context (includes              │   │
│  │  $BROKER_PATH absolute path)                        │   │
│  │  ↓                                                   │   │
│  │  Agent calls broker directly:                       │   │
│  │  - broker read (get messages)                       │   │
│  │  - broker send (send messages)                      │   │
│  │  - broker ack (acknowledge processed)               │   │
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

### Broker Commands
- `broker send --from <agent> --to <agent> --content <msg>` - Send a message
- `broker read <agent>` - Read pending messages for an agent
- `broker read <agent> --all` - Read all messages (including acknowledged)
- `broker ack <msg_id>...` - Acknowledge one or more messages
- `broker onboard` - Show usage instructions

### Git Commands
- `git status` - Check repository state
- `git add/commit/push` - Version control
- `git tag` - Mark iterations

### Message Storage
- Messages stored in `messages.jsonl` (JSONL format)
- File location configurable via `MESSAGES_FILE` environment variable
- Uses flock for concurrent access safety

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
- **Direct Broker Access**: Agents call broker commands directly
- **Explicit Acknowledgment**: Agents acknowledge messages with `broker ack`
- **Absolute Paths**: `$BROKER_PATH` in context ensures agents can find broker from any directory
- **Graceful Termination**: System stops when no messages remain

**Tools:**
- `broker` (tools/broker): JSONL-based message broker for inter-agent communication
- `git`: Version control and collaboration
- AI agents: opencode, gemini, qwen, cline, codex (configured in config.py)

**Configuration:**
- `required_tools`: ["git", "jq"] (broker is a project script, not a system tool)
- Broker path computed dynamically from project root
