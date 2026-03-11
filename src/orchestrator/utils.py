import datetime
from rich.console import Console
from rich.panel import Panel

console = Console()

def get_timestamp() -> str:
    """Returns a formatted timestamp string."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_status(color: str, label: str, message: str) -> None:
    """Prints a status message with a timestamp and color."""
    timestamp = get_timestamp()
    console.print(f"[{color}]{timestamp} [{label}] {message}[/{color}]")

def print_info(message: str) -> None:
    """Prints an informational message in blue."""
    print_status("blue", "INFO", message)

def print_success(message: str) -> None:
    """Prints a success message in green."""
    print_status("green", "SUCCESS", message)

def print_warning(message: str) -> None:
    """Prints a warning message in yellow."""
    print_status("yellow", "WARNING", message)

def print_error(message: str) -> None:
    """Prints an error message in red."""
    print_status("red", "ERROR", message)

def print_header(title: str) -> None:
    """Prints a bold header panel."""
    console.print(Panel(f"[bold]{title}[/bold]", border_style="bold blue"))

def log_agent_activation(agent_name: str, message_count: int) -> None:
    """Logs agent activation with message count."""
    print_info(f"[ACTIVATION] {agent_name} selected ({message_count} pending messages)")

def log_messages_received(agent_name: str, count: int) -> None:
    """Logs messages received by an agent."""
    if count > 0:
        print_info(f"[RECEIVED] {agent_name}: {count} message(s) in context")
    else:
        print_info(f"[RECEIVED] {agent_name}: No messages in context")

def log_message_sent(from_agent: str, to_agent: str, content: str) -> None:
    """Logs a message sent by an agent."""
    # Truncate long content for display
    display_content = content[:60] + "..." if len(content) > 60 else content
    print_info(f"[SENT] {from_agent}->{to_agent}: {display_content}")

def log_messages_acknowledged(agent_name: str, bead_ids: list) -> None:
    """Logs messages acknowledged by an agent."""
    if bead_ids:
        ids_str = ", ".join(bead_ids[:5])
        if len(bead_ids) > 5:
            ids_str += f" (+{len(bead_ids) - 5} more)"
        print_info(f"[ACKNOWLEDGED] {agent_name} marked read: {ids_str}")
    else:
        print_info(f"[ACKNOWLEDGED] {agent_name}: No messages marked as read")
