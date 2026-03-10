#!/bin/bash

################################################################################
# Multi-Agent SDLC Orchestration Script
# 
# Purpose: Orchestrate a full software development lifecycle using multiple AI
# agents, coordinated through a shared task management system (beads) and Git.
#
# Usage: ./orchestrate_sdlc.sh
#
# Requirements:
#   - Git repository initialized in current directory
#   - 'bd' (beads) command available in PATH
#   - agent command command available in PATH for AI agent interaction
#   - specs.md file present for project specifications
#
################################################################################

set -o pipefail

################################################################################
# CONFIGURATION & CONSTANTS
################################################################################

readonly MAX_RETRIES=3
readonly MAX_ITERATIONS=24  # Prevent infinite loops
readonly AGENT_TIMEOUT_LIMIT=1200s
readonly AGENT_COMMAND="qwen"
readonly AGENT_NONINTERACTIVE_PARAM="-y"


# Color codes for output
readonly COLOR_RESET='\033[0m'
readonly COLOR_BOLD='\033[1m'
readonly COLOR_GREEN='\033[32m'
readonly COLOR_YELLOW='\033[33m'
readonly COLOR_RED='\033[31m'
readonly COLOR_BLUE='\033[34m'

################################################################################
# UTILITY FUNCTIONS
################################################################################

