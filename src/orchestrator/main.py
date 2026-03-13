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
from typing import Optional

from orchestrator.config import config
from orchestrator.service import orchestration_service
from orchestrator.utils import (
    print_info,
    print_error,
    print_success,
    print_header,
    log_agent_activation,
    log_messages_received,
)
from orchestrator.agents import registry

app = typer.Typer()


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

    # Bootstrap: create initial message to each agent
    print_info("Creating bootstrap messages...")
    orchestration_service.create_bootstrap_messages()
    print_success("Bootstrap messages created")

    print_success("All prerequisites verified")

    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print_header(f"ITERATION {iteration}")

        # 1. Check for pending messages
        pending_count = orchestration_service.count_pending_messages()
        if pending_count == 0:
            print_header("NO PENDING MESSAGES - SYSTEM COMPLETE")
            print_success("All messages processed. System completed naturally.")
            break

        # 2. Select agent with most pending messages (tie-break by role order)
        selected_agent = orchestration_service.select_agent_by_messages()
        if not selected_agent:
            print_error("No agent could be selected.")
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

        # Tagging
        subprocess.run(
            ["git", "tag", "-a", f"iteration-{iteration}", "-m", f"Iteration {iteration} completed"],
            capture_output=True
        )

        # Brief pause
        time.sleep(1)

    print_header("ORCHESTRATION FINAL STATUS")
    print_success(f"System completed after {iteration} iterations.")

    # Final status report
    final_state = orchestration_service.get_beads_state()
    print_info(f"Final project state:\n{final_state}")


if __name__ == "__main__":
    app()
