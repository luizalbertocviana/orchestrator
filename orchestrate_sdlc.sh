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
#   - 'opencode' command available in PATH for AI agent interaction
#   - specs.md file present for project specifications
#
################################################################################

set -o pipefail

################################################################################
# CONFIGURATION & CONSTANTS
################################################################################

readonly MAX_RETRIES=3
readonly MAX_ITERATIONS=20  # Prevent infinite loops

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
  local tools=("git" "bd" "opencode")
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

# Get list of blockers
list_blockers() {
  local beads_output
  beads_output=$(get_beads_state)
  echo "$beads_output" | grep -i -E "(BLOCKER|CRITICAL|ERROR)"
}

# Determine which phase is currently complete
get_completed_phases() {
  local beads_output
  beads_output=$(get_beads_state)
  echo "$beads_output" | grep -i "completed"
}

# Check if a specific phase is marked complete
is_phase_complete() {
  local phase_name="$1"
  local beads_output
  beads_output=$(get_beads_state)
  
  if echo "$beads_output" | grep -i "$phase_name" | grep -i "completed" > /dev/null; then
    return 0
  fi
  return 1
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
    output=$(opencode run "$full_prompt" 2>&1)
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
- Use 'bd create' to log findings and create tasks for downstream phases.
- Update beads status as you work using 'bd update [ID] "status"'.
- Use Git to version control any updated documentation: 'git checkout -b requirements/analysis', make changes, then 'git commit -m "Requirements: [summary]"' and 'git push origin requirements/analysis'.
- Output your findings clearly, organized by category (functional, non-functional, security, performance).
- Highlight any clarifications or assumptions made.
- Log completion to beads when ready: 'bd create "Requirement analysis completed. Ready for design phase."'
- End by suggesting the next phase, but defer final decision to Orchestrator.
EOF
}

get_architect_prompt() {
  cat << 'EOF'
You are the Architect/Designer for a software development project.

Your responsibilities:
1. Review finalized requirements from specs.md and completed requirement analysis beads.
2. Design the overall system architecture (monolithic, microservices, modular, etc.).
3. Define data models, database schemas, and API contracts.
4. Create component diagrams, sequence diagrams, or other design artifacts.
5. Identify technology stack and justify choices based on requirements.

Instructions:
- Use 'bd list' to check that requirements phase is complete.
- Create implementation tasks using 'bd create "Dev task: Implement [module]"' for each component.
- Use Git to version control design documents: 'git checkout -b design/architecture', add files, 'git commit -m "Design: [summary]"', 'git push origin design/architecture'.
- Provide clear system architecture overview and technology stack rationale.
- Break down design into implementable components with clear interfaces.
- Log completion when ready: 'bd create "System design completed. Ready for development phase."'
- End by suggesting the Development phase, but defer final decision to Orchestrator.
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
- Use 'bd list' to see all "Dev task:" beads assigned to development.
- Use 'bd update [ID] "in-progress"' when starting implementation of a module.
- Use 'bd update [ID] "completed"' when a module is ready for testing.
- Use Git with meaningful commits: 'git checkout -b dev/[feature-name]', develop, 'git commit -m "Dev: Implement [feature]"', 'git push origin dev/[feature-name]'.
- Present implemented code with explanations of key logic.
- List all modules/features completed.
- Report any blockers or design issues via beads: 'bd create "BLOCKER: [issue]"'.
- Log completion when ready: 'bd create "Code implementation completed. Ready for testing."'
- End by suggesting the Testing phase, but defer final decision to Orchestrator.
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
- Use 'bd list' to confirm all dev modules are marked "completed".
- Use 'bd create "BUG: [description]"' for each defect discovered.
- Use 'bd create "CRITICAL: [issue]"' for blockers that prevent deployment.
- Use 'bd create "TEST: [scenario]"' to document test runs.
- Use Git to version control tests: 'git checkout -b testing/[module-name]', add test scripts, 'git commit -m "Tests: [summary]"', 'git push origin testing/[module-name]'.
- Provide comprehensive test report (unit test results, integration tests, functional tests).
- List all bugs found, categorized by severity (critical, major, minor).
- Log completion when ready: 'bd create "Testing phase completed. [X] bugs found and logged."'
- End by suggesting next phase (Deployment if all critical bugs resolved, else Development if major bugs found).
EOF
}

get_deployer_prompt() {
  cat << 'EOF'
You are the Deployer for a software development project.

Your responsibilities:
1. Review tested and approved code from Testing phase.
2. Prepare deployment artifacts (binaries, containers, configuration files, etc.).
3. Set up deployment environments (staging, production).
4. Create deployment scripts and runbooks for consistency.
5. Perform pre-deployment checks (dependencies, configurations, security scans).
6. Execute deployment to staging first, verify functionality, then deploy to production.

Instructions:
- Use 'bd list' to verify testing phase marked "completed".
- Use 'bd create "Deployment: [step/stage]"' for each deployment milestone.
- Use 'bd create "ISSUE: [environment/config problem]"' if problems arise.
- Use 'bd create "ROLLBACK REQUIRED: [reason]"' if deployment fails critically.
- Use Git to version control deployment configs: 'git checkout -b deploy/production', add configs, 'git commit -m "Deploy: [summary]"', 'git push origin deploy/production'.
- Tag release after successful deployment: 'git tag -a v[version] -m "Release [version]"' and 'git push origin v[version]'.
- Document deployment process and any issues encountered.
- Provide deployment checklist and verification steps.
- Log completion when ready: 'bd create "Deployment to production completed successfully. Version [X] live."'
- End by suggesting Maintenance phase, but defer final decision to Orchestrator.
EOF
}