# Print colored output
print_status() {
  local color="$1"
  local label="$2"
  local message="$3"

  local timestamp
  timestamp=$(date +"%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u +"%Y-%m-%d %H:%M:%S")

  printf "${color}${timestamp} [${label}] ${message}${COLOR_RESET}\n" >&2
}

print_info() {
  print_status "$COLOR_BLUE" "INFO" "$1"
}

print_success() {
  print_status "$COLOR_GREEN" "SUCCESS" "$1"
}

print_warning() {
  print_status "$COLOR_YELLOW" "WARNING" "$1"
}

print_error() {
  print_status "$COLOR_RED" "ERROR" "$1"
}

print_header() {
  local title="$1"
  printf "${COLOR_BOLD}\n========== $title ==========${COLOR_RESET}\n" >&2
}

# Verify that required tools are available
verify_tools() {
  local tools=("git" "bd" "jq" "$AGENT_COMMAND")
  local missing=()

  for tool in "${tools[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
      missing+=("$tool")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    print_error "Missing required tools: ${missing[*]}"
    return 1
  fi

  return 0
}

# Verify we're in a Git repository
verify_git_repo() {
  if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a Git repository. Please initialize one."
    return 1
  fi
  return 0
}

# Verify specs.md exists
verify_specs_file() {
  if [[ ! -f "specs.md" ]]; then
    print_warning "specs.md not found. Creating template."
    create_specs_template
  fi
}

# Create a template specs.md if it doesn't exist
create_specs_template() {
  cat > specs.md << 'EOF'
# Project Specifications

## Overview
[Describe the project briefly]

## Requirements

### Functional Requirements
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

### Non-Functional Requirements
- [Performance requirement]
- [Scalability requirement]
- [Security requirement]

## Technology Stack
[To be determined during design phase]

## Architecture Overview
[To be determined during design phase]

## Timeline & Milestones
[To be updated as project progresses]

EOF
  print_success "Created specs.md template"
}

# Initialize beads task system
initialize_beads() {
  print_info "Initializing beads task system"
  
  # Create initial task if none exists
  if ! bd list > /dev/null 2>&1 || [[ -z "$(bd list)" ]]; then
    bd init
    bd create "Phase: Requirements Analysis - Review and refine specs.md"
    print_success "Initial bead task created"
  else
    print_info "Beads system already initialized"
  fi
}

# Get current beads state
get_beads_state() {
  bd list 2>/dev/null || echo ""
}

# Get current git status
get_git_status() {
  git status --short 2>/dev/null || echo ""
}

# Get recent git commits
get_git_log() {
  git log --oneline -5 2>/dev/null || echo ""
}

# Check if there are any critical errors or blockers in beads
check_for_blockers() {
  local beads_output
  beads_output=$(get_beads_state)

  if echo "$beads_output" | grep -i -E "(BLOCKER|CRITICAL|ERROR)" > /dev/null; then
    return 0  # Blockers found
  fi
  return 1  # No blockers
}

################################################################################
# MESSAGING SYSTEM FUNCTIONS
################################################################################

# Send a message to another agent via beads
# Usage: send_message "from_agent" "to_agent" "message_content"
send_message() {
  local from_agent="$1"
  local to_agent="$2"
  local message="$3"
  local timestamp
  timestamp=$(date +"%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u +"%Y-%m-%d %H:%M:%S")
  
  local formatted_message="MESSAGE: [${timestamp}] ${from_agent}→${to_agent}: ${message}"
  bd create "$formatted_message" 2>/dev/null
  local exit_code=$?
  
  if [[ $exit_code -eq 0 ]]; then
    print_info "Message sent: ${from_agent}→${to_agent}"
    return 0
  else
    print_warning "Failed to send message: ${from_agent}→${to_agent}"
    return 1
  fi
}

# Read all messages from beads
# Returns: filtered list of MESSAGE beads
get_all_messages() {
  local beads_output
  beads_output=$(bd list 2>/dev/null || echo "")
  
  if [[ -n "$beads_output" ]]; then
    echo "$beads_output" | grep "^.*MESSAGE:" || echo ""
  else
    echo ""
  fi
}

# Get messages addressed to a specific agent
# Usage: get_messages_for_agent "agent_name"
get_messages_for_agent() {
  local target_agent="$1"
  local all_messages
  all_messages=$(get_all_messages)
  
  if [[ -n "$all_messages" ]]; then
    # Match messages addressed to the target agent
    echo "$all_messages" | grep -i "→${target_agent}" || echo ""
  else
    echo ""
  fi
}

# Get messages from a specific agent
# Usage: get_messages_from_agent "agent_name"
get_messages_from_agent() {
  local source_agent="$1"
  local all_messages
  all_messages=$(get_all_messages)
  
  if [[ -n "$all_messages" ]]; then
    # Match messages sent by the source agent
    echo "$all_messages" | grep -i "${source_agent}→" || echo ""
  else
    echo ""
  fi
}

# Mark a message as read by closing the bead
# Usage: mark_message_read <bead_id>
mark_message_read() {
  local bead_id="$1"
  
  if [[ -n "$bead_id" ]]; then
    bd close "$bead_id" 2>/dev/null
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
      print_info "Message marked as read: ID $bead_id"
      return 0
    else
      print_warning "Failed to mark message as read: ID $bead_id"
      return 1
    fi
  else
    print_warning "No bead ID provided for mark_message_read"
    return 1
  fi
}

################################################################################
# AGENT INTERACTION FUNCTIONS
################################################################################

# Call an AI agent with a prompt and context
call_agent() {
  local agent_name="$1"
  local prompt="$2"
  local context="$3"
  
  local full_prompt
  full_prompt=$(cat <<EOF
$prompt

CURRENT PROJECT CONTEXT:
$context

Please proceed with your role and responsibilities.
EOF
)

  local attempt=1
  while [[ $attempt -le $MAX_RETRIES ]]; do
    print_info "Calling agent: $agent_name (attempt $attempt/$MAX_RETRIES)"
    
    local output
    output=$(timeout $AGENT_TIMEOUT_LIMIT $AGENT_COMMAND $AGENT_NONINTERACTIVE_PARAM "$full_prompt" 2>&1)
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]] && [[ -n "$output" ]]; then
      echo "$output"
      return 0
    fi
    
    print_warning "Agent call failed with exit code $exit_code"
    ((attempt++))
    
    if [[ $attempt -le $MAX_RETRIES ]]; then
      sleep 2  # Brief pause before retry
    fi
  done
  
  print_error "Agent $agent_name failed after $MAX_RETRIES attempts"
  return 1
}

# Commit changes to Git
commit_changes() {
  local agent_name="$1"
  local message="$2"
  
  git add -A 2>/dev/null || return 1
  
  # Only commit if there are changes
  if ! git diff --cached --quiet; then
    git commit -m "[$agent_name] $message" 2>/dev/null || return 1
    print_success "Changes committed: $message"
    return 0
  else
    print_info "No changes to commit"
    return 0
  fi
}

# Log action to beads
log_to_beads() {
  local message="$1"
  bd create "$message" 2>/dev/null || print_warning "Failed to log to beads: $message"
}

