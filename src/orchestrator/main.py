import typer
import time
import re
from typing import Optional
from orchestrator.config import config
from orchestrator.service import orchestration_service
from orchestrator.utils import print_info, print_error, print_success, print_header
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

def parse_orchestrator_decision(output: str) -> str:
    """Parses the orchestrator's output to determine the next action."""
    normalized = strip_markdown(output)
    
    if re.search(r'PROJECT_COMPLETE', normalized, re.IGNORECASE):
        return "PROJECT_COMPLETE"
    
    halt_match = re.search(r'PROJECT_HALTED[:\s]*(.*)', normalized, re.IGNORECASE)
    if halt_match:
        reason = halt_match.group(1).strip()
        return f"PROJECT_HALTED: {reason}" if reason else "PROJECT_HALTED"

    agent_match = re.search(r'NEXT_AGENT\s*:\s*([A-Za-z/ ]+)', normalized, re.IGNORECASE)
    if agent_match:
        next_agent = agent_match.group(1).strip()
        return next_agent

    for agent_name in registry.list_agents():
        if agent_name.lower() in normalized.lower():
            return agent_name

    return "UNKNOWN"

@app.command()
def run(
    max_iterations: int = typer.Option(config.max_iterations, help="Maximum number of iterations.")
):
    """Starts the multi-agent SDLC orchestration."""
    print_header("MULTI-AGENT SDLC ORCHESTRATION SYSTEM (PYTHON)")

    # Prerequisites
    print_info("Verifying prerequisites...")
    if not orchestration_service.verify_tools():
        return
    if not orchestration_service.verify_git_repo():
        return
    orchestration_service.verify_specs_file()
    if not orchestration_service.initialize_beads():
        return
    
    print_success("All prerequisites verified")

    iteration = 0
    project_status = "RUNNING"

    while project_status == "RUNNING" and iteration < max_iterations:
        iteration += 1
        print_header(f"ITERATION {iteration}")

        # 1. Run Orchestrator to get decision
        print_info("Getting Orchestrator decision...")
        orchestrator_output = orchestration_service.activate_agent("Orchestrator", iteration)
        
        if not orchestrator_output:
            print_error("Orchestrator failed to provide a decision.")
            project_status = "HALTED"
            break

        next_action = parse_orchestrator_decision(orchestrator_output)
        print_info(f"Orchestrator decision: {next_action}")

        # 2. Handle completion or halt
        if next_action == "PROJECT_COMPLETE":
            print_header("PROJECT COMPLETION")
            print_success("All phases completed successfully!")
            
            # Final status report
            final_beads = orchestration_service.get_beads_state()
            print_info(f"Final project state:\n{final_beads}")
            
            project_status = "COMPLETE"
            break
        elif next_action.startswith("PROJECT_HALTED"):
            print_error(f"Project halted: {next_action}")
            project_status = "HALTED"
            break
        elif next_action == "UNKNOWN":
            print_error("Could not determine next agent from Orchestrator output.")
            project_status = "HALTED"
            break

        # 3. Activate the determined agent
        print_header(f"ACTIVATING AGENT: {next_action}")
        agent_output = orchestration_service.activate_agent(next_action, iteration)
        
        if not agent_output:
            print_error(f"Agent {next_action} failed.")
            continue

        print_info(f"Agent {next_action} completed.")
        
        # 4. Commit changes and Tag
        commit_msg = f"Iteration {iteration} - {next_action} task completed"
        orchestration_service.commit_changes(next_action, commit_msg)
        
        # Tagging (matching bash script iteration-N)
        import subprocess
        subprocess.run(["git", "tag", "-a", f"iteration-{iteration}", "-m", f"Iteration {iteration} completed"], capture_output=True)
        
        # Brief pause
        time.sleep(1)

    print_header("ORCHESTRATION FINAL STATUS")
    if project_status == "COMPLETE":
        print_success(f"Project completed successfully after {iteration} iterations.")
    elif project_status == "HALTED":
        print_error(f"Project halted after {iteration} iterations.")
    else:
        print_error(f"Project reached maximum iterations ({max_iterations}) without completion.")

if __name__ == "__main__":
    app()