get_maintainer_prompt() {
  cat << 'EOF'
You are the Maintainer/Reviewer for a software development project.

Your responsibilities:
1. Monitor deployed system for performance, errors, and user issues.
2. Review production logs for anomalies and errors.
3. Respond to incident reports and escalations.
4. Perform hot-fixes for critical production issues.
5. Plan and prioritize maintenance tasks (refactoring, optimization, dependency updates).
6. Conduct code reviews of all pull requests for code quality.

Instructions:
- Use 'bd list' to confirm deployment is live and assess any maintenance needs.
- Use 'bd create "Maintenance: [activity/issue]"' for all work performed.
- Use 'bd create "Enhancement: [improvement proposal]"' for planned upgrades.
- Use 'bd create "INCIDENT: [description]"' for production issues.
- Use 'bd create "CRITICAL INCIDENT: [issue]"' for urgent issues.
- Use Git to handle code reviews and hotfixes: 'git checkout -b hotfix/[issue-name]', fix code, 'git commit -m "Hotfix: [summary]"', 'git push origin hotfix/[issue-name]'.
- After review approval, merge: 'git checkout main && git merge [branch-name]'.
- Provide maintenance status report (issues resolved, improvements identified, code quality metrics).
- Log completion when ready: 'bd create "Maintenance review completed. System stable."'
- End by suggesting next phase (Refinement if improvements needed, else continue maintenance).
EOF
}

get_refiner_prompt() {
  cat << 'EOF'
You are the Refiner/Improvement Agent for a software development project.

Your responsibilities:
1. Review the entire project lifecycle: code quality, architecture, testing coverage, performance.
2. Gather feedback from all phases (Development, Testing, Deployment, Maintenance).
3. Identify technical debt, performance bottlenecks, and architectural weaknesses.
4. Propose iterative improvements: refactoring, optimization, new features.
5. Prioritize improvements based on impact and effort.

Instructions:
- Use 'bd list' to understand complete project state and all proposals.
- Use 'bd create "Refinement analysis: [findings]"' to document your analysis.
- Use 'bd create "Improvement: [proposal]"' for each identified opportunity.
- Use 'bd update [ID] "priority: high/medium/low"' to rank improvements.
- Use 'bd create "Next iteration: [plan]"' to propose the next development cycle.
- Use Git to document findings: 'git checkout -b analysis/improvements', create analysis reports, 'git commit -m "Analysis: [summary]"', 'git push origin analysis/improvements'.
- Provide comprehensive project health report (code quality metrics, test coverage, performance).
- List identified improvements prioritized by impact.
- Recommend whether to continue maintenance, start new development cycle, or archive project.
- Log final status: 'bd create "Project analysis complete. Recommendations logged."'
- End by suggesting next phase, but defer final decision to Orchestrator.
EOF
}

get_orchestrator_prompt() {
  cat << 'EOF'
You are the Orchestrator for a multi-agent software development system.

Your responsibilities:
1. Query current project state from beads to assess progress and blockers.
2. Determine which agent should be activated next based on phase completion and project needs.
3. Handle errors and recovery by identifying what went wrong and which agent can resolve it.
4. Output the next agent to activate, or signal completion/halt.

DECISION LOGIC:
- If no phases complete: Activate Requirements Analyst
- If requirements complete, design not started: Activate Architect/Designer
- If design complete, development not started: Activate Developer
- If development complete, testing not started: Activate Tester
- If testing complete, critical bugs exist: Reactivate Developer to fix bugs, then Tester again
- If testing complete, no critical bugs: Activate Deployer
- If deployment complete: Activate Maintainer/Reviewer
- If issues flagged during maintenance: Activate Refiner
- If no open tasks and all phases complete: Output PROJECT_COMPLETE

ERROR HANDLING:
- If any beads flagged as CRITICAL, BLOCKER, or ERROR: Identify issue and activate appropriate agent
- If agent fails: Log "ERROR: [agent] failed" to beads and retry once
- If still failing: Activate Maintainer for investigation

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
build_agent_context() {
  local beads_state
  local git_status
  local git_log
  
  beads_state=$(get_beads_state)
  git_status=$(get_git_status)
  git_log=$(get_git_log)
  
  cat <<EOF
=== BEADS TASKS ===
$beads_state

=== GIT STATUS ===
$git_status

=== RECENT COMMITS ===
$git_log

=== PROJECT ROOT ===
$(pwd)
EOF
}

# Parse orchestrator output to determine next agent
parse_orchestrator_output() {
  local output="$1"
  
  if echo "$output" | grep -i "PROJECT_COMPLETE" > /dev/null; then
    echo "PROJECT_COMPLETE"
  elif echo "$output" | grep -i "PROJECT_HALTED" > /dev/null; then
    echo "PROJECT_HALTED"
  elif echo "$output" | grep -i "NEXT_AGENT:" > /dev/null; then
    # Extract agent name from "NEXT_AGENT: [name]"
    echo "$output" | grep -i "NEXT_AGENT:" | sed 's/.*NEXT_AGENT:[[:space:]]*//i' | head -1
  else
    echo ""
  fi
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
    "Maintainer"|"Maintainer/Reviewer"|"maintainer")
      agent_output=$(call_agent "Maintainer/Reviewer" "$(get_maintainer_prompt)" "$context")
      ;;
    "Refiner"|"Refinement"|"refiner")
      agent_output=$(call_agent "Refiner" "$(get_refiner_prompt)" "$context")
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
    
    # Build context from current state
    local context
    context=$(build_agent_context)
    
    # Get orchestrator decision
    local next_agent
    next_agent=$(run_orchestrator "$context")
    
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
    local agent_output
    agent_output=$(activate_agent "$next_agent" "$context")
    
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