################################################################################
# AGENT PROMPTS
################################################################################

get_requirements_analyst_prompt() {
  cat << 'EOF'
You are the Requirements Analyst for a software development project.

Your responsibilities:
1. Review the project specification file (specs.md) and any related documentation.
2. Identify and clarify all functional and non-functional requirements.
3. Detect ambiguities, gaps, or conflicts in requirements.
4. Propose additional requirements for robustness (error handling, performance, security, scalability).

Instructions:
- Log findings and create tasks for downstream phases.
- Use Git to version control any updated documentation.
- Output your findings clearly, organized by category (functional, non-functional, security, performance).
- Highlight any clarifications or assumptions made.
- End by suggesting the next phase, but defer final decision to Orchestrator.

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Requirements Analyst]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Requirements Analyst" or "→[Requirements Analyst]"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Clarification requests to upstream agents
  - Handoff notifications to downstream agents
  - Blocker escalations to Orchestrator
  - Team-wide announcements (use →[All])
EOF
}

get_architect_prompt() {
  cat << 'EOF'
You are the Architect/Designer for a software development project.

Your responsibilities:
1. Review finalized requirements from specs.md.
2. Design the overall system architecture (monolithic, microservices, modular, etc.).
3. Define data models, database schemas, and API contracts.
4. Create component diagrams, sequence diagrams, or other design artifacts.
5. Identify technology stack and justify choices based on requirements.

Instructions:
- Create implementation tasks.
- Use Git to version control design documents.
- Provide clear system architecture overview and technology stack rationale.
- Break down design into implementable components with clear interfaces.
- Log completion when ready.
- End by suggesting the Development phase, but defer final decision to Orchestrator.

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Architect/Designer]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Architect" or "→[Architect/Designer]"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Clarification requests to upstream agents
  - Handoff notifications to downstream agents
  - Blocker escalations to Orchestrator
  - Team-wide announcements (use →[All])
EOF
}

get_developer_prompt() {
  cat << 'EOF'
You are the Developer for a software development project.

Your responsibilities:
1. Review design documents, architecture, and data models.
2. Implement code for assigned components/modules based on design specs.
3. Follow the technology stack and architecture decided by the Architect.
4. Write clean, well-commented, and maintainable code: clean code, object calisthenics, etc.
5. Create unit tests for your code as you develop.

Instructions:
- Use Git with meaningful commits.
- Present implemented code with explanations of key logic.
- List all modules/features completed.
- Report any blockers or design issues via beads.
- Log completion when ready.
- End by suggesting the Testing phase, but defer final decision to Orchestrator.

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Developer]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Developer" or "→[Developer]"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Clarification requests to upstream agents
  - Handoff notifications to downstream agents
  - Blocker escalations to Orchestrator
  - Team-wide announcements (use →[All])
EOF
}

get_tester_prompt() {
  cat << 'EOF'
You are the Tester for a software development project.

Your responsibilities:
1. Review implemented code from development branches.
2. Execute unit tests and verify code coverage.
3. Perform integration testing to ensure modules work together.
4. Create and run test cases based on requirements from specs.md.
5. Test edge cases, error handling, and non-functional requirements.
6. Document test results and any bugs or issues found.

Instructions:
- Use Git to version control tests.
- Provide comprehensive test report (unit test results, integration tests, functional tests).
- List all bugs found, categorized by severity (critical, major, minor).
- Log completion when ready.
- End by suggesting next phase (Deployment if all critical bugs resolved, else Development if major bugs found).

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Tester]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Tester" or "→[Tester]"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Clarification requests to upstream agents
  - Handoff notifications to downstream agents
  - Blocker escalations to Orchestrator
  - Team-wide announcements (use →[All])
EOF
}

