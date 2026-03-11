from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from orchestrator.main import app, strip_markdown, parse_messages, parse_mark_read, run
import subprocess

runner = CliRunner()

def test_strip_markdown():
    # Fix: ensure underscores are actually surrounded by word boundaries or at end/start
    assert strip_markdown("**bold** *italic* `code` __ under __ _ line _") == "bold italic code under line"

def test_parse_messages():
    output = """
    I've completed my work.
    MESSAGE: [Developer]→[Tester]: Code ready for testing.
    MESSAGE: [Developer]→[Architect/Designer]: Design question about API.
    """
    messages = parse_messages(output)
    assert len(messages) == 2
    assert messages[0] == ("Developer", "Tester", "Code ready for testing.")
    assert messages[1] == ("Developer", "Architect/Designer", "Design question about API.")

def test_parse_mark_read():
    output = """
    I've processed the messages.
    MARK_READ: beads-123, beads-124
    MARK_READ: beads-125
    """
    bead_ids = parse_mark_read(output)
    assert len(bead_ids) == 3
    assert "beads-123" in bead_ids
    assert "beads-124" in bead_ids
    assert "beads-125" in bead_ids

def test_parse_messages_empty():
    assert parse_messages("No messages here") == []

def test_parse_mark_read_empty():
    assert parse_mark_read("No mark read here") == []

def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SDLC Orchestrator v0.1.0" in result.stdout

@patch('orchestrator.main.orchestration_service')
@patch('time.sleep', return_value=None)
@patch('subprocess.run')
def test_run_success(mock_sub, mock_sleep, mock_service):
    # Setup mocks
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.side_effect = [2, 1, 0]  # Messages decrease
    mock_service.count_messages_for_agent.return_value = 2  # Messages for agent
    mock_service.select_agent_by_messages.return_value = "Developer"
    mock_service.get_beads_state.return_value = "Done"

    # Agent output with messages
    mock_service.activate_agent.return_value = """
    I've completed my work.
    MESSAGE: [Developer]→[Tester]: Ready for testing.
    MARK_READ: beads-123
    """

    # Call directly
    run(max_iterations=3)

    assert mock_service.activate_agent.call_count >= 1
    assert mock_service.commit_changes.called
    assert mock_service.register_message.called
    assert mock_service.mark_message_read.called

@patch('orchestrator.main.orchestration_service')
def test_run_no_messages(mock_service):
    """Test that system completes when no pending messages."""
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.return_value = 0  # No messages from start

    run(max_iterations=5)
    
    # Should complete immediately without activating agents
    assert mock_service.activate_agent.call_count == 0

@patch('orchestrator.main.orchestration_service')
def test_run_max_iterations(mock_service):
    """Test that system stops at max iterations."""
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.return_value = 1  # Always has messages
    mock_service.count_messages_for_agent.return_value = 1  # Messages for agent
    mock_service.select_agent_by_messages.return_value = "Developer"
    mock_service.activate_agent.return_value = "Done"

    run(max_iterations=3)
    
    # Should stop at max iterations
    assert mock_service.activate_agent.call_count == 3

@patch('orchestrator.main.orchestration_service')
def test_prerequisites_fail(mock_service):
    mock_service.verify_tools.return_value = False
    run(max_iterations=5)

    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = False
    run(max_iterations=5)

    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = False
    run(max_iterations=5)
