import shutil
import subprocess
import os
import time
import datetime
import re
from typing import List, Optional, Dict, Tuple
from orchestrator.config import config
from orchestrator.agents import registry, Agent
from orchestrator.beads import beads
from orchestrator.utils import print_info, print_error, print_success, print_header, print_warning

# Agent role ordering for tie-breaking (SDLC order)
AGENT_ROLE_ORDER = [
    "Requirements Analyst",
    "Architect/Designer",
    "Developer",
    "Tester",
    "Deployer",
    "Maintainer/Reviewer",
    "Refiner",
    "Git Maintainer",
    "Documentation Specialist"
]

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
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
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
        """Verifies if beads is initialized."""
        try:
            # Check if bd list works
            result = subprocess.run(["bd", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print_error("Beads is not initialized.")
                print_info("Please run 'bd init' manually to set up beads in this repository.")
                return False
            
            return True
        except Exception as e:
            print_error(f"Failed to verify beads initialization: {e}")
            return False

    def get_beads_state(self) -> str:
        """Returns the full project state from beads."""
        return beads.get_state()

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
        """
        Retrieves messages addressed to this agent with bead IDs.
        Format: [beads-XXX] MESSAGE: [FromAgent]→[TargetAgent]: content
        """
        try:
            result = subprocess.run(
                ["bd", "list", "--status=open", "--json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            messages = []
            
            # Parse JSONL output (one JSON object per line)
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                try:
                    import json
                    bead = json.loads(line)
                    title = bead.get("title", "")
                    bead_id = bead.get("id", "")
                    
                    if "MESSAGE:" in title:
                        # Check if message is for this agent or [All]
                        if f"→{agent_name}" in title or "→[All]" in title:
                            # Format with bead ID for agent reference
                            messages.append(f"[{bead_id}] {title}")
                except json.JSONDecodeError:
                    continue
            
            return "\n".join(messages) if messages else "No new messages"
        except Exception as e:
            print_error(f"Failed to get messages for {agent_name}: {e}")
            return "No new messages"

    def mark_message_read(self, bead_id: str) -> bool:
        """Marks a message as read by closing the bead."""
        try:
            beads.close_issue(bead_id, reason="Marked as read")
            print_info(f"Message marked as read: ID {bead_id}")
            return True
        except Exception as e:
            print_warning(f"Failed to mark message as read: {e}")
            return False

    def create_bootstrap_messages(self) -> None:
        """Creates initial bootstrap messages to all agents at system startup."""
        bootstrap_content = "Bootstrap message to start the message-driven SDLC system. Begin your role and send messages to other agents as needed."
        for agent_name in AGENT_ROLE_ORDER:
            try:
                beads.send_message("System", agent_name, bootstrap_content)
                print_info(f"Bootstrap message sent to: {agent_name}")
            except Exception as e:
                print_warning(f"Failed to create bootstrap message for {agent_name}: {e}")

    def count_pending_messages(self) -> int:
        """Counts the number of pending (open) MESSAGE: beads."""
        try:
            result = subprocess.run(
                ["bd", "list", "--status=open"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            count = 0
            for line in result.stdout.splitlines():
                if "MESSAGE:" in line:
                    count += 1
            return count
        except Exception as e:
            print_error(f"Failed to count pending messages: {e}")
            return 0

    def count_messages_for_agent(self, agent_name: str) -> int:
        """Counts pending messages for a specific agent."""
        try:
            result = subprocess.run(
                ["bd", "list", "--status=open", "--json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            count = 0
            
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                try:
                    import json
                    bead = json.loads(line)
                    title = bead.get("title", "")
                    
                    if "MESSAGE:" in title:
                        if f"→{agent_name}" in title or "→[All]" in title:
                            count += 1
                except json.JSONDecodeError:
                    continue
            
            return count
        except Exception as e:
            print_error(f"Failed to count messages for {agent_name}: {e}")
            return 0

    def get_pending_messages_by_agent(self) -> Dict[str, List[Dict]]:
        """
        Gets all pending messages grouped by target agent.
        Returns dict: {agent_name: [{'id': 'beads-xxx', 'title': '...'}, ...]}
        """
        try:
            result = subprocess.run(
                ["bd", "list", "--status=open", "--json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            messages_by_agent: Dict[str, List[Dict]] = {}
            
            # Parse JSONL output (one JSON object per line)
            for line in result.stdout.strip().splitlines():
                if not line.strip():
                    continue
                try:
                    import json
                    bead = json.loads(line)
                    title = bead.get("title", "")
                    bead_id = bead.get("id", "")
                    
                    if "MESSAGE:" in title:
                        # Extract target agent from title
                        # Format: "MESSAGE: [timestamp] FromAgent→ToAgent: content"
                        match = re.search(r'→\[?([^\]:]+)\]?:', title)
                        if match:
                            target_agent = match.group(1).strip()
                            if target_agent not in messages_by_agent:
                                messages_by_agent[target_agent] = []
                            messages_by_agent[target_agent].append({'id': bead_id, 'title': title})
                except json.JSONDecodeError:
                    continue
            
            return messages_by_agent
        except Exception as e:
            print_error(f"Failed to get pending messages: {e}")
            return {}

    def select_agent_by_messages(self) -> Optional[str]:
        """
        Selects the agent with the most pending messages.
        Uses AGENT_ROLE_ORDER for tie-breaking.
        """
        messages_by_agent = self.get_pending_messages_by_agent()
        
        if not messages_by_agent:
            return None
        
        # Find agent with most messages
        max_count = 0
        selected_agent = None
        
        for agent_name in AGENT_ROLE_ORDER:
            if agent_name in messages_by_agent:
                count = len(messages_by_agent[agent_name])
                if count > max_count:
                    max_count = count
                    selected_agent = agent_name
        
        # If no agent from the order has messages, pick the first one with messages
        if not selected_agent:
            for agent_name, messages in messages_by_agent.items():
                if messages:
                    selected_agent = agent_name
                    break
        
        return selected_agent

    def register_message(self, from_agent: str, to_agent: str, content: str) -> bool:
        """Registers a new message in beads."""
        return self.send_message(from_agent, to_agent, content)

    def commit_changes(self, agent_name: str, message: str) -> bool:
        """Commits changes to git if any."""
        try:
            subprocess.run(["git", "add", "-A"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Check for changes
            diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
            if diff.returncode != 0:
                subprocess.run(["git", "commit", "-m", f"[{agent_name}] {message}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
            result = subprocess.run(["git", "status", "--short"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return result.stdout.strip()
        except Exception:
            return "Error getting git status"

    def get_git_log(self, n: int = 5) -> str:
        """Returns the recent git log entries."""
        try:
            result = subprocess.run(["git", "log", "-n", str(n), "--oneline"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return result.stdout.strip()
        except Exception:
            return "Error getting git log"

    def get_beads_prime(self) -> str:
        """Returns the output of bd prime."""
        try:
            result = subprocess.run(["bd", "prime"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=timeout_seconds
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