get_deployer_prompt() {
  cat << 'EOF'
You are the Deployer for a software development project.

Your responsibilities:
1. Review tested and approved code from Testing phase.
2. Prepare deployment artifacts (binaries, containers, configuration files, etc.).
3. Set up deployment environment configs (staging, production).
4. Create deployment scripts and runbooks for consistency.
5. Perform pre-deployment checks (dependencies, configurations, security scans).
6. Execute deployment locally and verify functionality.

Instructions:
- Use Git to version control deployment configs.
- Try to deploy locally.
- Tag release after successful deployment: 'git tag -a v[version] -m "Release [version]"'.
- Document deployment process and any issues encountered.
- Provide deployment checklist and verification steps.
- Log completion when ready.
- End by suggesting Maintenance phase, but defer final decision to Orchestrator.

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Deployer]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Deployer" or "→[Deployer]"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Clarification requests to upstream agents
  - Handoff notifications to downstream agents
  - Blocker escalations to Orchestrator
  - Team-wide announcements (use →[All])
EOF
}

get_maintainer_prompt() {
  cat << 'EOF'
You are the Maintainer/Reviewer for a software development project.

Your responsibilities:
1. Monitor locally deployed system for performance, errors, and user issues.
2. Review logs for anomalies and errors.
3. Respond to incident reports and escalations.
4. Perform hot-fixes for critical issues.
5. Plan and prioritize maintenance tasks (refactoring, optimization, dependency updates).

Instructions:
- Use Git to handle code reviews and hotfixes.
- After review approval, merge: 'git checkout main && git merge [branch-name]'.
- Provide maintenance status report (issues resolved, improvements identified, code quality metrics).
- Log completion when ready.
- End by suggesting next phase (Refinement if improvements needed, else continue maintenance).

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Maintainer/Reviewer]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Maintainer" or "→[Maintainer/Reviewer]"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Clarification requests to upstream agents
  - Handoff notifications to downstream agents
  - Blocker escalations to Orchestrator
  - Team-wide announcements (use →[All])
EOF
}

get_refiner_prompt() {
  cat << 'EOF'
You are the Refiner/Improvement Agent for a software development project.

Your responsibilities:
1. Review the entire project lifecycle: code quality, architecture, testing coverage, performance.
2. Gather feedback from all agents.
3. Identify technical debt, performance bottlenecks, and architectural weaknesses.
4. Propose iterative improvements: refactoring, optimization, new features.
5. Prioritize improvements based on impact and effort.

Instructions:
- Use Git to document findings.
- Provide comprehensive project health report (code quality metrics, test coverage, performance).
- List identified improvements prioritized by impact.
- Recommend whether to continue maintenance, start new development cycle, or archive project.
- Log final status.
- End by suggesting next phase, but defer final decision to Orchestrator.

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Refiner]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Refiner" or "→[Refiner]"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Clarification requests to upstream agents
  - Handoff notifications to downstream agents
  - Blocker escalations to Orchestrator
  - Team-wide announcements (use →[All])
EOF
}

get_git_maintainer_prompt() {
  cat << 'EOF'
You are the Git Maintainer for a software development project.

Your responsibilities:
1. Verify the repository is in a clean state (no uncommitted changes).
2. Ensure the master branch is checked out for the next iteration.
3. Fetch from remote to stay aware of upstream changes (do not pull automatically).
4. Create iteration tags (e.g., iteration-1, iteration-2) to mark progress.
5. Ensure the master branch tells a coherent development story.

Instructions:
- Check complete git logs to ensure master branch tells a coherent development story.
- Check status: Run 'git status' to verify repository state.
- Checkout master: Run 'git checkout master' (or 'git checkout main' if that's the default).
- Fetch remote: Run 'git fetch' to update remote tracking branches.
- Create tags: Run 'git tag -a iteration-N -m "Iteration N completed"' where N is the iteration number.
- Report current branch and repository state.
- List any uncommitted changes or issues found.
- If uncommitted changes exist, DO NOT commit automatically; log to beads for Orchestrator decision.

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Git Maintainer]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Git Maintainer"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Clarification requests to upstream agents
  - Handoff notifications to downstream agents
  - Blocker escalations to Orchestrator
  - Team-wide announcements (use →[All])
EOF
}

