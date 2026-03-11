from orchestrator.utils import get_timestamp, print_info, print_success, print_warning, print_error, print_header
from rich.console import Console

def test_get_timestamp():
    timestamp = get_timestamp()
    assert len(timestamp) == 19 # YYYY-MM-DD HH:MM:SS

def test_print_functions(capsys):
    print_info("info")
    print_success("success")
    print_warning("warning")
    print_error("error")
    print_header("header")
    
    captured = capsys.readouterr()
    # Rich uses escape codes, so we check if the message is in the output
    assert "info" in captured.err or captured.out
    assert "success" in captured.err or captured.out
    assert "warning" in captured.err or captured.out
    assert "error" in captured.err or captured.out
    assert "header" in captured.err or captured.out
