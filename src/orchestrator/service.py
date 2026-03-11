import shutil
import subprocess
import os
import time
import datetime
from typing import List, Optional
from orchestrator.config import config
from orchestrator.agents import registry, Agent
from orchestrator.beads import beads
from orchestrator.utils import print_info, print_error, print_success, print_header, print_warning

class OrchestrationService:
    def __init__(self):
        self.available_cli_agents = self._get_available_cli_agents()

    def _get_available_cli_agents(self) -> List[str]:
        """Checks which configured CLI agents are available in the PATH."""
        print_info("Checking available cli agents...")
        
        available = []
        missing = []
        for agent in config.agents:
            if shutil.which(agent):
                available.append(agent)
                print_info(f"Found: {agent}")
            else:
                missing.append(agent)
        
        if missing:
            print_warning(f"Missing cli agents: {' '.join(missing)} (skipping from rotation)")
        
        if not available:
            print_error(f"No cli agents available. Please install at least one of: {' '.join(config.agents)}")
            return []
        
        print_info(f"Using sequential rotation across {len(available)} available cli agent(s): {' '.join(available)}")
        return available

    def get_next_cli_agent(self, iteration: int) -> Optional[str]:
        """Selects the next CLI agent using sequential rotation."""
        if not self.available_cli_agents:
            return None
        
        index = (iteration - 1) % len(self.available_cli_agents)
        return self.available_cli_agents[index]

    def verify_tools(self) -> bool:
        """Verifies that required tools are available."""
        missing = []
        for tool in config.required_tools:
            if not shutil.which(tool):
                missing.append(tool)
        
        if missing:
            print_error(f"Missing required tools: {', '.join(missing)}")
            return False
        return True

    def verify_git_repo(self) -> bool:
        """Verifies that we are in a git repository."""
        try:
            subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], 
                           capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            print_error("Not a git repository.")
            return False

    def create_specs_template(self) -> None:
        """Creates a default specs.md template."""
        content = """# Project Specifications

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
"""
        with open("specs.md", "w") as f:
            f.write(content)
        print_success("Created specs.md template")

    def verify_specs_file(self) -> bool:
        """Verifies that specs.md exists."""
        if not os.path.exists("specs.md"):
            print_warning("specs.md not found. Creating empty specs.md...")
            self.create_specs_template()
        return True

    def initialize_beads(self) -> bool:
        """Initializes beads if not already initialized."""
        try:
            # Check if bd list works
            result = subprocess.run(["bd", "list"], capture_output=True, text=True)
            if result.returncode != 0 or not result.stdout.strip():
                print_info("Initializing beads...")
                # We assume bd is installed and usable
                subprocess.run(["bd", "init"], capture_output=True)
                beads.create_issue("Phase: Requirements Analysis - Review and refine specs.md")
                print_success("Initial bead task created")
            return True
        except Exception as e:
            print_error(f"Failed to initialize beads: {e}")
            return False

    def get_beads_state(self) -> str:
        """Returns the full project state from beads."""
        return beads.get_state()

    def check_for_blockers(self) -> bool:
        """Checks if there are any critical errors or blockers in beads."""
        state = self.get_beads_state()
        import re
        if re.search(r"(BLOCKER|CRITICAL|ERROR)", state, re.IGNORECASE):
            return True
        return False

    def send_message(self, from_agent: str, to_agent: str, content: str) -> bool:
        """Sends an inter-agent message via beads."""
        try:
            beads.send_message(from_agent, to_agent, content)
            print_info(f"Message sent: {from_agent}→{to_agent}")
            return True
        except Exception as e:
            print_warning(f"Failed to send message: {e}")
            return False

    def get_messages_for_agent(self, agent_name: str) -> str:
        """Retrieves messages addressed to this agent."""
        all_beads = self.get_beads_state()
        messages = []
        for line in all_beads.splitlines():
            if "MESSAGE:" in line and f"→{agent_name}" in line:
                messages.append(line)
            elif "MESSAGE:" in line and "→[All]" in line:
                messages.append(line)
        
        return "\n".join(messages) if messages else "No new messages"

    def get_messages_from_agent(self, agent_name: str) -> str:
        """Retrieves messages sent by this agent."""
        all_beads = self.get_beads_state()
        messages = []
        for line in all_beads.splitlines():
            if "MESSAGE:" in line and f"{agent_name}→" in line:
                messages.append(line)
        
        return "\n".join(messages) if messages else "No sent messages"

    def mark_message_read(self, bead_id: str) -> bool:
        """Marks a message as read by closing the bead."""
        try:
            beads.close_issue(bead_id, reason="Marked as read")
            print_info(f"Message marked as read: ID {bead_id}")
            return True
        except Exception as e:
            print_warning(f"Failed to mark message as read: {e}")
            return False

    def commit_changes(self, agent_name: str, message: str) -> bool:
        """Commits changes to git if any."""
        try:
            subprocess.run(["git", "add", "-A"], capture_output=True)
            # Check for changes
            diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
            if diff.returncode != 0:
                subprocess.run(["git", "commit", "-m", f"[{agent_name}] {message}"], capture_output=True)
                print_success(f"Changes committed: {message}")
                return True
            else:
                print_info("No changes to commit")
                return True
        except Exception as e:
            print_error(f"Failed to commit changes: {e}")
            return False

    def get_git_status(self) -> str:
        """Returns the current git status."""
        try:
            result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return "Error getting git status"

    def get_git_log(self, n: int = 5) -> str:
        """Returns the recent git log entries."""
        try:
            result = subprocess.run(["git", "log", "-n", str(n), "--oneline"], capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return "Error getting git log"

    def get_beads_prime(self) -> str:
        """Returns the output of bd prime."""
        try:
            result = subprocess.run(["bd", "prime"], capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return "Error running bd prime"

    def build_context(self, agent_name: str) -> str:
        """Builds a comprehensive context for the agent."""
        beads_state = self.get_beads_state()
        git_status = self.get_git_status()
        git_log = self.get_git_log()
        beads_prime = self.get_beads_prime()
        messages = self.get_messages_for_agent(agent_name)
        cwd = os.getcwd()

        return f"""=== BEADS PRIME ===
{beads_prime}

=== BEADS TASKS ===
{beads_state}

=== INTER-AGENT MESSAGES (addressed to you) ===
{messages}

=== GIT STATUS ===
{git_status}

=== RECENT COMMITS ===
{git_log}

=== PROJECT ROOT ===
{cwd}
"""

    def call_agent_with_retry(self, logical_agent_name: str, prompt: str, context: str, iteration: int) -> Optional[str]:
        """Calls a CLI agent with retry and rotation logic."""
        full_prompt = f"{prompt}\n\nCURRENT PROJECT CONTEXT:\n{context}\n\nPlease proceed with your role and responsibilities."
        
        current_cli_agent = self.get_next_cli_agent(iteration)
        if not current_cli_agent:
            print_error("No CLI agents available.")
            return None

        print_info(f"Selected cli agent: {current_cli_agent} (iteration: {iteration})")

        attempt = 1
        agents_tried = []
        
        timeout_val = config.agent_timeout_limit
        if isinstance(timeout_val, str) and timeout_val.endswith('s'):
            timeout_seconds = int(timeout_val[:-1])
        else:
            timeout_seconds = int(timeout_val)

        while attempt <= config.max_retries:
            agents_tried.append(current_cli_agent)
            flags = config.agent_flags.get(current_cli_agent, "-y")
            
            print_info(f"Calling cli agent: {current_cli_agent} [{logical_agent_name}] (attempt {attempt}/{config.max_retries})")
            
            try:
                # Use stderr=subprocess.STDOUT to match bash's 2>&1 behavior
                process = subprocess.run(
                    [current_cli_agent] + flags.split() + [full_prompt],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    stderr=subprocess.STDOUT
                )
                if process.returncode == 0 and process.stdout.strip():
                    return process.stdout.strip()
                
                print_warning(f"cli agent {current_cli_agent} failed with exit code {process.returncode}")
                if process.stdout.strip():
                    print_info(f"Agent Output: {process.stdout.strip()}")
            except subprocess.TimeoutExpired:
                print_warning(f"cli agent {current_cli_agent} timed out after {timeout_seconds}s")
            except Exception as e:
                print_warning(f"Error calling {current_cli_agent}: {e}")

            if attempt < config.max_retries:
                # Rotate to next agent for retry
                current_cli_agent = self.get_next_cli_agent(iteration + attempt)
                print_info(f"Will retry with: {current_cli_agent}")
                time.sleep(2)
            
            attempt += 1

        print_error(f"All agent attempts failed. Tried: {', '.join(agents_tried)}")
        return None

    def activate_agent(self, agent_name: str, iteration: int) -> Optional[str]:
        """Activates a specific logical agent."""
        agent = registry.get_agent(agent_name)
        if not agent:
            print_error(f"Unknown logical agent: {agent_name}")
            return None

        print_info(f"Activating {agent_name} (Iteration {iteration})...")
        
        context = self.build_context(agent_name)
        prompt = agent.get_prompt(context)
        
        output = self.call_agent_with_retry(agent_name, prompt, context, iteration)
        return output

# Global service instance
orchestration_service = OrchestrationService()