get_documentation_specialist_prompt() {
  cat << 'EOF'
You are the Documentation Specialist for a software development project.

Your responsibilities:
1. Review implemented features, architecture, and deployment procedures.
2. Create user-facing documentation (guides, API documentation, tutorials).
3. Write technical documentation for developers (architecture docs, code comments, setup guides).
4. Develop operational documentation (deployment guides, troubleshooting, runbooks).
5. Ensure documentation is clear, complete, and up-to-date with current implementation.
6. Identify gaps in documentation and propose additions via beads.

Instructions:
- Use Git to version control all documentation.
- Create documentation incrementally as features are developed, not all at the end.
- Ensure API documentation matches actual implementation; flag discrepancies via beads.
- Request code comments from developers if code documentation is insufficient.
- Prioritize documentation for critical features and operational procedures.
- Log completion when ready.
- End by suggesting areas for future documentation improvements.

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Documentation Specialist]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Documentation Specialist" or "→[Documentation Specialist]"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Clarification requests to upstream agents
  - Handoff notifications to downstream agents
  - Blocker escalations to Orchestrator
  - Team-wide announcements (use →[All])
EOF
}

get_orchestrator_prompt() {
  cat << 'EOF'
You are the Orchestrator for a multi-agent software development system.

Your responsibilities:
1. Query current project state from beads to assess progress and blockers.
2. Determine which agent should be activated next based on phase completion and project needs.
3. Handle errors and recovery by identifying what went wrong and which agent can resolve it.
4. Monitor inter-agent messages to ensure communication flow.
5. Output the next agent to activate, or signal completion/halt.

AVAILABLE AGENTS:
- Requirements Analyst
- Architect/Designer
- Developer
- Tester
- Deployer
- Maintainer/Reviewer
- Documentation Specialist
- Refiner
- Git Maintainer
- Orchestrator

INTER-AGENT MESSAGING:
- Send messages: bd create "MESSAGE: [Orchestrator]→[TargetAgent]: <content>"
- Receive messages: Check bd list for entries containing "→Orchestrator"
- Acknowledge: Mark read messages as closed with bd close <id>
- Use messaging for:
  - Direct agent activation directives
  - Escalation responses to blocker reports
  - Team-wide announcements (use →[All])
  - Coordination instructions between agents

OUTPUT FORMAT:
- Output exactly one line: "NEXT_AGENT: [agent name]" to activate that agent
- Or "PROJECT_COMPLETE" when project is done
- Or "PROJECT_HALTED: [reason]" if unrecoverable error

Include brief rationale based on current state analysis.
EOF
}

################################################################################
# ORCHESTRATION LOGIC
################################################################################

# Build context for agent from current project state
# Usage: build_agent_context "agent_name"
build_agent_context() {
  local agent_name="$1"
  local beads_state
  local git_status
  local git_log
  local messages

  beads_state=$(get_beads_state)
  git_status=$(get_git_status)
  git_log=$(get_git_log)
  
  # Get messages addressed to this agent
  if [[ -n "$agent_name" ]]; then
    messages=$(get_messages_for_agent "$agent_name")
  else
    messages=""
  fi

  cat <<EOF
=== BEADS PRIME ===
$(bd prime)
=== BEADS TASKS ===
$beads_state

=== INTER-AGENT MESSAGES (addressed to you) ===
${messages:-No new messages}

=== GIT STATUS ===
$git_status

=== RECENT COMMITS ===
$git_log

=== PROJECT ROOT ===
$(pwd)
EOF
}

