# Agent Instructions

**For AI Assistants working on THIS repository** (the orchestrator project).

This project uses a **message broker** (`tools/broker`) for inter-agent communication in the SDLC system.

**Note**: `bd` (beads) is used by **you (the AI assistant)** and human developers to track issues for THIS project. The SDLC agents (Requirements Analyst, Developer, etc.) do NOT use beads - they communicate exclusively via the broker.

## Quick Reference

### For SDLC Agent Communication (broker)
```bash
$BROKER_PATH read "Agent Name"           # Read your messages
$BROKER_PATH send --from X --to Y --content Z  # Send a message
$BROKER_PATH ack msg_id1 msg_id2         # Acknowledge messages
$BROKER_PATH onboard                     # Show usage instructions
```

### For Issue Tracking (bd)
```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work atomically
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var

---

## Inter-Agent Messaging with Broker

**IMPORTANT**: This project uses a **JSONL-based message broker** for inter-agent communication in the SDLC system.

### Why Broker?

- Lightweight: Shell script with no external dependencies (only `jq`)
- Simple: JSONL storage with flock-based locking
- Direct: Agents call broker commands directly
- Persistent: Messages stored in `messages.jsonl`

### Quick Start

**Read your messages:**
```bash
$BROKER_PATH read "Your Agent Name"
```

**Send a message:**
```bash
$BROKER_PATH send --from "Your Agent Name" --to "Target Agent" --content "message content"
```

**Acknowledge processed messages:**
```bash
$BROKER_PATH ack msg_1234567890_a1b2c3d4
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

### Workflow for SDLC Agents

1. **Receive context**: Your activation includes `$BROKER_PATH` (absolute path to broker script)
2. **Read messages**: Call `$BROKER_PATH read "Your Agent Name"` to get pending messages
3. **Process messages**: Act on the information/requests in messages
4. **Send messages**: Call `$BROKER_PATH send` to communicate with other agents
5. **Acknowledge**: Call `$BROKER_PATH ack` for ALL processed messages

### Important Rules

- ✅ Use broker for ALL inter-agent communication
- ✅ Read your messages at the start of each activation
- ✅ Send at least one message per activation
- ✅ Acknowledge ALL processed messages
- ✅ Use `$BROKER_PATH` from context (absolute path, works from any directory)
- ❌ Do NOT use MESSAGE:/MARK_READ: output patterns
- ❌ Do NOT use beads for inter-agent messages (bd is for issue tracking only)

---

## Issue Tracking with bd (beads)

**IMPORTANT**: `bd` (beads) is used by **you (the AI assistant)** and human developers to track issues for THIS orchestrator project. The SDLC agents (Requirements Analyst, Developer, Tester, etc.) do NOT use beads - they use the broker for inter-agent communication.

**This distinction matters:**
- **You (AI assistant)**: Use `bd` to track your work on THIS repository
- **SDLC agents**: Use `broker` to communicate while developing OTHER projects

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Version-controlled: Built on Dolt with cell-level merge
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Assistants

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs with git:

- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking (AI assistants and humans)
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

---

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

---

## Summary

**Two Systems:**
1. **Broker** (`tools/broker`): Inter-agent messaging for SDLC workflow
2. **bd (beads)**: Issue tracking for project management

**Key Commands:**
- `$BROKER_PATH read/send/ack`: Agent communication
- `bd ready/create/close`: Issue tracking
- `git pull/push`: Version control
