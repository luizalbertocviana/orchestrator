"""Main entry point for the message-driven multi-agent SDLC system.

Agents communicate directly via the broker script. The orchestrator:
1. Creates bootstrap messages at startup
2. Selects agents based on SDLC order
3. Activates agents (which call broker directly)
4. Commits git changes after each iteration
"""

import typer
import time
import subprocess
import re
from typing import Optional

from orchestrator.config import config
from orchestrator.service import orchestration_service
from orchestrator.utils import (
    print_info,
    print_error,
    print_success,
    print_warning,
    print_header,
    log_agent_activation,
    log_messages_received,
)
from orchestrator.agents import registry

app = typer.Typer()


def get_last_iteration_from_tags() -> int:
    """Get the last iteration number from existing git tags.
    
    Parses tags matching 'iteration-N' pattern and returns the maximum N.
    Returns 0 if no iteration tags exist.
    
    Returns:
        int: The last iteration number from tags, or 0 if none exist.
    """
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "iteration-*"],
            capture_output=True,
            text=True,
            check=True
        )
        tags = result.stdout.strip().splitlines()
        if not tags:
            return 0
        
        # Extract iteration numbers from tag names
        iteration_numbers = []
        for tag in tags:
            match = re.match(r"iteration-(\d+)$", tag)
            if match:
                iteration_numbers.append(int(match.group(1)))
        
        return max(iteration_numbers) if iteration_numbers else 0
    except subprocess.CalledProcessError:
        # Git command failed (e.g., not a git repo)
        return 0
    except Exception:
        # Any other error, return 0 to start fresh
        return 0


@app.command()
def version():
    """Shows the version of the orchestrator."""
    print("SDLC Orchestrator v0.1.0")


@app.command()
def run(
    max_iterations: int = typer.Option(config.max_iterations, help="Maximum number of iterations.")
):
    """Starts the message-driven multi-agent SDLC system."""
    print_header("MESSAGE-DRIVEN MULTI-AGENT SDLC SYSTEM")

    # Prerequisites
    print_info("Verifying prerequisites...")
    if not orchestration_service.verify_tools():
        return
    if not orchestration_service.verify_git_repo():
        return
    orchestration_service.verify_specs_file()
    if not orchestration_service.initialize_beads():
        return

    # Bootstrap: create initial messages only if no pending messages exist
    print_info("Checking for pending messages...")
    if orchestration_service.count_pending_messages() == 0:
        print_info("No pending messages found. Creating bootstrap messages...")
        orchestration_service.create_bootstrap_messages()
        print_success("Bootstrap messages created")
    else:
        print_info("Found existing pending messages. Skipping bootstrap.")

    print_success("All prerequisites verified")

    # Get last iteration from existing tags to continue numbering across runs
    last_iteration_from_tags = get_last_iteration_from_tags()
    if last_iteration_from_tags > 0:
        print_info(f"Found existing iteration tags. Resuming from iteration {last_iteration_from_tags}.")

    # Track iterations for this run separately to allow fresh max_iterations each run
    iterations_this_run = 0
    exit_reason = "max_iterations_reached"  # Default if loop completes without break

    while iterations_this_run < max_iterations:
        iterations_this_run += 1

        # Calculate continuous iteration number for tagging and display
        iteration = last_iteration_from_tags + iterations_this_run
        print_header(f"ITERATION {iteration}")

        # 1. Check for pending messages
        pending_count = orchestration_service.count_pending_messages()
        if pending_count == 0:
            print_header("NO PENDING MESSAGES - SYSTEM COMPLETE")
            print_success("All messages processed. System completed naturally.")
            exit_reason = "completed_naturally"
            break

        selected_agent = orchestration_service.select_agent_by_messages()
        if not selected_agent:
            print_error("No agent could be selected.")
            exit_reason = "no_agent_selected"
            break

        # Log agent activation with count for this specific agent
        selected_agent_count = orchestration_service.count_messages_for_agent(selected_agent)
        log_agent_activation(selected_agent, selected_agent_count)

        # 3. Activate the agent
        print_header(f"ACTIVATING AGENT: {selected_agent}")

        # Log messages received
        received_count = orchestration_service.count_messages_for_agent(selected_agent)
        log_messages_received(selected_agent, received_count)

        # Agent calls broker directly to read/send/ack messages
        agent_output = orchestration_service.activate_agent(selected_agent, iteration)

        if not agent_output:
            print_error(f"Agent {selected_agent} failed.")
            continue

        # 4. Commit changes and tag
        commit_msg = f"Iteration {iteration} - {selected_agent} task completed"
        orchestration_service.commit_changes(selected_agent, commit_msg)

        # Tagging with continuous iteration number
        subprocess.run(
            ["git", "tag", "-a", f"iteration-{iteration}", "-m", f"Iteration {iteration} completed"],
            capture_output=True
        )

        # Brief pause
        time.sleep(1)

    # Final status report based on exit reason
    print_header("ORCHESTRATION FINAL STATUS")
    
    remaining_messages = orchestration_service.count_pending_messages()
    
    if exit_reason == "completed_naturally":
        print_success(f"System completed naturally after {iterations_this_run} iterations this run ({last_iteration_from_tags + iterations_this_run} total).")
        print_success("No pending messages remaining.")
    elif exit_reason == "no_agent_selected":
        print_error(f"Orchestration stopped: no agent could be selected after {iterations_this_run} iterations.")
        if remaining_messages > 0:
            print_warning(f"Warning: {remaining_messages} pending messages remain unprocessed.")
    elif exit_reason == "max_iterations_reached":
        print_warning(f"Maximum iterations ({max_iterations}) reached after {iterations_this_run} iterations this run ({last_iteration_from_tags + iterations_this_run} total).")
        if remaining_messages > 0:
            print_warning(f"Warning: {remaining_messages} pending messages remain unprocessed.")
            print_info("To continue, run the orchestrator again or increase max_iterations.")
        else:
            print_success("No pending messages remaining.")

    # Final status report
    final_state = orchestration_service.get_beads_state()
    print_info(f"Final project state:\n{final_state}")


if __name__ == "__main__":
    app()
