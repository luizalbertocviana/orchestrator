import typer
import time
import re
from typing import Optional, List, Tuple
from orchestrator.config import config
from orchestrator.service import orchestration_service
from orchestrator.utils import print_info, print_error, print_success, print_header, log_agent_activation, log_messages_received, log_message_sent, log_messages_acknowledged
from orchestrator.agents import registry

app = typer.Typer()

def strip_markdown(text: str) -> str:
    """Removes basic markdown formatting for cleaner parsing."""
    # Remove bold (**)
    text = text.replace("**", "")
    # Remove italics (*)
    text = text.replace("*", "")
    # Remove underline (__) only at word boundaries
    text = re.sub(r'\b__\b', '', text)
    # Remove single underline (_) only at word boundaries
    text = re.sub(r'\b_\b', '', text)
    # Remove inline code (`)
    text = text.replace("`", "")
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_messages(output: str) -> List[Tuple[str, str, str]]:
    """
    Extracts MESSAGE: patterns from agent output.
    Returns list of (from_agent, to_agent, content) tuples.
    Format: MESSAGE: [AgentName]→[TargetAgent]: <content>
    """
    messages = []
    # Match MESSAGE: [Agent]→[Target]: content (one per line)
    pattern = r'MESSAGE:\s*\[([^\]]+)\]\s*→\s*\[([^\]]+)\]\s*:\s*(.+?)$'
    for match in re.finditer(pattern, output, re.IGNORECASE | re.MULTILINE):
        from_agent, to_agent, content = match.groups()
        messages.append((from_agent.strip(), to_agent.strip(), content.strip()))
    return messages

def parse_mark_read(output: str) -> List[str]:
    """
    Extracts MARK_READ: patterns from agent output.
    Returns list of bead IDs (e.g., ['beads-123', 'beads-124']).
    Format: MARK_READ: beads-XXX or MARK_READ: beads-XXX, beads-YYY
    """
    bead_ids = []
    pattern = r'MARK_READ:\s*([^\n]+)'
    matches = re.findall(pattern, output, re.IGNORECASE)
    for match in matches:
        # Split by comma and extract bead IDs
        ids = re.findall(r'beads-[\w]+', match)
        bead_ids.extend(ids)
    return bead_ids

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

        # Log agent activation
        log_agent_activation(selected_agent, pending_count)

        # 3. Activate the agent
        print_header(f"ACTIVATING AGENT: {selected_agent}")
        
        # Log messages received
        received_count = orchestration_service.count_messages_for_agent(selected_agent)
        log_messages_received(selected_agent, received_count)
        
        agent_output = orchestration_service.activate_agent(selected_agent, iteration)

        if not agent_output:
            print_error(f"Agent {selected_agent} failed.")
            continue

        # 4. Parse and register new messages
        new_messages = parse_messages(agent_output)
        for from_agent, to_agent, content in new_messages:
            orchestration_service.register_message(from_agent, to_agent, content)
            log_message_sent(from_agent, to_agent, content)

        # 5. Mark messages as read
        mark_read_ids = parse_mark_read(agent_output)
        for bead_id in mark_read_ids:
            orchestration_service.mark_message_read(bead_id)
        log_messages_acknowledged(selected_agent, mark_read_ids)

        # 6. Commit changes and Tag
        commit_msg = f"Iteration {iteration} - {selected_agent} task completed"
        orchestration_service.commit_changes(selected_agent, commit_msg)

        # Tagging
        import subprocess
        subprocess.run(["git", "tag", "-a", f"iteration-{iteration}", "-m", f"Iteration {iteration} completed"], capture_output=True)

        # Brief pause
        time.sleep(1)

    print_header("ORCHESTRATION FINAL STATUS")
    print_success(f"System completed after {iteration} iterations.")
    
    # Final status report
    final_beads = orchestration_service.get_beads_state()
    print_info(f"Final project state:\n{final_beads}")

if __name__ == "__main__":
    app()
