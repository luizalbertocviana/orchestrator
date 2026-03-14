"""Tests for the main module."""

from typer.testing import CliRunner
from unittest.mock import patch, MagicMock, call
from orchestrator.main import app, run, get_last_iteration_from_tags
import subprocess

runner = CliRunner()


def test_version_command():
    """Test version command."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SDLC Orchestrator v0.1.0" in result.stdout


class TestGetLastIterationFromTags:
    """Tests for get_last_iteration_from_tags function."""

    @patch('orchestrator.main.subprocess.run')
    def test_no_tags_exist(self, mock_sub):
        """Test when no iteration tags exist."""
        mock_sub.return_value = MagicMock(stdout="", stderr="", returncode=0)
        
        result = get_last_iteration_from_tags()
        
        assert result == 0

    @patch('orchestrator.main.subprocess.run')
    def test_single_tag(self, mock_sub):
        """Test with a single iteration tag."""
        mock_sub.return_value = MagicMock(stdout="iteration-1\n", stderr="", returncode=0)
        
        result = get_last_iteration_from_tags()
        
        assert result == 1

    @patch('orchestrator.main.subprocess.run')
    def test_multiple_tags(self, mock_sub):
        """Test with multiple iteration tags."""
        mock_sub.return_value = MagicMock(stdout="iteration-1\niteration-5\niteration-3\n", stderr="", returncode=0)
        
        result = get_last_iteration_from_tags()
        
        assert result == 5

    @patch('orchestrator.main.subprocess.run')
    def test_non_sequential_tags(self, mock_sub):
        """Test with non-sequential tags (e.g., after manual deletion)."""
        mock_sub.return_value = MagicMock(stdout="iteration-2\niteration-7\niteration-12\n", stderr="", returncode=0)
        
        result = get_last_iteration_from_tags()
        
        assert result == 12

    @patch('orchestrator.main.subprocess.run')
    def test_git_command_fails(self, mock_sub):
        """Test when git command fails."""
        mock_sub.side_effect = subprocess.CalledProcessError(1, "git")
        
        result = get_last_iteration_from_tags()
        
        assert result == 0

    @patch('orchestrator.main.subprocess.run')
    def test_mixed_tag_names(self, mock_sub):
        """Test with mixed tag names (only iteration-* should be counted)."""
        mock_sub.return_value = MagicMock(stdout="iteration-1\nv1.0.0\niteration-3\nrelease-1\n", stderr="", returncode=0)
        
        result = get_last_iteration_from_tags()
        
        # Only iteration-1 and iteration-3 match, max is 3
        assert result == 3

    @patch('orchestrator.main.subprocess.run')
    def test_invalid_tag_format(self, mock_sub):
        """Test with invalid tag formats are ignored."""
        mock_sub.return_value = MagicMock(stdout="iteration-abc\niteration-1\niteration-\n", stderr="", returncode=0)
        
        result = get_last_iteration_from_tags()
        
        # Only iteration-1 is valid
        assert result == 1


@patch('orchestrator.main.orchestration_service')
@patch('orchestrator.main.get_last_iteration_from_tags')
@patch('time.sleep', return_value=None)
@patch('subprocess.run')
def test_run_success(mock_sub, mock_sleep, mock_get_last_iter, mock_service):
    """Test successful run with iterations."""
    # Setup mocks
    mock_get_last_iter.return_value = 0  # No existing tags
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
@patch('orchestrator.main.get_last_iteration_from_tags')
def test_run_no_messages(mock_service):
    """Test that system completes when no pending messages."""
    mock_get_last_iter.return_value = 0  # No existing tags
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.return_value = 0  # No messages from start

    run(max_iterations=5)

    # Should complete immediately without activating agents
    assert mock_service.activate_agent.call_count == 0


@patch('orchestrator.main.orchestration_service')
@patch('orchestrator.main.get_last_iteration_from_tags')
def test_run_max_iterations(mock_service):
    """Test that system stops at max iterations."""
    mock_get_last_iter.return_value = 0  # No existing tags
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
@patch('orchestrator.main.get_last_iteration_from_tags')
@patch('time.sleep', return_value=None)
@patch('subprocess.run')
def test_run_resumes_from_existing_tags(mock_sub, mock_sleep, mock_get_last_iter, mock_service):
    """Test that run continues iteration numbering from existing tags."""
    # Mock that 24 tags already exist from previous run
    mock_get_last_iter.return_value = 24
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.return_value = 1  # Always has messages
    mock_service.count_messages_for_agent.return_value = 1
    mock_service.select_agent_by_messages.return_value = "Developer"
    mock_service.activate_agent.return_value = "Done"

    run(max_iterations=3)

    # Should run 3 iterations this run
    assert mock_service.activate_agent.call_count == 3
    
    # Verify iteration numbers passed to activate_agent start at 25
    calls = mock_service.activate_agent.call_args_list
    assert calls[0][0][1] == 25  # First iteration: 24 + 1 = 25
    assert calls[1][0][1] == 26  # Second iteration: 24 + 2 = 26
    assert calls[2][0][1] == 27  # Third iteration: 24 + 3 = 27


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
@patch('orchestrator.main.get_last_iteration_from_tags')
def test_bootstrap_skipped_when_messages_exist(mock_get_last_iter, mock_service):
    """Test that bootstrap messages are skipped when pending messages exist."""
    mock_get_last_iter.return_value = 0  # No existing tags
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.return_value = 5  # Messages exist
    mock_service.select_agent_by_messages.return_value = None  # No agent selected

    run(max_iterations=1)

    # Bootstrap should be skipped
    mock_service.create_bootstrap_messages.assert_not_called()


@patch('orchestrator.main.orchestration_service')
@patch('orchestrator.main.get_last_iteration_from_tags')
def test_bootstrap_created_when_no_messages(mock_get_last_iter, mock_service):
    """Test that bootstrap messages are created when no pending messages."""
    mock_get_last_iter.return_value = 0  # No existing tags
    mock_service.verify_tools.return_value = True
    mock_service.verify_git_repo.return_value = True
    mock_service.initialize_beads.return_value = True
    mock_service.count_pending_messages.return_value = 0  # No messages
    mock_service.select_agent_by_messages.return_value = None  # No agent selected

    run(max_iterations=1)

    # Bootstrap should be created
    mock_service.create_bootstrap_messages.assert_called_once()


@patch('orchestrator.main.orchestration_service')
@patch('orchestrator.main.get_last_iteration_from_tags')
@patch('time.sleep', return_value=None)
@patch('subprocess.run')
def test_run_agent_fails(mock_sub, mock_sleep, mock_get_last_iter, mock_service):
    """Test that system continues when agent fails."""
    mock_get_last_iter.return_value = 0  # No existing tags
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
