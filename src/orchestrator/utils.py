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
