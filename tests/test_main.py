"""Tests for the main module."""

from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from orchestrator.main import app, run
import subprocess

runner = CliRunner()


def test_version_command():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SDLC Orchestrator v0.1.0" in result.stdout


@patch('orchestrator.main.orchestration_service')
@patch('time.sleep', return_value=None)
@patch('subprocess.run')
def test_run_success(mock_sub, mock_sleep, mock_service):
    """Test successful run with iterations."""
    # Setup mocks
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.side_effect = [2, 1, 0]  # Messages decrease
    mock_service.count_messages_for_agent.return_value = 2  # Messages for agent
    mock_service.select_agent_by_messages.return_value = "Developer"
    mock_service.get_beads_state.return_value = "Done"

    # Agent output (agents call broker directly, output is just informational)
    mock_service.activate_agent.return_value = "Completed work, sent messages via broker."

    # Call directly
    run(max_iterations=3)

    assert mock_service.activate_agent.call_count >= 1
    assert mock_service.commit_changes.called
    # No more register_message or mark_message_read - agents call broker directly


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
    """Test that system exits on prerequisite failures."""
    mock_service.verify_tools.return_value = False
    run(max_iterations=5)

    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = False
    run(max_iterations=5)

    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = False
    run(max_iterations=5)


@patch('orchestrator.main.orchestration_service')
def test_bootstrap_skipped_when_messages_exist(mock_service):
    """Test that bootstrap messages are skipped when pending messages exist."""
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.return_value = 5  # Messages exist
    mock_service.select_agent_by_messages.return_value = None  # No agent selected

    run(max_iterations=1)

    # Bootstrap should be skipped
    mock_service.create_bootstrap_messages.assert_not_called()


@patch('orchestrator.main.orchestration_service')
def test_bootstrap_created_when_no_messages(mock_service):
    """Test that bootstrap messages are created when no pending messages."""
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.return_value = 0  # No messages
    mock_service.select_agent_by_messages.return_value = None  # No agent selected

    run(max_iterations=1)

    # Bootstrap should be created
    mock_service.create_bootstrap_messages.assert_called_once()


@patch('orchestrator.main.orchestration_service')
@patch('time.sleep', return_value=None)
@patch('subprocess.run')
def test_run_agent_fails(mock_sub, mock_sleep, mock_service):
    """Test that system continues when agent fails."""
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.return_value = 1
    mock_service.count_messages_for_agent.return_value = 1
    mock_service.select_agent_by_messages.return_value = "Developer"
    mock_service.activate_agent.return_value = None  # Agent failed

    run(max_iterations=2)

    # Should continue to next iteration despite failure
    assert mock_service.activate_agent.call_count == 2