# Strip markdown formatting and common artifacts from text
# Usage: strip_markdown "$text"
strip_markdown() {
  local text="$1"
  
  # Remove bold markers (**) - must be done before single asterisk removal
  text=$(echo "$text" | sed 's/\*\*//g')
  # Remove italic markers (*) - standalone asterisks
  text=$(echo "$text" | sed 's/\*//g')
  # Remove underline markers (__ or _) only when used as formatting (at word boundaries)
  # Preserve underscores within identifiers like NEXT_AGENT
  text=$(echo "$text" | sed 's/\b__\b//g' | sed 's/\b_\b//g')
  # Remove inline code markers (`)
  text=$(echo "$text" | sed 's/`//g')
  # Remove extra whitespace
  text=$(echo "$text" | sed 's/[[:space:]]\+/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  
  echo "$text"
}

# Parse orchestrator output to determine next agent
# Robust to markdown formatting variations like **NEXT_AGENT:** or *NEXT_AGENT:*
parse_orchestrator_output() {
  local output="$1"
  local normalized_output
  
  # First, normalize the output by stripping markdown formatting
  normalized_output=$(strip_markdown "$output")
  
  # Check for project completion/halt signals first
  if echo "$normalized_output" | grep -i "PROJECT_COMPLETE" > /dev/null; then
    echo "PROJECT_COMPLETE"
    return 0
  elif echo "$normalized_output" | grep -i "PROJECT_HALTED" > /dev/null; then
    echo "PROJECT_HALTED"
    return 0
  fi
  
  # Try to extract NEXT_AGENT with flexible pattern matching
  # Matches: NEXT_AGENT: AgentName, NEXT_AGENT : AgentName, etc.
  local next_agent
  next_agent=$(echo "$normalized_output" | grep -ioE "NEXT_AGENT[[:space:]]*:[[:space:]]*[A-Za-z][A-Za-z/ ]*" | sed 's/.*NEXT_AGENT[[:space:]]*:[[:space:]]*//i' | head -1)
  
  if [[ -n "$next_agent" ]]; then
    # Trim any trailing whitespace
    next_agent=$(echo "$next_agent" | sed 's/[[:space:]]*$//')
    echo "$next_agent"
    return 0
  fi
  
  # Fallback: Try to find agent names directly from the known agent list
  # This handles cases where orchestrator outputs just the agent name without NEXT_AGENT prefix
  local known_agents=(
    "Requirements Analyst"
    "Architect/Designer"
    "Developer"
    "Tester"
    "Deployer"
    "Maintainer/Reviewer"
    "Documentation Specialist"
    "Refiner"
    "Git Maintainer"
  )
  
  for agent in "${known_agents[@]}"; do
    # Case-insensitive match, word boundary aware
    if echo "$normalized_output" | grep -qi "\\b${agent}\\b"; then
      # Prefer lines that look like directives (start with agent name or contain common directive words)
      local matched_line
      matched_line=$(echo "$normalized_output" | grep -i "\\b${agent}\\b" | head -1)
      if [[ -n "$matched_line" ]]; then
        echo "$agent"
        return 0
      fi
    fi
  done
  
  # No agent found
  echo ""
  return 1
}

# Activate appropriate agent based on orchestrator decision
activate_agent() {
  local agent_name="$1"
  local context="$2"
  local agent_output
  
  case "$agent_name" in
    "Requirements Analyst"|"analyst")
      agent_output=$(call_agent "Requirements Analyst" "$(get_requirements_analyst_prompt)" "$context")
      ;;
    "Architect"|"Designer"|"architect/designer"|"Architect/Designer")
      agent_output=$(call_agent "Architect/Designer" "$(get_architect_prompt)" "$context")
      ;;
    "Developer"|"developer")
      agent_output=$(call_agent "Developer" "$(get_developer_prompt)" "$context")
      ;;
    "Tester"|"tester")
      agent_output=$(call_agent "Tester" "$(get_tester_prompt)" "$context")
      ;;
    "Deployer"|"deployer")
      agent_output=$(call_agent "Deployer" "$(get_deployer_prompt)" "$context")
      ;;
    "Documentation Specialist"|"Documentation"|"documentation")
      agent_output=$(call_agent "Documentation Specialist" "$(get_documentation_specialist_prompt)" "$context")
      ;;
    "Maintainer"|"Maintainer/Reviewer"|"maintainer")
      agent_output=$(call_agent "Maintainer/Reviewer" "$(get_maintainer_prompt)" "$context")
      ;;
    "Refiner"|"Refinement"|"refiner")
      agent_output=$(call_agent "Refiner" "$(get_refiner_prompt)" "$context")
      ;;
    "Git Maintainer"|"git"|"git-maintainer"|"GitMaintainer")
      agent_output=$(call_agent "Git Maintainer" "$(get_git_maintainer_prompt)" "$context")
      ;;
    *)
      print_error "Unknown agent: $agent_name"
      return 1
      ;;
  esac
  
  # Return agent output
  if [[ -n "$agent_output" ]]; then
    echo "$agent_output"
    return 0
  else
    return 1
  fi
}

