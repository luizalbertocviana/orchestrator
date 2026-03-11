from unittest.mock import patch, MagicMock
import subprocess
from orchestrator.beads import BeadsWrapper

def test_run_command_success():
    wrapper = BeadsWrapper()
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout="Success", returncode=0)
        result = wrapper._run_command(["list"])
        assert result == "Success"
        mock_run.assert_called_with(["bd", "list"], capture_output=True, text=True, check=True)

def test_run_command_error():
    wrapper = BeadsWrapper()
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["bd", "list"], output="Error output")
        result = wrapper._run_command(["list"])
        assert result == "Error output"

def test_list_issues():
    wrapper = BeadsWrapper()
    with patch.object(wrapper, '_run_command') as mock_run:
        mock_run.return_value = "issue list"
        assert wrapper.list_issues(status="open") == "issue list"
        mock_run.assert_called_with(["list", "--status=open"])

def test_create_issue():
    wrapper = BeadsWrapper()
    with patch.object(wrapper, '_run_command') as mock_run:
        wrapper.create_issue("Title", description="Desc", issue_type="bug", priority=1)
        mock_run.assert_called_with(["create", "--title", "Title", "--type", "bug", "--priority", "1", "--description", "Desc"])

def test_close_issue():
    wrapper = BeadsWrapper()
    with patch.object(wrapper, '_run_command') as mock_run:
        wrapper.close_issue("beads-123", reason="Fixed")
        mock_run.assert_called_with(["close", "beads-123", "--reason", "Fixed"])

def test_get_ready():
    wrapper = BeadsWrapper()
    with patch.object(wrapper, '_run_command') as mock_run:
        wrapper.get_ready()
        mock_run.assert_called_with(["ready"])

def test_get_state():
    wrapper = BeadsWrapper()
    with patch.object(wrapper, '_run_command') as mock_run:
        wrapper.get_state()
        mock_run.assert_called_with(["list"])

def test_send_message():
    wrapper = BeadsWrapper()
    with patch.object(wrapper, 'create_issue') as mock_create:
        wrapper.send_message("AgentA", "AgentB", "Hello")
        # Check if title contains MESSAGE and the agents
        args, _ = mock_create.call_args
        assert "MESSAGE:" in args[0]
        assert "AgentA→AgentB" in args[0]
        assert "Hello" in args[0]
