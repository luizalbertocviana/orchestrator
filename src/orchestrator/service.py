"""Orchestration service for the message-driven multi-agent SDLC system.

This service provides:
- Bootstrap message creation at startup
- Agent selection based on pending message count
- Agent activation with context
- Git commit after each iteration

Agents communicate directly via the broker script (broker send/read/ack).
"""

import shutil
import subprocess
import os
import time
from typing import List, Optional, Dict
from pathlib import Path

from orchestrator.config import config
from orchestrator.agents import registry, Agent
from orchestrator.broker_wrapper import BrokerWrapper, get_broker
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
    """Service for orchestrating the multi-agent SDLC system."""
    
    def __init__(self, broker: Optional[BrokerWrapper] = None):
        """Initialize the orchestration service.
        
        Args:
            broker: Optional BrokerWrapper instance. Uses global instance if not provided.
        """
        self.broker = broker or get_broker()
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
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
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
        """Verifies that the broker script is available.

        Note: Method name kept for backward compatibility.
        """
        if not self.broker.verify():
            print_error("Broker script not found or not executable.")
            print_info(f"Expected at: {self.broker.broker_path}")
            return False
        return True

    def get_beads_state(self) -> str:
        """Returns a summary of pending messages from broker."""
        counts = self.broker.count_by_agent()
        if not counts:
            return "No pending messages"
        
        lines = ["Pending messages by agent:"]
        for agent, count in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {agent}: {count}")
        return "\n".join(lines)
    
    def create_bootstrap_messages(self) -> None:
        """Creates initial bootstrap messages to all agents at system startup."""
        bootstrap_content = "Bootstrap message to start the message-driven SDLC system. Begin your role and send messages to other agents as needed."
        for agent_name in AGENT_ROLE_ORDER:
            try:
                self.broker.send_message("System", agent_name, bootstrap_content)
                print_info(f"Bootstrap message sent to: {agent_name}")
            except Exception as e:
                print_warning(f"Failed to create bootstrap message for {agent_name}: {e}")
    
    def count_pending_messages(self) -> int:
        """Counts the total number of pending (unacknowledged) messages."""
        all_pending = self.broker.get_all_pending()
        return len(all_pending)
    
    def count_messages_for_agent(self, agent_name: str) -> int:
        """Counts pending messages for a specific agent."""
        return self.broker.count_pending(agent_name)
    
    def get_pending_messages_by_agent(self) -> Dict[str, List[Dict]]:
        """
        Gets all pending messages grouped by target agent.
        
        Returns:
            Dict mapping agent names to lists of pending messages.
            Each message is a dict with 'id', 'to', 'from', 'content', etc.
        """
        all_pending = self.broker.get_all_pending()
        
        messages_by_agent: Dict[str, List[Dict]] = {}
        for msg in all_pending:
            to_agent = msg.get("to", "")
            if to_agent:
                if to_agent not in messages_by_agent:
                    messages_by_agent[to_agent] = []
                messages_by_agent[to_agent].append(msg)
        
        return messages_by_agent
    
    def select_agent_by_messages(self) -> Optional[str]:
        """
        Selects the first agent in AGENT_ROLE_ORDER that has pending messages.
        If no agent from the order has messages, falls back to any agent with messages.
        """
        messages_by_agent = self.get_pending_messages_by_agent()

        if not messages_by_agent:
            return None

        # Find the first agent in order that has any messages
        for agent_name in AGENT_ROLE_ORDER:
            if agent_name in messages_by_agent and messages_by_agent[agent_name]:
                return agent_name

        # If no agent from the order has messages, pick the first one with messages
        for agent_name, messages in messages_by_agent.items():
            if messages:
                return agent_name

        return None
    
    def commit_changes(self, agent_name: str, message: str) -> bool:
        """Commits changes to git if any."""
        try:
            subprocess.run(["git", "add", "-A"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Check for changes
            diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
            if diff.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m", f"[{agent_name}] {message}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
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
            result = subprocess.run(
                ["git", "status", "--short"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout.strip()
        except Exception:
            return "Error getting git status"
    
    def get_git_log(self, n: int = 5) -> str:
        """Returns the recent git log entries."""
        try:
            result = subprocess.run(
                ["git", "log", "-n", str(n), "--oneline"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout.strip()
        except Exception:
            return "Error getting git log"
    
    def build_context(self, agent_name: str, iteration: int = 0) -> str:
        """Builds context for the agent.

        Note: Agents read their own messages directly from broker.
        This context provides git status and project info only.

        Args:
            agent_name: Name of the agent being activated
            iteration: Current iteration number (0 if not provided)
        """
        git_status = self.get_git_status()
        git_log = self.get_git_log()
        cwd = os.getcwd()
        broker_path = str(self.broker.broker_path)

        return f"""=== GIT STATUS ===
{git_status if git_status else "Clean working tree"}

=== RECENT COMMITS ===
{git_log if git_log else "No commits yet"}

=== PROJECT ROOT ===
{cwd}

=== BROKER SCRIPT PATH ===
{broker_path}

=== BROKER STATUS ===
{self.broker.generate_context()}

=== ITERATION ===
{iteration}
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
        """Activates a specific logical agent.

        The agent receives context and will call broker directly to:
        - Read its messages: broker read <agent_name>
        - Send messages: broker send --from <X> --to <Y> --content <msg>
        - Acknowledge messages: broker ack <msg_id>
        """
        agent = registry.get_agent(agent_name)
        if not agent:
            print_error(f"Unknown logical agent: {agent_name}")
            return None

        print_info(f"Activating {agent_name} (Iteration {iteration})...")

        context = self.build_context(agent_name, iteration)
        prompt = agent.get_prompt(context)

        output = self.call_agent_with_retry(agent_name, prompt, context, iteration)
        return output


# Global service instance
orchestration_service = OrchestrationService()