# Run orchestrator to determine next agent
run_orchestrator() {
  local context="$1"
  local orchestrator_output
  
  print_header "ORCHESTRATOR DECISION"
  
  orchestrator_output=$(call_agent "Orchestrator" "$(get_orchestrator_prompt)" "$context")
  
  if [[ $? -ne 0 ]]; then
    print_error "Orchestrator failed to execute"
    return 1
  fi
  
  print_info "Orchestrator output:\n$orchestrator_output"
  
  local next_agent
  next_agent=$(parse_orchestrator_output "$orchestrator_output")
  
  if [[ -z "$next_agent" ]]; then
    print_error "Could not parse orchestrator output"
    return 1
  fi
  
  echo "$next_agent"
  return 0
}

################################################################################
# MAIN ORCHESTRATION LOOP
################################################################################

main() {
  print_header "MULTI-AGENT SDLC ORCHESTRATION SYSTEM"
  
  # Verify prerequisites
  print_info "Verifying prerequisites..."
  verify_tools || exit 1
  verify_git_repo || exit 1
  verify_specs_file
  initialize_beads
  
  print_success "All prerequisites verified"
  
  # Main orchestration loop
  local iteration=0
  local project_status="RUNNING"

  while [[ "$project_status" == "RUNNING" ]] && [[ $iteration -lt $MAX_ITERATIONS ]]; do
    ((iteration++))
    print_header "ITERATION $iteration"

    # Build context for orchestrator (no agent-specific messages)
    local orchestrator_context
    orchestrator_context=$(build_agent_context "Orchestrator")

    # Get orchestrator decision
    local next_agent
    next_agent=$(run_orchestrator "$orchestrator_context")

    if [[ $? -ne 0 ]]; then
      print_error "Orchestrator decision failed"
      project_status="HALTED"
      break
    fi

    # Handle project completion or halt signals
    if [[ "$next_agent" == "PROJECT_COMPLETE" ]]; then
      print_header "PROJECT COMPLETION"
      print_success "All phases completed successfully!"

      # Final status
      local final_beads
      final_beads=$(get_beads_state)
      print_info "Final project state:\n$final_beads"

      project_status="COMPLETE"
      break
    fi

    if [[ "$next_agent" == "PROJECT_HALTED"* ]]; then
      print_error "Project halted: $next_agent"
      project_status="HALTED"
      break
    fi

    # Activate the determined agent
    print_header "ACTIVATING AGENT: $next_agent"
    
    # Build context specific to the activated agent (includes their messages)
    local agent_context
    agent_context=$(build_agent_context "$next_agent")
    
    local agent_output
    agent_output=$(activate_agent "$next_agent" "$agent_context")

    if [[ $? -ne 0 ]]; then
      print_error "Agent activation failed: $next_agent"
      log_to_beads "ERROR: Agent $next_agent failed. Iteration $iteration."

      # Continue to next iteration for error handling
      continue
    fi

    # Output agent results
    print_info "Agent $next_agent completed:\n$agent_output"

    # Attempt to commit changes
    commit_changes "$next_agent" "Completed phase" || print_warning "Could not commit changes"

    # Invoke Git Maintainer to ensure repository hygiene and checkout master
    print_header "GIT MAINTENANCE"
    local git_maintainer_context
    git_maintainer_context=$(build_agent_context "Git Maintainer")
    local git_maintainer_output
    git_maintainer_output=$(activate_agent "Git Maintainer" "$git_maintainer_context")
    
    if [[ $? -eq 0 ]] && [[ -n "$git_maintainer_output" ]]; then
      print_info "Git Maintainer completed:\n$git_maintainer_output"
      # Log git maintenance to beads
      log_to_beads "Git: Iteration $iteration - Repository maintenance completed"
    else
      print_warning "Git Maintainer failed - repository state may need attention"
      log_to_beads "GIT ISSUE: Git Maintainer failed during iteration $iteration"
    fi

    # Brief pause before next iteration
    sleep 1
  done
  
  # Print final status
  print_header "ORCHESTRATION FINAL STATUS"
  if [[ "$project_status" == "COMPLETE" ]]; then
    print_success "Project completed successfully after $iteration iterations"
    exit 0
  elif [[ "$project_status" == "HALTED" ]]; then
    print_error "Project halted after $iteration iterations"
    exit 1
  else
    print_error "Project reached maximum iterations ($MAX_ITERATIONS) without completion"
    exit 1
  fi
}

################################################################################
# SCRIPT ENTRY POINT
################################################################################

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
  exit $?
fi
